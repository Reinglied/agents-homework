"""Deterministic contract checks. Does not call a live model or grade prose."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_agent(folder):
    folder = Path(folder).resolve()
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location('candidate_agent', folder / 'agent.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_result(case, result, observed, emitted):
    expected = case['expected']
    require(isinstance(result, dict), 'run_agent must return a dict')
    require(result.get('model_calls') == expected['model_calls'] == len(observed['histories']), 'Wrong model-call count')
    require(result.get('tool_calls') == expected['tool_calls'] == len(observed['tools']), 'Wrong tool-call count')
    status = result.get('stop_reason')
    require(isinstance(status, str) and bool(status), 'Missing stop status')
    if expected.get('final', True):
        require(status == 'final_answer', 'Correct answer was not accepted')
        require(result.get('answer') == expected['answer'], 'Injected valid answer changed or wrong draft accepted')
    else:
        require(status != 'final_answer' and result.get('answer') is None, 'Unsafe final answer instead of stop')
    trace = result.get('trace')
    require(isinstance(trace, list), 'Missing trace')
    tool_events = [e for e in trace if e.get('event') == 'tool']
    model_events = [e for e in trace if e.get('event') == 'model']
    require(len(tool_events) == len(observed['tools']), 'Every dispatched tool needs a trace event')
    require(len(model_events) == len(observed['histories']), 'Every model attempt needs a trace event')
    for number, (event, actual) in enumerate(zip(tool_events, observed['tools']), 1):
        require(event.get('name') == actual['name'], 'Trace tool name differs from actual call')
        payload = event.get('result')
        require(isinstance(payload, dict), 'Tool result must be structured')
        if number in case.get('error_tools', []) or actual.get('raised') or 'error' in actual.get('result', {}):
            err = payload.get('error', {})
            require(isinstance(err, dict) and isinstance(err.get('code'), str) and bool(err['code'])
                    and isinstance(err.get('message'), str) and bool(err['message']), 'Missing useful structured error')
        else:
            require(payload == actual['result'], 'Trace must preserve returned source IDs and numbered lines')
    for history in observed['histories']:
        require(any(m.get('role') == 'user' and m.get('content') == case['question'] for m in history), 'Original question lost')
        # At the next model call, each preceding accepted assistant call has a matching result.
        pending = []
        result_index = 0
        for message in history:
            if message.get('role') == 'assistant' and message.get('tool_calls'):
                pending.extend(c['id'] for c in message['tool_calls'])
            if message.get('role') == 'tool':
                require(message.get('tool_call_id') in pending, 'Tool result has no matching call ID')
                pending.remove(message['tool_call_id'])
                payload = json.loads(message['content'])
                require(isinstance(payload, dict), 'Tool feedback must be a JSON object')
                require(result_index < len(tool_events) and payload == tool_events[result_index]['result'], 'History feedback differs from logged tool result')
                result_index += 1
        require(not pending, 'Missing tool feedback before next model call')
    if case.get('validation_feedback'):
        events = [e for e in trace if e.get('event') == 'validation']
        require(bool(events), 'Missing rejection trace')
        rejected = case['rejected_answer']
        histories = observed['histories']
        feedback = False
        for history in histories:
            for i, message in enumerate(history):
                if message.get('role') == 'assistant' and message.get('content') == rejected:
                    feedback |= any(m.get('role') in ('user', 'system', 'tool') and bool(m.get('content')) for m in history[i+1:])
        require(feedback, 'No nonempty corrective feedback after rejected draft')
    # These assertions test protocol mechanics, not the truth of arbitrary prose.
    return result


def run_case(agent, case):
    cfg = dict(agent.load_config(), **case.get('config', {}))
    observed = {'histories': [], 'tools': []}
    emitted = []
    script = case['steps']
    original_tool = agent.run_allowed_tool
    def model(history, tools):
        observed['histories'].append(copy.deepcopy(history))
        index = len(observed['histories']) - 1
        require(index < len(script), 'Unexpected extra model call')
        step = script[index]
        if step.get('raise_model'):
            raise agent.AgentError('Controlled model failure')
        return copy.deepcopy(step), {'prompt_tokens': 10, 'completion_tokens': 5}
    def tool(name, arguments, docs):
        actual = {'name': name, 'arguments': arguments}
        observed['tools'].append(actual)
        index = str(len(observed['tools']))
        injected = case.get('tool_overrides', {}).get(index)
        if injected and 'raise' in injected:
            actual['raised'] = injected['raise']
            raise RuntimeError(injected['raise'])
        result = copy.deepcopy(injected['result']) if injected else original_tool(name, arguments, docs)
        actual['result'] = copy.deepcopy(result)
        return result
    result = None
    try:
        with patch.object(agent, 'run_allowed_tool', side_effect=tool):
            result = agent.run_agent(case['question'], cfg, model, mode='STUB', emit=emitted.append)
        # Test-only secret originates inside the raised exception, never in the question.
        for override in case.get('tool_overrides', {}).values():
            if 'raise' in override:
                require(override['raise'] not in json.dumps([result, emitted, observed['histories']], ensure_ascii=False), 'Raw exception leaked into agent output/history')
        check_result(case, result, observed, emitted)
    except Exception as exc:
        exc.case_evidence = {'result': result, 'observed': observed, 'emitted': emitted}
        raise
    return {'result': result, 'observed': observed, 'emitted': emitted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', required=True)
    parser.add_argument('--cases', default=str(Path(__file__).with_name('public.json')))
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding='utf-8'))
    agent = load_agent(args.agent)
    report = {'mode': 'STUB', 'purpose': 'mechanics and controlled recovery only', 'cases': []}
    for case in cases:
        start = time.perf_counter()
        row = {'id': case['id'], 'requirements': case['requirements'], 'expected': case['expected']}
        try:
            row.update(status='PASS', evidence=run_case(agent, case))
        except Exception as exc:
            row.update(status='FAIL', error=type(exc).__name__ + ': ' + str(exc), traceback=traceback.format_exc(), evidence=getattr(exc, 'case_evidence', None))
        row['seconds'] = time.perf_counter() - start
        report['cases'].append(row)
    report['passed'] = sum(c['status'] == 'PASS' for c in report['cases'])
    report['total'] = len(cases)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"STUB: {report['passed']}/{report['total']} passed; report: {output}")
    return int(report['passed'] != report['total'])


if __name__ == '__main__':
    raise SystemExit(main())
