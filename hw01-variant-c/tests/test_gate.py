import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import freeze
import snapshot


class GateTests(unittest.TestCase):
    def test_both_snapshots_required_and_anchored(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'source'; source.mkdir()
            (source/'agent.py').write_text('original')
            anchors={}
            file=root/'anchors.json'
            for branch in ('direct','with-spec'):
                target=root/branch
                anchors[branch]={'path':str(target),'manifest_sha256':snapshot.create(source,target,'first')}
                file.write_text(json.dumps(anchors))
                if branch=='direct':
                    with self.assertRaises(ValueError): freeze.gate_first_pair(file)
            self.assertTrue(freeze.gate_first_pair(file))
            # Even coherent payload+manifest replacement must fail against external anchor.
            target=root/'direct'
            (target/'payload/agent.py').write_text('replaced')
            data=json.loads((target/'manifest.json').read_text())
            data['files']=snapshot.inventory(target/'payload')
            (target/'manifest.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError): freeze.gate_first_pair(file)


if __name__=='__main__': unittest.main()
