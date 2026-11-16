import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'attempt'
        self.source.mkdir()
        (self.source / 'agent.py').write_text('print(42)', encoding='utf-8')
        (self.source / 'evidence').mkdir()
        (self.source / 'evidence' / 'prompt.txt').write_text('Исходное поручение', encoding='utf-8')
        self.target = self.root / 'snapshots' / 'first'

    def test_roundtrip_and_immutable_copy(self):
        sha = snapshot.create(self.source, self.target, 'first')
        (self.source / 'agent.py').write_text('changed')
        self.assertEqual(sha, snapshot.verify(self.target))
        files = json.loads((self.target / 'manifest.json').read_text())['files']
        self.assertEqual(set(files), {'agent.py', 'evidence/prompt.txt'})

    def test_no_overwrite(self):
        snapshot.create(self.source, self.target, 'first')
        with self.assertRaises(ValueError):
            snapshot.create(self.source, self.target, 'first')

    def test_corruption_removal_and_addition(self):
        for change in ('edit', 'remove', 'add'):
            with self.subTest(change=change):
                target = self.target.parent / change
                snapshot.create(self.source, target, change)
                file = target / 'payload' / 'agent.py'
                if change == 'edit':
                    file.write_text('tampered')
                elif change == 'remove':
                    file.unlink()
                else:
                    (target / 'payload' / 'extra').write_text('extra')
                with self.assertRaises(ValueError):
                    snapshot.verify(target)

    def test_nested_target_rejected(self):
        with self.assertRaises(ValueError):
            snapshot.create(self.source, self.source / 'snapshot', 'first')

    def test_change_during_copy_rejected(self):
        original = snapshot.shutil.copytree
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            (self.source / 'agent.py').write_text('changed during copy')
            return result
        with patch.object(snapshot.shutil, 'copytree', side_effect=mutate):
            with self.assertRaises(ValueError):
                snapshot.create(self.source, self.target, 'first')
        self.assertFalse(self.target.exists())

    def test_automatic_capture_on_executor_success_and_failure(self):
        for code in (0, 2):
            target = self.target.parent / ('exit-' + str(code))
            result, sha = snapshot.run_and_capture(
                self.source, target, 'run-' + str(code),
                [sys.executable, '-c', 'print("executor output"); raise SystemExit(' + str(code) + ')'])
            self.assertEqual(result, code)
            self.assertEqual(snapshot.verify(target), sha)
            self.assertIn('executor output', (target / 'payload' / 'evidence' / 'logs' / ('run-' + str(code) + '.txt')).read_text())


if __name__ == '__main__':
    unittest.main()
