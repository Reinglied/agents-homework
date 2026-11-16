import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_live


class LiveRunnerTests(unittest.TestCase):
    def test_bad_key_input_rejected_without_echo(self):
        for value in ('', 'test key', 'test\x16key', 'test\nkey', '«test»', '"test"', "'test'"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): run_live.validate_key(value)
        self.assertEqual(run_live.validate_key('synthetic_KEY-123'),'synthetic_KEY-123')

    def test_double_entry_matches(self):
        for values,valid in [(['synthetic-key','synthetic-key'],True),(['synthetic-key','synthetic-other'],False)]:
            reader=iter(values)
            with patch('builtins.print'):
                if valid: self.assertEqual(run_live.read_confirmed_key(lambda:next(reader)),'synthetic-key')
                else:
                    with self.assertRaises(ValueError): run_live.read_confirmed_key(lambda:next(reader))

    def test_complete_and_missing_usage(self):
        self.assertEqual(run_live.usage_total({'model_calls':2,'trace':[{'event':'model','usage':{'total_tokens':5}},{'event':'model','usage':{'total_tokens':7}}]}),12)
        self.assertIsNone(run_live.usage_total({'model_calls':2,'trace':[{'event':'model','usage':{'total_tokens':5}},{'event':'model'}]}))

    def test_redaction(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'result.json'
            run_live.write_json(file,{'message':'secret-test'},'secret-test')
            self.assertNotIn('secret-test',file.read_text())

    def test_transport_failure_survives_agent_catching_it(self):
        class AgentError(Exception): pass
        def failing_model(history,tools): raise AgentError('HTTP 429. Quota.')
        def agent_run(question,cfg,model,**kwargs):
            try: model([],[])
            except AgentError: pass
            return {'stop_reason':'model_error','answer':None,'model_calls':1,'tool_calls':0,'trace':[]}
        fake=SimpleNamespace(AgentError=AgentError,load_config=lambda:{},make_live_model=lambda cfg,key:failing_model,run_agent=agent_run)
        with tempfile.TemporaryDirectory() as folder,patch.object(run_live,'load_agent',return_value=fake),patch.dict('os.environ',{'AGENT_API_KEY':'synthetic-key'}):
            file=Path(folder)/'result.json'
            self.assertEqual(run_live.run_worker(Path(folder),'question',file),0)
            data=json.loads(file.read_text(encoding='utf-8'))
            self.assertEqual(data['model_transport_errors'][0]['message'],'HTTP 429. Quota.')
            self.assertIsNone(data['result']['answer'])


if __name__=='__main__': unittest.main()
