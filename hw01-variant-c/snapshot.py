"""Content-verified snapshots; standard library only. Never imports agent code."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import uuid
from datetime import datetime, timezone


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def inventory(root):
    if not root.is_dir() or root.is_symlink() or (hasattr(root, 'is_junction') and root.is_junction()):
        raise ValueError('Root must be a regular directory')
    result = {}
    for item in sorted(root.rglob('*')):
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise ValueError('Links are not allowed: ' + str(item))
        if item.is_file():
            result[item.relative_to(root).as_posix()] = digest(item)
    return result


def verify(target):
    target = Path(target).resolve()
    manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
    actual = inventory(target / 'payload')
    if actual != manifest['files'] or not actual:
        raise ValueError('Snapshot content does not match manifest')
    return digest(target / 'manifest.json')


def create(source, target, label):
    source, target = Path(source).resolve(), Path(target).resolve()
    if not source.is_dir() or target.exists():
        raise ValueError('Source must exist and target must be new')
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('Source and target must not contain each other')
    before = inventory(source)
    if not before:
        raise ValueError('Empty source')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / ('.pending-' + uuid.uuid4().hex)
    staging.mkdir()
    try:
        shutil.copytree(source, staging / 'payload')
        if inventory(source) != before or inventory(staging / 'payload') != before:
            raise ValueError('Source changed during snapshot')
        manifest = {'schema': 1, 'label': label,
                    'created_utc': datetime.now(timezone.utc).isoformat(),
                    'files': before}
        with (staging / 'manifest.json').open('x', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        verify(staging)
        if target.exists():
            raise ValueError('Target already exists')
        staging.rename(target)
        return verify(target)
    except BaseException:
        # Preserve incomplete evidence for diagnosis; never delete input/output.
        raise


def run_and_capture(source, target, label, command):
    """Run a synchronous executor; snapshot on exit before caller can evaluate it."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+', label):
        raise ValueError('Label must be a simple identifier')
    if Path(target).exists():
        raise ValueError('Target already exists')
    evidence = Path(source) / 'evidence' / 'logs'
    evidence.mkdir(parents=True, exist_ok=True)
    log = evidence / (label + '.txt')
    with log.open('xb') as stream:
        result = subprocess.run(command, cwd=source, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    (evidence / (label + '-exit.json')).write_text(
        json.dumps({'command': command, 'exit_code': result.returncode}), encoding='utf-8')
    return result.returncode, create(source, target, label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('verify')
    check.add_argument('target')
    for name in ('create', 'run'):
        cmd = sub.add_parser(name)
        cmd.add_argument('source')
        cmd.add_argument('target')
        cmd.add_argument('label')
        if name == 'run':
            cmd.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'verify':
        print(verify(args.target))
    elif args.action == 'create':
        print(create(args.source, args.target, args.label))
    else:
        command = args.command
        if command and command[0] == '--':
            command = command[1:]
        if not command:
            parser.error('An executor command is required')
        code, sha = run_and_capture(args.source, args.target, args.label, command)
        print(json.dumps({'executor_exit_code': code, 'manifest_sha256': sha}))
        return code
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
