#!/usr/bin/env python3
"""One bounded native lifecycle; evidence stays under the explicit external root.

Exit 0 means this lifecycle passed, not that GUI/features were verified. Exit 1
means failure; exit 2 means preflight blocked. Never sends termination signals.
"""
import argparse
import ctypes
import hashlib
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
COMMAND_DEADLINE = None


def command(*args):
    timeout = 5 if COMMAND_DEADLINE is None else min(5, COMMAND_DEADLINE - time.monotonic())
    if timeout <= 0:
        raise TimeoutError('Lifecycle hard deadline reached')
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          timeout=timeout, env={**os.environ, 'LC_ALL': 'C'}).stdout


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
    profile = Path(tempfile.mkdtemp(prefix='test-profile-r5-', dir=root))
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


def native_application(original, rows, request=False):
    current = next((r for r in rows if identity(r) == identity(original)), None)
    if not current or 'U' in current['state']:
        raise ValueError('Quit refused: process identity absent/changed or uninterruptible')
    # NSRunningApplication targets the existing PID and executable, never launches
    # an installed bundle. terminate is a normal application Quit request.
    script = '''ObjC.import('AppKit');
function run(args) {
  const app = $.NSRunningApplication.runningApplicationWithProcessIdentifier(Number(args[0]));
  if (app.isNil()) return 'unregistered';
  if (app.terminated) return 'exiting';
  if (app.executableURL.isNil() || ObjC.unwrap(app.executableURL.path) !== args[1])
    return 'identity_mismatch';
  if (!app.finishedLaunching) return 'registered';
  if (args[2] !== 'quit') return 'ready';
  // JXA invokes zero-argument Objective-C selectors on property access.
  const accepted = app.terminate;
  if (typeof accepted !== 'boolean') throw Error('Non-Boolean Quit response');
  return accepted === true ? 'accepted' : 'refused';
}'''
    output = command('/usr/bin/osascript', '-l', 'JavaScript', '-e', script,
                     str(original['pid']), original['executable'],
                     'quit' if request else 'inspect').strip()
    if output not in ('unregistered', 'registered', 'ready', 'exiting', 'accepted', 'refused'):
        raise ValueError('Invalid native application identity/response: ' + repr(output))
    return output


def native_quit(original, rows):
    return native_application(original, rows, request=True)


def classify(exit_code, quit_requested, failure, watchdog, remaining):
    if exit_code is None and not quit_requested and not failure and not watchdog and not remaining:
        return 'NOT TESTED'
    return ('PASS' if exit_code == 0 and quit_requested and not failure and
            not watchdog and not remaining else 'FAIL')


def supervise(process, profile, run, seconds, grace, sample, guard, quit_app,
              clock=time.monotonic, sleep=time.sleep, interrupted=lambda: False,
              inspect_app=None, started=None, initial_failure=None, evidence_guard=None):
    start = clock() if started is None else started
    deadline = start + seconds
    finish = deadline + grace
    known, u_since = set(), {}
    original = None
    result = dict(pid=process.pid, exit_code=None, quit_requested=False,
                  quit_attempts=0, quit_errors=[], failure=initial_failure,
                  uninterruptible_observed=False, persistent_uninterruptible=False,
                  remaining=[], events=[])
    next_quit, last = deadline, start
    native_state = None
    exit_recorded = False
    helpers_verified = False

    def save(name, value):
        try:
            if evidence_guard:
                evidence_guard()
            with (run / name).open('a') as out:
                out.write(json.dumps(value) + '\n')
        except Exception as exc:
            result['failure'] = result['failure'] or 'evidence_write_failed: ' + str(exc)

    def event(name, **details):
        value = dict(event=name, elapsed=clock()-start, time_unix=time.time(),
                     pid=process.pid, browser_identity=original, **details)
        result['events'].append(value)
        save('events.jsonl', value)

    event('process_spawned')
    while True:
        # Poll before potentially failing inspection, retaining direct-child ownership.
        result['exit_code'] = process.poll()
        if result['exit_code'] is not None and not exit_recorded:
            event('browser_exited', exit_code=result['exit_code'])
            exit_recorded = True
        now = clock()
        if now >= finish:
            if now - last > 15:
                result['failure'] = result['failure'] or 'observation_delayed'
                event('observation_delayed', interval=now-last)
            result['failure'] = result['failure'] or 'lifecycle_timeout'
            event('timeout_reached', cleanup_required=result['exit_code'] is None or bool(result['remaining']))
            break
        try:
            resources = guard()
            rows = sample()
            now = clock()
            owned = owned_processes(rows, profile, known)
            result['remaining'] = owned
            if original is None:
                original = next((r for r in owned if r['pid'] == process.pid), None)
                if original:
                    result['browser_identity'] = original
                    event('process_identity_verified')
            active_u = {identity(r) for r in owned if 'U' in r['state']}
            for key in active_u:
                result['uninterruptible_observed'] = True
                if key not in u_since:
                    u_since[key] = now
                    event('uninterruptible_started', process_identity=key)
                elif now - u_since[key] >= 15 and not result['persistent_uninterruptible']:
                    result['persistent_uninterruptible'] = True
                    result['failure'] = result['failure'] or 'persistent_uninterruptible_process'
                    event('persistent_uninterruptible', process_identity=key, observed_span=now-u_since[key])
            for key in list(u_since):
                if key not in active_u:
                    event('uninterruptible_ended', process_identity=key, observed_span=now-u_since.pop(key))
            if len(owned) != len(rows):
                result['failure'] = result['failure'] or 'unexpected_compiled_app_process'
            if now - last > 15:
                result['failure'] = result['failure'] or 'observation_delayed'
                event('observation_delayed', interval=now-last)
            if interrupted():
                result['failure'] = result['failure'] or 'supervisor_interrupted'
                next_quit = min(next_quit, now)
            save('samples.jsonl', dict(elapsed=now-start, processes=owned,
                 resources=resources if isinstance(resources, dict) else None,
                 exit_code=process.poll()))
            # A command that consumed the budget cannot authorize a late Quit.
            if clock() >= finish:
                continue
            if process.poll() is not None:
                if not owned:
                    if not exit_recorded:
                        event('browser_exited', exit_code=process.poll())
                        exit_recorded = True
                    event('helpers_exited')
                    helpers_verified = True
                    break
            elif original and not active_u:
                if inspect_app and native_state != 'ready':
                    state = inspect_app(original, sample())
                    if state != native_state:
                        if state == 'ready' and native_state != 'registered':
                            event('browser_registered')
                        event({'registered': 'browser_registered', 'ready': 'browser_ready_for_native_quit'}.get(
                            state, 'application_' + state))
                    native_state = state
                if (next_quit <= clock() < finish and not result['quit_requested'] and
                        result['quit_attempts'] < 2 and
                        (inspect_app is None or native_state == 'ready')):
                    fresh = sample()
                    if clock() < finish and not any('U' in r['state'] for r in fresh):
                        result['quit_attempts'] += 1
                        event('quit_requested', attempt=result['quit_attempts'])
                        try:
                            response = quit_app(original, fresh)
                            if response not in ('accepted', 'refused', 'registered', 'unregistered', 'exiting'):
                                raise ValueError('Unexpected native Quit result')
                            event('quit_' + response)
                            if response == 'accepted':
                                result['quit_requested'] = True
                                result['quit_elapsed'] = clock() - start
                            else:
                                result['quit_errors'].append(response)
                                native_state = None
                        except Exception as exc:
                            result['quit_errors'].append(str(exc))
                            result['failure'] = result['failure'] or 'native_quit_failed'
                            event('quit_error', reason=str(exc))
                        next_quit = clock() + 5
            last = now
        except Exception as exc:
            # Inspection failures invalidate PASS but do not abandon a live child.
            result['failure'] = result['failure'] or str(exc)
            event('monitor_error', reason=str(exc))
        sleep(min(2, max(0, finish - clock())))
    result['exit_code'] = process.poll()
    if result['exit_code'] is not None and not exit_recorded:
        event('browser_exited', exit_code=result['exit_code'])
    result['elapsed_seconds'] = clock() - start
    result['cleanup_required'] = result['exit_code'] is None or not helpers_verified
    return result


R4_MARKER_SHA256 = 'c2c2c21b47a933abcf91fc90aaa3573f3863fa6bc642ed7302deea5f2807ad5c'


def review_r4_marker(root, latch, rows):
    """Only the exact R4 failure reviewed by R5 is eligible, never future failures."""
    if rows:
        raise ValueError('Previous compiled browser/helpers remain')
    raw = latch.read_bytes()
    if hashlib.sha256(raw).hexdigest() != R4_MARKER_SHA256:
        raise ValueError('Marker differs from the reviewed R4 failure')
    marker = json.loads(raw)
    evidence = contained(root, Path(marker['evidence']).relative_to(root))
    result = json.loads((evidence / 'result.json').read_text())
    launch = json.loads((evidence / 'launch.json').read_text())
    cleanup = json.loads((evidence / 'cleanup-result.json').read_text())
    if (result != marker['result'] or result['clean_shutdown'] != 'FAIL' or
            result['pid'] != launch['pid'] or result['profile'] != launch['profile'] or
            cleanup['remaining_processes'] != [] or not (evidence / 'samples.jsonl').is_file() or
            not (evidence / 'browser.log').is_file()):
        raise ValueError('R4 evidence does not validate the reviewed marker')
    archive = contained(root, 'logs/TrinolLifecycle.r4-reviewed.json')
    if archive.exists():
        raise ValueError('R5 reviewed retry already consumed')
    return dict(archive=str(archive), marker_sha256=R4_MARKER_SHA256,
                previous_evidence=str(evidence), authorization='Phase 1C-R5 section 8, one reviewed retry')


def arm_latch(latch, run, retry):
    record = dict(evidence=str(run), state='in_progress', reviewed_retry=retry)
    if retry:
        if hashlib.sha256(latch.read_bytes()).hexdigest() != retry['marker_sha256']:
            raise ValueError('Reviewed marker changed before archival')
        # Preserve original bytes and atomically replace the guard: never a clear gap.
        os.link(latch, retry['archive'])
        temporary = run / 'new-marker.json'
        temporary.write_text(json.dumps(record) + '\n')
        os.replace(temporary, latch)
    else:
        with latch.open('x') as out:
            out.write(json.dumps(record) + '\n')


def main():
    global COMMAND_DEADLINE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', required=True, type=Path)
    parser.add_argument('--volume-uuid', required=True)
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--grace-seconds', type=int, default=30)
    parser.add_argument('--reviewed-r4-retry', action='store_true',
                        help='Consume only the exact failure reviewed by Phase 1C-R5')
    parser.add_argument('--workload', choices=('blank', 'browsing'), default='blank')
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
            rows = snapshot(app)
            retry = review_r4_marker(root, latch, rows) if args.reviewed_r4_retry else None
            if latch.exists() and not retry:
                raise ValueError('Prior lifecycle failure requires review: ' + str(latch))
            if rows:
                raise ValueError('Existing compiled-app processes; no overlapping launch')
            processes = command('/bin/ps', '-axo', 'comm=')
            if any(Path(p.strip()).name in ('siso', 'ninja', 'autoninja', 'clang', 'clang++')
                   for p in processes.splitlines()):
                raise ValueError('A compiler/build process is active')
            baseline = memory(probe)
            if baseline['pressure'] != 1:
                raise ValueError('Normal idle memory pressure required')
            run = Path(tempfile.mkdtemp(prefix='phase1cr5-lifecycle-', dir=logs))
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
            if args.workload == 'browsing':
                fixture = run / 'rendering.html'
                fixture.write_text('<!doctype html><title>R5 loading</title><h1>R5 local HTML</h1>'
                    '<p id="result">Pending JavaScript</p><script>'
                    'document.querySelector("#result").textContent="PASS: JavaScript DOM updated";'
                    'document.title="R5 JavaScript PASS";</script>')
                argv[-1:] = [fixture.as_uri(), 'https://example.com/']
            interrupted = []
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda *_: interrupted.append(True))
            guard()
            # A crash of this supervisor must also block the next launch.
            arm_latch(latch, run, retry)
            print('Evidence: ' + str(run), flush=True)
            with (run / 'browser.log').open('x') as log:
                started = time.monotonic()
                COMMAND_DEADLINE = started + args.seconds + args.grace_seconds
                # Bound each runtime probe by both five seconds and the run deadline.
                probe.command = lambda *a: command(*a).encode()
                process = subprocess.Popen(argv, env=launch_environment(crash),
                                           stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                launch_failure = None
                try:
                    (run / 'launch.json').write_text(json.dumps(dict(command=argv,
                        pid=process.pid, profile=str(profile), crash_directory=str(crash),
                        start_time_unix=time.time(), seconds=args.seconds,
                        grace_seconds=args.grace_seconds, baseline_memory=baseline,
                        volume_uuid=args.volume_uuid, reviewed_retry=retry,
                        workload=args.workload), indent=2) + '\n')
                except Exception as exc:
                    launch_failure = 'launch_evidence_failed: ' + str(exc)
                result = supervise(process, profile, run, args.seconds, args.grace_seconds,
                                   lambda: snapshot(app), guard, native_quit,
                                   interrupted=lambda: bool(interrupted),
                                   inspect_app=native_application, started=started,
                                   initial_failure=launch_failure,
                                   evidence_guard=lambda: assert_mount(root, Path(volume.mount), device))
            COMMAND_DEADLINE = None
            assert_mount(root, Path(volume.mount), device)
            result['watchdog'] = WATCHDOG in (run / 'browser.log').read_text(errors='replace').lower()
            if result['watchdog']:
                event = dict(event='watchdog_detected_in_log', time_unix=time.time(),
                             elapsed=time.monotonic()-started, pid=process.pid,
                             browser_identity=result.get('browser_identity'))
                result.setdefault('events', []).append(event)
                with (run / 'events.jsonl').open('a') as events:
                    events.write(json.dumps(event) + '\n')
            result['dumps'] = [str(p.relative_to(profile)) for p in crash.rglob('*.dmp')]
            if result['dumps']:
                result['failure'] = result['failure'] or 'crash_dump_created'
            result['clean_shutdown'] = classify(result['exit_code'], result['quit_requested'],
                result['failure'], result['watchdog'], result['remaining'])
            result['gui_and_functional_tests'] = 'NOT TESTED'
            result['profile'] = str(profile)
            if result.get('cleanup_required'):
                result['operator_action'] = 'Immediate supervised native GUI cleanup required; no new launch'
            (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            if result['clean_shutdown'] != 'PASS':
                latch.write_text(json.dumps(dict(evidence=str(run), result=result), indent=2) + '\n')
            else:
                latch.unlink()
            print(json.dumps(result), flush=True)
            return 0 if result['clean_shutdown'] == 'PASS' else 1
    except Exception as exc:
        print(json.dumps(dict(outcome='blocked' if process is None else 'monitor_failure',
                              reason=str(exc), pid=process.pid if process else None,
                              exit_code=process.poll() if process else None,
                              cleanup_required=process is not None and process.poll() is None)), flush=True)
        return 2 if process is None else 1
    finally:
        COMMAND_DEADLINE = None


if __name__ == '__main__':
    raise SystemExit(main())
