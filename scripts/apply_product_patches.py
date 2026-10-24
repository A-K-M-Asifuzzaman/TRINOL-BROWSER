#!/usr/bin/env python3
"""Check a pinned patch/overlay contract; writes require explicit --apply.

Check mode uses a temporary Git index/object store, supporting dependent patches
without writing the checkout. Never resets, cleans, builds or launches Chromium.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class ContractError(ValueError):
    def __init__(self, message, applied=()):
        super().__init__(message)
        self.applied = list(applied)


def safe_path(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative or
            any(p in ('', '.', '..', '.git') for p in relative.split('/')) or
            PurePosixPath(relative).is_absolute()):
        raise ContractError('Unsafe contract path: ' + str(relative))
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ContractError('Symlink contract path: ' + relative)
    if not path.resolve().is_relative_to(root):
        raise ContractError('Path escaped root')
    return path


def git(checkout, *args, env=None):
    return subprocess.run(['git', '-C', str(checkout), *args], env=env,
                          check=True, capture_output=True, text=True, timeout=120).stdout.strip()


def patch_targets(checkout, patch):
    text = patch.read_text()
    # shortcut: regular text diffs only; review binary/rename/symlink support when needed.
    if re.search(r'^(?:GIT binary patch|rename |copy |(?:new file|new|old|deleted file) mode (?!100644\b|100755\b))', text, re.M):
        raise ContractError('Only regular-file text patches are supported')
    stats = git(checkout, 'apply', '--numstat', '-z', str(patch))
    if not stats:
        raise ContractError('Empty patch: ' + patch.name)
    for line in stats.split('\0'):
        if not line:
            continue
        added, deleted, name = line.split('\t', 2)
        if added == '-' or deleted == '-':
            raise ContractError('Binary patch unsupported')
        safe_path(checkout, name)
        if name.split('/')[0] in ('out', 'depot_tools'):
            raise ContractError('Generated/tool target forbidden')


def apply_contract(product, checkout, apply=False):
    product, checkout = Path(product).resolve(strict=True), Path(checkout).resolve(strict=True)
    if (product == checkout or product.is_relative_to(checkout) or checkout.is_relative_to(product)):
        raise ContractError('Product and checkout must be separate')
    if Path(git(checkout, 'rev-parse', '--show-toplevel')).resolve() != checkout:
        raise ContractError('Checkout must be its Git root')
    manifest = json.loads(safe_path(product, 'upstream/manifest.json').read_text())
    revision = manifest['chromium']['revision']
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ContractError('Full Chromium revision required')
    if git(checkout, 'rev-parse', 'HEAD') != revision:
        raise ContractError('Pinned HEAD mismatch')
    if git(checkout, 'status', '--porcelain', '--untracked-files=all'):
        raise ContractError('Checkout has local changes; preserve and inspect them')
    if manifest['patch_series'] != 'patches/series':
        raise ContractError('Unexpected patch series')
    entries = [line.strip() for line in safe_path(product, manifest['patch_series']).read_text().splitlines()
               if line.strip() and not line.lstrip().startswith('#')]
    if len(entries) != len(set(entries)):
        raise ContractError('Duplicate series entry')
    patches = [safe_path(product, 'patches/' + name) for name in entries]
    for patch in patches:
        patch_targets(checkout, patch)
    overlays, destinations = [], set()
    for entry in manifest['overlays']:
        if set(entry) != {'source', 'destination', 'sha256'}:
            raise ContractError('Overlay requires source, destination and sha256')
        source = safe_path(product, entry['source'])
        target = safe_path(checkout, entry['destination'])
        if not entry['destination'].startswith('trinol/'):
            raise ContractError('Owned overlays must target trinol/')
        if target.exists() or target in destinations:
            raise ContractError('Overlay destination collision')
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise ContractError('Overlay digest mismatch')
        destinations.add(target)
        overlays.append((source, target))
    # A scratch index AND scratch object store avoid .git writes in check mode.
    with tempfile.TemporaryDirectory(prefix='trinol-patch-check-') as temp:
        objects = Path(temp) / 'objects'
        objects.mkdir()
        original_objects = Path(git(checkout, 'rev-parse', '--git-path', 'objects'))
        if not original_objects.is_absolute():
            original_objects = checkout / original_objects
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp)/'index'),
                   GIT_OBJECT_DIRECTORY=str(objects),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=str(original_objects.resolve()))
        git(checkout, 'read-tree', 'HEAD', env=env)
        for patch in patches:
            git(checkout, 'apply', '--cached', '--check', str(patch), env=env)
            git(checkout, 'apply', '--cached', str(patch), env=env)
        tracked = set(git(checkout, 'ls-files', '-z', env=env).split('\0'))
        if any(str(target.relative_to(checkout)) in tracked for _, target in overlays):
            raise ContractError('Overlay collides with a patched file')
    applied = []
    try:
        if apply:
            for name, patch in zip(entries, patches):
                git(checkout, 'apply', '--check', str(patch))
                git(checkout, 'apply', str(patch))
                applied.append('patches/' + name)
            for source, target in overlays:
                safe_path(checkout, target.relative_to(checkout).as_posix())
                target.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation refuses any existing content, including races.
                with target.open('xb') as stream:
                    stream.write(source.read_bytes())
                applied.append(target.relative_to(checkout).as_posix())
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise ContractError(str(exc), applied) from exc
    return dict(mode='apply' if apply else 'check', revision=revision,
                patches=[dict(path=n, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                         for n, p in zip(entries, patches)],
                overlays=[t.relative_to(checkout).as_posix() for _, t in overlays], applied=applied)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product-root', type=Path, default=ROOT)
    parser.add_argument('--checkout', required=True, type=Path)
    parser.add_argument('--apply', action='store_true', help='Write reviewed patches/overlays; default is check only')
    args = parser.parse_args()
    try:
        print(json.dumps(apply_contract(args.product_root, args.checkout, args.apply), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(error=str(exc), applied=getattr(exc, 'applied', []),
                             action='Preserve checkout; no automatic rollback/reset')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
