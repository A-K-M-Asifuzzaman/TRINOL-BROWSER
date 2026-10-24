#!/usr/bin/env python3
"""Check a pinned patch/overlay contract; writes require explicit --apply.

Check mode uses a temporary Git index/object store, supporting dependent patches
without writing the checkout. Never resets, cleans, builds or launches Chromium.
"""
from contextlib import contextmanager
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


def product_contract(product, manifest):
    """Validate the declared patch bytes and exact authorized output inventory."""
    if manifest.get('patch_series') != 'patches/series':
        raise ContractError('Unexpected patch series')
    entries = [s.strip() for s in safe_path(product, 'patches/series').read_text().splitlines()
               if s.strip() and not s.lstrip().startswith('#')]
    if len(entries) != len(set(entries)):
        raise ContractError('Duplicate series entry')
    patches = [safe_path(product, 'patches/' + name) for name in entries]
    overlays = manifest.get('overlays', [])
    contract = manifest.get('customization')
    if not entries and not overlays and contract is None:
        return patches, {}
    if (not isinstance(contract, dict) or set(contract) !=
            {'schema_version', 'id', 'upstream_revision', 'patches', 'files'} or
            contract['schema_version'] != 1 or
            not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', contract['id']) or
            contract['upstream_revision'] != manifest['chromium']['revision']):
        raise ContractError('Explicit pinned customization contract required')
    expected_patches = [dict(path=n, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                        for n, p in zip(entries, patches)]
    if contract['patches'] != expected_patches:
        raise ContractError('Patch order/digest mismatch')
    files = {}
    for entry in contract['files']:
        if not isinstance(entry, dict) or set(entry) != {'path', 'mode', 'sha256'}:
            raise ContractError('Invalid authorized file record')
        name = entry['path']
        safe_path(product, name)
        if name in files:
            raise ContractError('Duplicate authorized file')
        deleted = entry['mode'] is None and entry['sha256'] is None
        if not deleted and (entry['mode'] not in ('100644', '100755') or
                not isinstance(entry['sha256'], str) or
                not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
            raise ContractError('Invalid authorized mode/digest')
        files[name] = entry
    targets = set()
    for patch in patches:
        targets.update(patch_targets(product, patch))
    for entry in overlays:
        if not isinstance(entry, dict) or set(entry) != {'source', 'destination', 'sha256'}:
            raise ContractError('Invalid overlay declaration')
        source = safe_path(product, entry['source'])
        name = entry['destination']
        safe_path(product, name)
        if not name.startswith('trinol/') or name in targets:
            raise ContractError('Overlay destination collision/escape')
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise ContractError('Overlay digest mismatch')
        targets.add(name)
        if files.get(name) != dict(path=name, mode='100644', sha256=entry['sha256']):
            raise ContractError('Overlay output not authorized')
    if targets != set(files):
        raise ContractError('Authorized inventory differs from patch/overlay targets')
    return patches, files


@contextmanager
def scratch_index(checkout):
    with tempfile.TemporaryDirectory(prefix='trinol-patch-check-') as temp:
        objects = Path(temp) / 'objects'
        objects.mkdir()
        original = Path(git(checkout, 'rev-parse', '--git-path', 'objects'))
        if not original.is_absolute():
            original = checkout / original
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp)/'index'),
                   GIT_OBJECT_DIRECTORY=str(objects),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=str(original.resolve()))
        git(checkout, 'read-tree', 'HEAD', env=env)
        yield env


def expected_outputs(product, checkout, manifest):
    patches, files = product_contract(product, manifest)
    with scratch_index(checkout) as env:
        for patch in patches:
            git(checkout, 'apply', '--cached', '--check', str(patch), env=env)
            git(checkout, 'apply', '--cached', str(patch), env=env)
        entries = git(checkout, 'ls-files', '--stage', '-z', '--', *files, env=env) if files else ''
        index = {}
        for entry in filter(None, entries.split('\0')):
            meta, name = entry.split('\t', 1)
            mode, oid, stage = meta.split()
            if stage != '0' or mode not in ('100644', '100755'):
                raise ContractError('Unsupported index file mode')
            content = subprocess.check_output(['git', '-C', str(checkout), 'cat-file', 'blob', oid], env=env)
            index[name] = dict(path=name, mode=mode, sha256=hashlib.sha256(content).hexdigest())
        for entry in manifest.get('overlays', []):
            name = entry['destination']
            if name in index:
                raise ContractError('Overlay collides with patched file')
            index[name] = dict(path=name, mode='100644', sha256=entry['sha256'])
        for name, record in files.items():
            actual = index.get(name, dict(path=name, mode=None, sha256=None))
            if record != actual:
                raise ContractError('Declared output differs from pinned patches: ' + name)
    return files


def verify_source_state(product, checkout, manifest, state='applied'):
    """Reject all undeclared tracked and nonignored untracked source changes."""
    if git(checkout, 'rev-parse', 'HEAD') != manifest['chromium']['revision']:
        raise ContractError('Pinned HEAD mismatch')
    changed = set(filter(None, git(checkout, 'diff', '--no-renames', '--name-only', '-z', 'HEAD').split('\0')))
    untracked = set(filter(None, git(checkout, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')))
    if state == 'pristine':
        if changed or untracked:
            raise ContractError('Pristine checkout has local changes')
        return 'pristine'
    if state != 'applied':
        raise ContractError('Unknown source verification state')
    files = expected_outputs(product, checkout, manifest)
    if changed | untracked != set(files):
        raise ContractError('Unexpected/missing source changes: ' + repr(sorted((changed | untracked) ^ set(files))))
    for name, record in files.items():
        target = safe_path(checkout, name)
        if record['mode'] is None:
            if target.exists():
                raise ContractError('Expected deletion still exists: ' + name)
        elif (not target.is_file() or
              ('100755' if target.stat().st_mode & 0o111 else '100644') != record['mode'] or
              hashlib.sha256(target.read_bytes()).hexdigest() != record['sha256']):
            raise ContractError('Unauthorized file content/mode: ' + name)
    return 'applied' if files else 'pristine'


def patch_targets(checkout, patch):
    text = patch.read_text()
    # shortcut: regular text diffs only; review binary/rename/symlink support when needed.
    if re.search(r'^(?:GIT binary patch|rename |copy |(?:new file|new|old|deleted file) mode (?!100644\b|100755\b))', text, re.M):
        raise ContractError('Only regular-file text patches are supported')
    stats = git(checkout, 'apply', '--numstat', '-z', str(patch))
    if not stats:
        raise ContractError('Empty patch: ' + patch.name)
    targets = set()
    for line in stats.split('\0'):
        if not line:
            continue
        added, deleted, name = line.split('\t', 2)
        if added == '-' or deleted == '-':
            raise ContractError('Binary patch unsupported')
        safe_path(checkout, name)
        targets.add(name)
        if name.split('/')[0] in ('out', 'depot_tools'):
            raise ContractError('Generated/tool target forbidden')
    return targets


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
    product_contract(product, manifest)
    expected_outputs(product, checkout, manifest)
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
    if apply:
        verify_source_state(product, checkout, manifest)
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
