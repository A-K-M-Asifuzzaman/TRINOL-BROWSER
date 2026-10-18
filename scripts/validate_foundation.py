#!/usr/bin/env python3
"""Validate the repository foundation contract without fetching dependencies."""
import json
from pathlib import Path
import re
import subprocess

from verify_upstream_checkout import validate_manifest

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'upstream/manifest.json').read_text())
    validate_manifest(manifest)
    series = ROOT / manifest['patch_series']
    assert series.is_file()
    assert not [line for line in series.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
    files = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=ROOT).decode().split('\0')
    markdown_count = 0
    for name in filter(None, files):
        path = ROOT / name
        assert not path.is_symlink(), f'Unexpected symlink: {name}'
        assert path.stat().st_size < 1024 * 1024, f'Review unexpected large file: {name}'
        assert not set(Path(name).parts) & {'chromium', 'depot_tools', 'node_modules', 'out'}, name
        if path.suffix == '.md':
            markdown_count += 1
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                assert (path.parent / target.split('#')[0]).exists(), f'{name}: broken link {target}'
    print(f'PASS: Phase {manifest["phase"]} manifest, empty customization contract, file bounds, '
          f'and local links in {markdown_count} Markdown files')
    print('Not a secret scanner, Chromium build, or browser test.')


if __name__ == '__main__':
    main()
