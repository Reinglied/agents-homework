"""Run the frozen 30-run LIVE plan. --dry-run never requests a key or calls API."""
import argparse
from datetime import datetime, timezone
import importlib.util
import hmac
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import freeze
import snapshot


def validate_key(value):
    if not value:
        raise ValueError('Ключ пустой.')
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError('В ключе есть пробел, перенос строки, управляющий или не-ASCII символ. Скопируйте только значение ключа.')
    if any(c in value for c in ('"', "'", '`')):
        raise ValueError('В ключ попали кавычки. Скопируйте только значение, без кавычек и команды.')
    return value


def read_confirmed_key(reader):
    print('Вставьте только значение API-ключа, без кавычек. Ввод скрыт.', flush=True)
    first = validate_key(reader())
    print(f'Получено символов: {len(first)}. Повторно вставьте тот же ключ для сверки.', flush=True)
    second = validate_key(reader())
    if not hmac.compare_digest(first, second):
        raise ValueError('Два ввода не совпадают. Запусков API не было; повторите команду.')
    print('Оба ввода совпадают; недопустимых символов не обнаружено. Это не проверка действительности ключа.', flush=True)
    return first


def write_json(path, value, key=None):
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if key:
        text = text.replace(key, '[REDACTED]')
    path.write_text(text, encoding='utf-8')


def load_agent(folder):
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location('live_candidate', folder / 'agent.py')
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    return agent


def run_worker(folder, question, output):
    key = os.environ['AGENT_API_KEY']
    agent = load_agent(folder)
    cfg = agent.load_config()
    live = agent.make_live_model(cfg, key)
    errors = []
    def tracked_model(history, tools):
        try:
            return live(history, tools)
        except Exception as exc:
            # The frozen transport emits safe AgentError diagnostics (no headers/body).
            errors.append({'type': type(exc).__name__, 'message': str(exc).replace(key, '[REDACTED]')
                           if isinstance(exc, agent.AgentError) else 'Unexpected transport exception'})
            raise
    started = datetime.now(timezone.utc).isoformat()
    tick = time.perf_counter()
    try:
        result = agent.run_agent(question, cfg, tracked_model, mode='LIVE', emit=lambda _: None)
        record = {'result': result, 'process_error': None}
    except Exception as exc:
        record = {'result': None, 'process_error': {'type': type(exc).__name__, 'message': 'Agent execution failed'}}
    record.update(started_utc=started, duration_seconds=time.perf_counter()-tick,
                  model_transport_errors=errors, config=cfg)
    write_json(output, record, key)
    return 0 if record['process_error'] is None else 2


def usage_total(result):
    if not result:
        return None
    events = [e for e in result.get('trace', []) if e.get('event') == 'model']
    values = [e.get('usage', {}).get('total_tokens') for e in events]
    if not values or len(values) != result.get('model_calls') or not all(type(v) is int for v in values):
        return None
    return sum(values)


def check_inputs(series_name='first'):
    if series_name not in ('first', 'round1', 'round2'):
        raise ValueError('Unknown series')
    anchor_file = ROOT / (series_name + '-anchors.json')
    freeze.gate_first_pair(anchor_file)
    anchors = json.loads(anchor_file.read_text(encoding='utf-8'))
    lock = json.loads((ROOT/'frozen-inputs.json').read_text(encoding='utf-8'))['files']
    for relative in ('evaluator/live-plan.json', 'evaluator/LIVE-RUBRIC.md'):
        if snapshot.digest(ROOT/relative) != lock[relative]:
            raise ValueError('Frozen LIVE input changed: '+relative)
    plan = json.loads((ROOT/'evaluator/live-plan.json').read_text(encoding='utf-8'))
    configs = [json.loads((Path(anchors[b]['path'])/'payload/config.json').read_text(encoding='utf-8')) for b in ('direct','with-spec')]
    if configs[0] != configs[1] or len(plan) != 30:
        raise ValueError('Unequal config or unexpected plan size')
    return anchors, plan, configs[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--series', choices=('first', 'round1', 'round2'), default='first')
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--question', help=argparse.SUPPRESS)
    parser.add_argument('--result', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return run_worker(args.worker, args.question, args.result)
    anchors, plan, cfg = check_inputs(args.series)
    if args.dry_run:
        print(f"DRY RUN OK: series={args.series}, {len(plan)} runs, snapshots verified, identical configs; no API calls.")
        print(f"Model: {cfg['model']}; at most {len(plan)*cfg['max_model_calls']} model calls.")
        return 0
    # Reuse the common, tested hidden console input; no key on command line or disk.
    sys.path.insert(0, str(Path(anchors['direct']['path'])/'payload'))
    from console_input import read_key
    key = read_confirmed_key(read_key)
    destination = ROOT/'live-results'/(args.series+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    destination.mkdir(parents=True, exist_ok=False)
    for branch, entry in anchors.items():
        shutil.copytree(Path(entry['path'])/'payload', destination/'work'/branch)
    write_json(destination/'series.json', {'mode':'LIVE','series':args.series,'anchors':anchors,'config':cfg,
              'runner_sha256':snapshot.digest(Path(__file__)), 'plan_sha256':snapshot.digest(ROOT/'evaluator/live-plan.json'),
              'retries':0,'note':'Auth/quota failures stop remaining planned runs; completed failures are not retried.'})
    rows = [dict(row, series=args.series, snapshot_sha256=anchors[row['branch']]['manifest_sha256']) for row in plan]
    write_json(destination/'results.json', rows)
    env = dict(os.environ, AGENT_API_KEY=key, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    print('Results: '+str(destination), flush=True)
    for row in rows:
        stem = f"{row['run']:02d}-{row['scenario']}-{row['repeat']}-{row['branch']}"
        result_file = destination/(stem+'.json')
        command = [sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker',
                   str(destination/'work'/row['branch']),'--question',row['question'],'--result',str(result_file)]
        tick=time.perf_counter()
        row['status']='RUNNING'
        write_json(destination/'results.json',rows)
        try:
            process=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf-8',
                                   timeout=cfg['max_model_calls']*cfg['timeout_seconds']+30)
            write_json(destination/(stem+'-process.json'),{'exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr},key)
            if not result_file.is_file():
                row.update(status='PROCESS_ERROR',duration_seconds=time.perf_counter()-tick)
                write_json(destination/'results.json',rows)
                break
            record=json.loads(result_file.read_text(encoding='utf-8'))
            result=record['result'] or {}
            errors=record['model_transport_errors']
            row.update(status='COMPLETED' if not record['process_error'] else 'AGENT_ERROR',
                       duration_seconds=record['duration_seconds'],started_utc=record['started_utc'],
                       stop_reason=result.get('stop_reason'),model_calls=result.get('model_calls'),
                       tool_calls=result.get('tool_calls'),tokens=usage_total(result),
                       transport_error=errors or None,evidence=result_file.name)
            if errors:
                row['status']='MODEL_OR_TRANSPORT_ERROR'
            print(f"{row['run']:02d}/30 {row['branch']} {row['scenario']}: {row['status']}, {row.get('stop_reason')}",flush=True)
            write_json(destination/'results.json',rows)
            if any(any(code in e['message'] for code in ('HTTP 401','HTTP 403','HTTP 429')) for e in errors):
                print('Authorization/quota error: stopped; remaining runs are NOT RUN.',flush=True)
                break
        except subprocess.TimeoutExpired:
            row.update(status='TIMEOUT',duration_seconds=time.perf_counter()-tick,
                       transport_error='Worker timeout; request billing/completion may be unknown.')
            write_json(destination/'results.json',rows)
        except KeyboardInterrupt:
            row.update(status='INTERRUPTED',duration_seconds=time.perf_counter()-tick)
            write_json(destination/'results.json',rows)
            print('Stopped by user; no retries.',flush=True)
            break
    freeze.gate_first_pair(ROOT/(args.series+'-anchors.json'))
    print('Saved: '+str(destination/'results.json'))
    print('Content scores remain unassigned: final_answer is not an automatic success.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
