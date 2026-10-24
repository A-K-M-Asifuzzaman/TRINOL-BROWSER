#!/usr/bin/env python3
"""Read-only capture of an already-supervised Chromium window; never selects an app."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import time

from build_chromium_macos import contained
import phase2b1v_runtime as visual
import test_chromium_lifecycle_macos as life


def capture(root, run, observer, name, window_id=None):
    run = contained(root, run.relative_to(root))
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', name):
        raise ValueError('Capture name must be a simple label')
    if (run / 'result.json').exists():
        raise ValueError('Session already finished; never launch another browser for capture')
    launch = json.loads(contained(root, (run / 'launch.json').relative_to(root)).read_text())
    claim = json.loads(contained(root, visual.CLAIM).read_text())
    if (claim['evidence'] != str(run) or claim['authorization'] != launch.get('visual_authorization')
            or claim['authorization']['phase'] != '2b1-v'):
        raise ValueError('Capture must belong to the claimed Phase 2B1-V supervised session')
    lines = contained(root, (run / 'events.jsonl').relative_to(root)).read_text().splitlines(keepends=True)
    events = [json.loads(line) for line in lines if line.endswith('\n')]
    original = next(e['browser_identity'] for e in events if e['event'] == 'process_identity_verified')
    profile = contained(root, Path(launch['profile']).relative_to(root))
    if (original['pid'] != launch['pid'] or original['executable'] != str(root / life.EXE)
            or '--user-data-dir=' + str(profile) not in original['command'].split()):
        raise ValueError('Capture does not identify the supervised disposable-profile browser')

    def recheck():
        rows = life.snapshot(root / life.APP, launch['pid'])
        if not any(life.identity(row) == life.identity(original) for row in rows):
            raise ValueError('Supervised PID/start/executable identity no longer exists')

    observer = visual.check_observer(root, observer)
    recheck()
    windows = json.loads(subprocess.check_output([str(observer), str(launch['pid'])], timeout=5))
    candidates = [w for w in windows if window_id is None or w['window_id'] == window_id]
    if len(candidates) != 1 or not isinstance(candidates[0]['window_id'], int) or candidates[0]['window_id'] <= 0:
        raise ValueError('Choose one verified owned window; available IDs: ' + str([w['window_id'] for w in windows]))
    window = candidates[0]
    library = contained(root, 'chromium/src/out/TrinolDev/libchrome_dll.dylib')
    if visual.sha256(library) != visual.LIBRARY_SHA256:
        raise ValueError('Corrected library changed before capture')
    loaded = subprocess.check_output(['/usr/sbin/lsof', '-p', str(launch['pid']), '-Fn'], timeout=5).decode()
    if 'n' + str(library) not in loaded.splitlines():
        raise ValueError('Expected corrected library is not mapped by the supervised process')
    target = contained(root, (run / (name + '.png')).relative_to(root))
    with target.open('xb'):
        pass  # Reserve exclusively; screencapture writes only this private evidence path.
    recheck()
    subprocess.run(['/usr/sbin/screencapture', '-x', '-l', str(window['window_id']), str(target)],
                   check=True, timeout=5)
    recheck()
    with target.open('rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or not all(struct.unpack('>II', header[16:24])):
        raise ValueError('Capture did not produce a PNG with positive dimensions')
    record = dict(time_unix=time.time(), browser_identity=life.identity(original), window=window,
                  image_pixels=struct.unpack('>II', header[16:24]),
                  library_sha256=visual.LIBRARY_SHA256, capture_sha256=visual.sha256(target))
    with (run / (name + '.json')).open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--window-observer', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--window-id', type=int)
    args = parser.parse_args()
    print(capture(args.build_root, args.run, args.window_observer, args.name, args.window_id))
