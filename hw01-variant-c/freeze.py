"""Freeze inputs and gate evaluation/repairs on verified first snapshots."""
import argparse
import json
from pathlib import Path
import snapshot

ROOT = Path(__file__).resolve().parent


def freeze_inputs(root=ROOT):
    root = Path(root)
    lock = root / 'frozen-inputs.json'
    if lock.exists():
        raise ValueError('Inputs already frozen; create a new protocol version, do not overwrite')
    files = {}
    for folder in ('ready', 'quality', 'prompts'):
        for relative, sha in snapshot.inventory(root / folder).items():
            files[folder + '/' + relative] = sha
    for relative in ('contract.md', 'matrix.md', 'protocol.md', 'registration.json',
                     'evaluator/external.json', 'evaluator/LIVE-RUBRIC.md', 'evaluator/live-plan.json',
                     'snapshot.py', 'freeze.py'):
        files[relative] = snapshot.digest(root / relative)
    lock.write_text(json.dumps({'schema': 1, 'files': files}, ensure_ascii=False, indent=2),encoding='utf-8')
    return snapshot.digest(lock)


def verify_inputs(root=ROOT):
    root = Path(root)
    data = json.loads((root / 'frozen-inputs.json').read_text(encoding='utf-8'))
    for relative, expected in data['files'].items():
        path = root / relative
        if not path.is_file() or snapshot.digest(path) != expected:
            raise ValueError('Frozen input changed: ' + relative)
    # Additional files in executor packages could leak solutions or change context.
    for folder in ('ready', 'quality', 'prompts'):
        actual = {folder+'/'+p:h for p,h in snapshot.inventory(root/folder).items()}
        expected = {p:h for p,h in data['files'].items() if p.startswith(folder+'/')}
        if actual != expected:
            raise ValueError('Frozen package inventory changed: '+folder)
    return snapshot.digest(root/'frozen-inputs.json')


def gate_first_pair(anchors):
    data = json.loads(Path(anchors).read_text(encoding='utf-8'))
    if set(data) != {'direct','with-spec'}:
        raise ValueError('Both first snapshots are required')
    for branch, entry in data.items():
        if snapshot.verify(entry['path']) != entry['manifest_sha256']:
            raise ValueError('First snapshot anchor differs: '+branch)
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','verify','gate'])
    parser.add_argument('--anchors')
    args=parser.parse_args()
    if args.action=='freeze': print(freeze_inputs())
    elif args.action=='verify': print(verify_inputs())
    else:
        if not args.anchors: parser.error('--anchors required')
        print(gate_first_pair(args.anchors))
