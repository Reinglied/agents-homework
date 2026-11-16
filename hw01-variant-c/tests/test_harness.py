"""Harness self-checks; these are not agent acceptance results."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'quality'))
import harness


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = harness.load_agent(ROOT/'baseline/direct')
        cls.public = json.loads((ROOT/'quality/public.json').read_text(encoding='utf-8'))

    def test_baseline_valid_controls(self):
        for case in self.public:
            if case['id'] in {'P-accept-correct','P-A1-complete','P-A2-no-price','P-positive-0','P-positive-1','P-positive-2','P-empty-search','P-exact-tool-budget','P-exact-model-budget','P-oversized-batch','P-remaining-budget','P-model-budget'}:
                with self.subTest(case=case['id']):
                    harness.run_case(self.agent,case)

    def test_known_baseline_defects_are_detected(self):
        for id_ in ('P-bad-citation-0','P-missing-reference','P-sparse-gap','P-tool-exception-recovery','P-model-error'):
            with self.subTest(case=id_):
                case=next(c for c in self.public if c['id']==id_)
                with self.assertRaises(Exception):
                    harness.run_case(self.agent,case)

    def test_oracle_rejects_corrupted_outputs(self):
        case=self.public[0]
        data=harness.run_case(self.agent,case)
        mutations={
            'model_count':lambda r,o:r.update(model_calls=0),
            'tool_count':lambda r,o:r.update(tool_calls=0),
            'over_reject':lambda r,o:r.update(stop_reason='stopped',answer=None),
            'wrong_answer':lambda r,o:r.update(answer='Different answer'),
            'no_trace':lambda r,o:r.update(trace=[]),
            'actual_call_missing':lambda r,o:o['tools'].pop(),
            'question_lost':lambda r,o:o['histories'][0].clear(),
        }
        for name,mutate in mutations.items():
            with self.subTest(mutation=name):
                changed=copy.deepcopy(data)
                mutate(changed['result'],changed['observed'])
                with self.assertRaises(AssertionError):
                    harness.check_result(case,changed['result'],changed['observed'],changed['emitted'])

    def test_error_result_must_be_structured(self):
        case=next(c for c in self.public if c['id']=='P-unknown-id')
        data=harness.run_case(self.agent,case)
        events=[e for e in data['result']['trace'] if e.get('event')=='tool']
        events[1]['result']={'error':{'code':'not_found'}}
        with self.assertRaises(AssertionError):
            harness.check_result(case,data['result'],data['observed'],data['emitted'])

    def test_tool_feedback_id_is_checked(self):
        case=self.public[0]
        data=harness.run_case(self.agent,case)
        for message in data['observed']['histories'][-1]:
            if message.get('role')=='tool': message['tool_call_id']='unmatched'
        with self.assertRaises(AssertionError):
            harness.check_result(case,data['result'],data['observed'],data['emitted'])

    def test_both_suites_cover_same_requirements(self):
        external=json.loads((ROOT/'evaluator/external.json').read_text(encoding='utf-8'))
        required={'A1','A2','A3','A4','A5','M1','M2','M3','M4','M5','M6','R1','R2','R3','R4','S1'}
        for cases in (self.public,external):
            self.assertEqual({r for c in cases for r in c['requirements']},required)
            self.assertEqual(len({c['id'] for c in cases}),len(cases))
            for case in cases:
                self.assertLessEqual(case['expected']['model_calls'],8)
                self.assertLessEqual(case['expected']['tool_calls'],16)
        self.assertNotEqual(self.public,external)


if __name__=='__main__': unittest.main()
