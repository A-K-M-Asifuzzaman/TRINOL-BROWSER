#!/usr/bin/env python3
"""One bounded native lifecycle; evidence stays under the explicit external root.

Exit 0 means this lifecycle passed, not that GUI/features were verified. Exit 1
means failure; exit 2 means preflight blocked. Never sends termination signals.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import plistlib
import signal
import struct
import subprocess
import tempfile
import time

from build_chromium_macos import assert_mount, build_lock, contained, memory
from check_chromium_build_storage import GIB, InspectionError, MacProbe, capacity
from verify_upstream_checkout import ROOT, verify

APP = 'chromium/src/out/TrinolDev/Chromium.app'
EXE = APP + '/Contents/MacOS/Chromium'
WATCHDOG = 'watchdog expired;'


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          timeout=5, env={**os.environ, 'LC_ALL': 'C'}).stdout


def verify_executable(root, version):
    exe = contained(root, EXE)
    if not exe.is_file() or not os.access(exe, os.X_OK):
        raise ValueError('Missing executable')
    with exe.open('rb') as stream:
        header = stream.read(12)
    if len(header) != 12 or struct.unpack('<III', header) != (0xfeedfacf, 0x100000c, 0):
        raise ValueError('Expected thin native arm64 Mach-O launcher')
    info = plistlib.loads(contained(root, APP + '/Contents/Info.plist').read_bytes())
    if (info.get('CFBundleShortVersionString') != version or
            info.get('CFBundleExecutable') != 'Chromium' or
            info.get('CFBundleIdentifier') != 'org.chromium.Chromium'):
        raise ValueError('Unexpected bundle identity/version')
    return exe


def inspect_storage(root, expected_uuid, probe):
    if root != root.resolve(strict=True) or root.is_relative_to(ROOT):
        raise ValueError('Build root must be canonical and outside product Git')
    volume = probe.volume(root)
    info = probe.disk(volume.device)
    if (volume.filesystem != 'apfs' or not volume.writable or
            info.get('VolumeUUID') != expected_uuid or
            not Path(volume.mount).is_relative_to('/Volumes')):
        raise ValueError('Unexpected writable external APFS volume/UUID')
    free = capacity(volume, probe, probe.images(), lambda *_: None)
    if free <= 60 * GIB:
        raise ValueError('Insufficient physical storage headroom')
    assert_mount(root, Path(volume.mount), root.stat().st_dev)
    return volume


def isolated_profile(root):
    profile = Path(tempfile.mkdtemp(prefix='test-profile-r4-', dir=root))
    contained(root, profile.relative_to(root))
    crash = profile / 'Crashpad-isolated'
    crash.mkdir(mode=0o700)
    return profile, crash


def launch_environment(crash):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('DYLD_', 'LD_', 'CHROME_', 'CHROMIUM_')):
            env.pop(key)
    # chrome/app/chrome_crash_reporter_client.cc supports this override.
    env['BREAKPAD_DUMP_LOCATION'] = str(crash)
    return env


def executable_path(pid):
    lib = ctypes.CDLL('/usr/lib/libproc.dylib')
    lib.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    lib.proc_pidpath.restype = ctypes.c_int
    buf = ctypes.create_string_buffer(4096)
    return os.fsdecode(buf.value) if lib.proc_pidpath(pid, buf, len(buf)) > 0 else ''


def parse_processes(text, app, path_for_pid):
    rows = []
    for line in text.splitlines():
        parts = line.split(None, 10)
        if len(parts) != 11 or str(app) not in parts[10]:
            continue
        pid = int(parts[0])
        exe = path_for_pid(pid)
        if not exe or not Path(exe).is_relative_to(app):
            continue
        rows.append(dict(pid=pid, ppid=int(parts[1]), state=parts[2],
                         start=' '.join(parts[3:8]), cpu=float(parts[8]),
                         rss_kib=int(parts[9]), executable=exe, command=parts[10]))
    return rows


def snapshot(app):
    return parse_processes(command('/bin/ps', '-axo',
                                   'pid=,ppid=,state=,lstart=,pcpu=,rss=,command='),
                           app, executable_path)


def identity(row):
    return row['pid'], row['start'], row['executable']


def owned_processes(rows, profile, known):
    owned = []
    for row in rows:
        args = row['command'].split()
        if (identity(row) in known or
                '--user-data-dir=' + str(profile) in args or
                '--database=' + str(profile / 'Crashpad-isolated') in args):
            owned.append(row)
    # Only descendants of currently matched identities are adopted, never PGID.
    while True:
        parents = {r['pid'] for r in owned}
        extra = [r for r in rows if r not in owned and r['ppid'] in parents]
        if not extra:
            break
        owned.extend(extra)
    known.update(identity(r) for r in owned)
    return owned


def native_quit(original, rows):
    current = next((r for r in rows if identity(r) == identity(original)), None)
    if not current or 'U' in current['state']:
        raise ValueError('Quit refused: process identity absent/changed or uninterruptible')
    # NSRunningApplication targets the existing PID and executable, never launches
    # an installed bundle. terminate is a normal application Quit request.
    script = '''ObjC.import('AppKit');
function run(args) {
  const app = $.NSRunningApplication.runningApplicationWithProcessIdentifier(Number(args[0]));
  if (!app || !app.executableURL || ObjC.unwrap(app.executableURL.path) !== args[1])
    throw Error('Application identity changed');
  return app.terminate ? 'requested' : 'refused';
}'''
    output = command('/usr/bin/osascript', '-l', 'JavaScript', '-e', script,
                     str(original['pid']), original['executable']).strip()
    if output != 'requested':
        raise ValueError('Native Quit was refused: ' + repr(output))


def classify(exit_code, quit_requested, failure, watchdog, remaining):
    if exit_code is None and not quit_requested and not failure and not watchdog and not remaining:
        return 'NOT TESTED'
    return ('PASS' if exit_code == 0 and quit_requested and not failure and
            not watchdog and not remaining else 'FAIL')


def supervise(process, profile, run, seconds, grace, sample, guard, quit_app,
              clock=time.monotonic, sleep=time.sleep, interrupted=lambda: False):
    start = clock()
    deadline = start + seconds
    finish = deadline + grace
    known = set()
    original = None
    result = dict(pid=process.pid, exit_code=None, quit_requested=False,
                  quit_attempts=0, quit_errors=[], failure=None,
                  uninterruptible_observed=False, remaining=[])
    next_quit = deadline
    last = start
    with (run / 'samples.jsonl').open('x') as output:
        while True:
            now = clock()
            try:
                resources = guard()
                rows = sample()
                now = clock()
                owned = owned_processes(rows, profile, known)
                result['remaining'] = owned
                result['exit_code'] = process.poll()
                if original is None:
                    original = next((r for r in owned if r['pid'] == process.pid), None)
                    if original:
                        result['browser_identity'] = original
                if any('U' in r['state'] for r in owned):
                    result.update(uninterruptible_observed=True,
                                  failure='uninterruptible_process_observed')
                if len(owned) != len(rows):
                    result['failure'] = 'unexpected_compiled_app_process'
                if now - last > 15:
                    result['failure'] = 'observation_delayed'
                if interrupted():
                    result['failure'] = 'supervisor_interrupted'
                output.write(json.dumps(dict(elapsed=now-start, processes=owned,
                    resources=resources if isinstance(resources, dict) else None,
                    exit_code=result['exit_code'])) + '\n')
                output.flush()
                if result['failure']:
                    # A transient U state blocks future trials, but must not
                    # trigger Quit before this instance finishes starting.
                    if result['failure'] in ('supervisor_interrupted',
                                             'unexpected_compiled_app_process'):
                        deadline = min(deadline, now)
                        next_quit = min(next_quit, now)
                        finish = min(finish, now + grace)
                if result['exit_code'] is not None:
                    if not owned:
                        break
                    finish = min(finish, now + grace)
                elif (next_quit <= now < finish and not result['quit_requested'] and
                      result['quit_attempts'] < 2):
                    if original and not any('U' in r['state'] for r in owned):
                        # Re-read immediately before the identity-checked native call.
                        result['quit_attempts'] += 1
                        try:
                            quit_app(original, sample())
                            result['quit_requested'] = True
                            result['quit_elapsed'] = clock() - start
                        except (ValueError, subprocess.SubprocessError) as exc:
                            result['quit_errors'].append(str(exc))
                            result['failure'] = result['failure'] or 'native_quit_failed'
                            next_quit = clock() + 5
                        # Refusal is not an exit event. Keep supervising/reaping
                        # through the bounded grace period, even after both tries.
                last = now
            except (OSError, ValueError, InspectionError, subprocess.SubprocessError) as exc:
                result['failure'] = str(exc)
                # On inspection/mount failure, preserve the child identity and
                # stop safely: no guessed Quit target, signal or retry loop.
                break
            if now >= finish:
                result['failure'] = result['failure'] or 'lifecycle_timeout'
                break
            sleep(min(2, max(0, finish - clock())))
    result['exit_code'] = process.poll()
    result['elapsed_seconds'] = clock() - start
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', required=True, type=Path)
    parser.add_argument('--volume-uuid', required=True)
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--grace-seconds', type=int, default=30)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 600 or not 10 <= args.grace_seconds <= 60:
        parser.error('Runtime must be 10..600 seconds; exit grace 10..60 seconds')
    process = None
    try:
        if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
            raise ValueError('Native macOS arm64 required')
        root = args.build_root.absolute()
        probe = MacProbe()
        volume = inspect_storage(root, args.volume_uuid, probe)
        manifest = json.loads((ROOT / 'upstream/manifest.json').read_text())
        verify(manifest, root / 'chromium', root / 'depot_tools')
        exe = verify_executable(root, manifest['chromium']['version'])
        app = root / APP
        logs = contained(root, 'logs')
        latch = contained(root, 'logs/TrinolLifecycle.blocked.json')
        # Share the build runner's lock: an authorized build cannot overlap.
        with build_lock(root):
            if latch.exists():
                raise ValueError('Prior lifecycle failure requires review: ' + str(latch))
            if snapshot(app):
                raise ValueError('Existing compiled-app processes; no overlapping launch')
            processes = command('/bin/ps', '-axo', 'comm=')
            if any(Path(p.strip()).name in ('siso', 'ninja', 'autoninja', 'clang', 'clang++')
                   for p in processes.splitlines()):
                raise ValueError('A compiler/build process is active')
            baseline = memory(probe)
            if baseline['pressure'] != 1:
                raise ValueError('Normal idle memory pressure required')
            run = Path(tempfile.mkdtemp(prefix='phase1cr4-lifecycle-', dir=logs))
            profile, crash = isolated_profile(root)
            device = root.stat().st_dev

            def guard():
                assert_mount(root, Path(volume.mount), device)
                if (probe.disk(volume.device).get('VolumeUUID') != args.volume_uuid or
                        os.statvfs(root).f_bavail * os.statvfs(root).f_frsize <= 60 * GIB):
                    raise ValueError('Mount identity/capacity changed')
                mem = memory(probe)
                if mem['pressure'] == 4 or mem['swap_bytes'] - baseline['swap_bytes'] >= 2 * GIB:
                    raise ValueError('Unsafe memory pressure/growth')
                return dict(mem, volume_uuid=args.volume_uuid,
                            available_bytes=os.statvfs(root).f_bavail * os.statvfs(root).f_frsize)

            argv = [str(exe), '--user-data-dir=' + str(profile), '--no-first-run',
                    '--no-default-browser-check', 'about:blank']
            interrupted = []
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda *_: interrupted.append(True))
            guard()
            # A crash of this supervisor must also block the next launch.
            latch.write_text(json.dumps(dict(evidence=str(run), state='in_progress')) + '\n')
            with (run / 'browser.log').open('x') as log:
                process = subprocess.Popen(argv, env=launch_environment(crash),
                                           stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                (run / 'launch.json').write_text(json.dumps(dict(command=argv,
                    pid=process.pid, profile=str(profile), crash_directory=str(crash),
                    start_time_unix=time.time(), seconds=args.seconds,
                    grace_seconds=args.grace_seconds, baseline_memory=baseline,
                    volume_uuid=args.volume_uuid), indent=2) + '\n')
                print('Evidence: ' + str(run), flush=True)
                result = supervise(process, profile, run, args.seconds, args.grace_seconds,
                                   lambda: snapshot(app), guard, native_quit,
                                   interrupted=lambda: bool(interrupted))
            assert_mount(root, Path(volume.mount), device)
            result['watchdog'] = WATCHDOG in (run / 'browser.log').read_text(errors='replace').lower()
            result['dumps'] = [str(p.relative_to(profile)) for p in crash.rglob('*.dmp')]
            if result['dumps']:
                result['failure'] = result['failure'] or 'crash_dump_created'
            result['clean_shutdown'] = classify(result['exit_code'], result['quit_requested'],
                result['failure'], result['watchdog'], result['remaining'])
            result['gui_and_functional_tests'] = 'NOT TESTED'
            result['profile'] = str(profile)
            (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            if result['clean_shutdown'] != 'PASS':
                latch.write_text(json.dumps(dict(evidence=str(run), result=result), indent=2) + '\n')
            else:
                latch.unlink()
            print(json.dumps(result), flush=True)
            return 0 if result['clean_shutdown'] == 'PASS' else 1
    except (OSError, ValueError, InspectionError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(outcome='blocked' if process is None else 'monitor_failure',
                              reason=str(exc), pid=process.pid if process else None)), flush=True)
        return 2 if process is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
