#!/usr/bin/env python3
"""Verify pinned upstream source/tool checkouts without downloading or building."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r'[0-9a-f]{40}')
URLS = {
    'chromium': 'https://chromium.googlesource.com/chromium/src.git',
    'depot_tools': 'https://chromium.googlesource.com/chromium/tools/depot_tools.git',
}


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError('Manifest must be an object')
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported manifest schema')
    phase = manifest.get('phase')
    if phase not in (0, '1a', '1b', '1c'):
        raise ValueError('Unsupported phase')
    for name, url in URLS.items():
        entry = manifest.get(name, {})
        if not isinstance(entry, dict):
            raise ValueError(f'{name} entry must be an object')
        if entry.get('url') != url:
            raise ValueError(f'Unexpected {name} upstream URL')
        revision = entry.get('revision')
        if phase in ('1b', '1c'):
            if not isinstance(revision, str) or not SHA.fullmatch(revision):
                raise ValueError(f'{name} needs a full lowercase commit SHA')
        elif revision is not None:
            raise ValueError('Pre-checkout phases must retain null revision pins')
    if manifest.get('patch_series') != 'patches/series' or manifest.get('overlays') != []:
        raise ValueError('Baseline must retain the empty customization contract')
    if phase in ('1b', '1c'):
        chromium = manifest['chromium']
        version = chromium.get('version', '')
        if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
            raise ValueError('Chromium requires a full release version')
        if chromium.get('tag') != 'refs/tags/' + version or chromium.get('channel') != 'Stable':
            raise ValueError('Expected a version-matched stable tag')
        evidence = manifest.get('verification', {})
        if not isinstance(evidence, dict):
            raise ValueError('Verification evidence must be an object')
        for field in ('source_head', 'depot_tools_head', 'dependencies_synced', 'hooks_completed'):
            if evidence.get(field) is not True:
                raise ValueError(f'Phase 1B completion evidence missing: {field}')
        if not re.fullmatch(r'[0-9a-f]{64}', evidence.get('deps_sha256', '')):
            raise ValueError('Missing verified DEPS digest')
        if phase == '1c':
            build = manifest.get('build', {})
            if not isinstance(build, dict) or build.get('status') != 'complete':
                raise ValueError('Phase 1C requires a completed build record')
            for field in ('gn_generated', 'chromium_compiled'):
                if evidence.get(field) is not True:
                    raise ValueError(f'Phase 1C completion evidence missing: {field}')
            for field in ('browser_launched', 'smoke_tests_completed'):
                if build.get(field) is not True:
                    raise ValueError(f'Phase 1C runtime evidence missing: {field}')
    return manifest


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True,
                          capture_output=True, text=True, timeout=120).stdout.strip()


def release_version(source):
    entries = {}
    for line in (source / 'chrome/VERSION').read_text().splitlines():
        key, value = line.split('=', 1)
        entries[key] = value
    return '.'.join(entries[key] for key in ('MAJOR', 'MINOR', 'BUILD', 'PATCH'))


def verify(manifest, checkout_root, depot_tools):
    validate_manifest(manifest)
    if manifest['phase'] not in ('1b', '1c'):
        raise ValueError('Manifest has no verified Phase 1B checkout yet')
    checkout_root = Path(checkout_root).expanduser().resolve(strict=True)
    source = (checkout_root / 'src').resolve(strict=True)
    depot = Path(depot_tools).expanduser().resolve(strict=True)
    for path in (checkout_root, source, depot):
        if any(char.isspace() for char in str(path)):
            raise ValueError('Resolved upstream paths must not contain whitespace')
        if path == ROOT or ROOT in path.parents or path in ROOT.parents:
            raise ValueError('Upstream and product repository paths must be separate')
    if source == depot or source in depot.parents or depot in source.parents:
        raise ValueError('Source and tool repositories must be separate')
    for marker in ('.gclient', '.gclient_entries'):
        if not (checkout_root / marker).is_file():
            raise ValueError(f'Missing gclient checkout metadata: {marker}')
    for name, path in (('chromium', source), ('depot_tools', depot)):
        if Path(git(path, 'rev-parse', '--show-toplevel')).resolve() != path.resolve():
            raise ValueError(f'{name} directory is not its Git root')
        if git(path, 'remote', 'get-url', 'origin') != URLS[name]:
            raise ValueError(f'{name} origin mismatch')
        if git(path, 'rev-parse', 'HEAD') != manifest[name]['revision']:
            raise ValueError(f'{name} HEAD mismatch')
        if git(path, 'status', '--porcelain', '--untracked-files=no'):
            raise ValueError(f'{name} has tracked modifications')
    if git(source, 'rev-parse', manifest['chromium']['tag'] + '^{commit}') != manifest['chromium']['revision']:
        raise ValueError('Local release tag does not resolve to pinned source')
    if release_version(source) != manifest['chromium']['version']:
        raise ValueError('chrome/VERSION mismatch')
    for name in ('chrome', 'content', 'components', 'third_party', 'build'):
        if not (source / name).is_dir():
            raise ValueError(f'Missing expected source directory: {name}')
    digest = hashlib.sha256((source / 'DEPS').read_bytes()).hexdigest()
    if digest != manifest['verification']['deps_sha256']:
        raise ValueError('DEPS digest mismatch')
    return [f'Chromium {manifest["chromium"]["version"]}: {manifest["chromium"]["revision"]}',
            f'depot_tools: {manifest["depot_tools"]["revision"]}',
            f'DEPS SHA-256: {digest}',
            'Tracked source/tool files are clean; this verifier does not run builds.',
            'Dependency/hook completion is recorded evidence; this check does not rerun sync '
            'or prove every dependency remains unchanged.']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'upstream/manifest.json')
    parser.add_argument('--checkout-root', required=True)
    parser.add_argument('--depot-tools', required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        for line in verify(manifest, args.checkout_root, args.depot_tools):
            print('PASS:', line)
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('BLOCKED:', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
