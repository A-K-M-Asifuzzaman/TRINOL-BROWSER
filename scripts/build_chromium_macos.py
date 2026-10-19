#!/usr/bin/env python3
"""Generate or incrementally build the pinned baseline with local resource guards."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import tempfile
import time

from check_chromium_build_storage import GIB, InspectionError, MacProbe, capacity
from verify_upstream_checkout import ROOT, verify

EXPECTED = {'target_os': '"mac"', 'target_cpu': '"arm64"', 'is_debug': 'false',
            'is_component_build': 'true', 'symbol_level': '1',
            'is_official_build': 'false', 'use_remoteexec': 'false'}


def contained(root, relative):
    path = root / relative
    if path.resolve() != path or not path.resolve().is_relative_to(root):
        raise ValueError(f'Symlink or escaped build path: {relative}')
    return path


def environment(root):
    depot = root / 'depot_tools'
    env = os.environ.copy()
    env.update(PATH=str(depot) + os.pathsep + env['PATH'], DEPOT_TOOLS_UPDATE='0',
               DEPOT_TOOLS_METRICS='0', CIPD_CACHE_DIR=str(depot / '.cipd-cache'),
               VPYTHON_VIRTUALENV_ROOT=str(depot / '.vpython-root'),
               XDG_CACHE_HOME=str(depot / '.cache'), TMPDIR=str(root / 'logs/tmp'),
               PYTHONUNBUFFERED='1', NINJA_SUMMARIZE_BUILD='1')
    for key in ('GIT_CACHE_PATH', 'CHROMIUM_OUT_DIR', 'CCACHE_DIR', 'SISO_PATH'):
        env.pop(key, None)
    return env


def parse_memory(pressure, swap):
    level = int(pressure.strip())
    match = re.search(r'used\s*=\s*([0-9.]+)([KMG])', swap)
    if level not in (1, 2, 4) or not match:
        raise ValueError('Unknown memory-pressure or swap output')
    return {'pressure': level, 'swap_bytes': int(float(match[1]) *
            {'K': 1024, 'M': 1024**2, 'G': GIB}[match[2]])}


def memory(probe):
    return parse_memory(probe.command('/usr/sbin/sysctl', '-n',
                                     'kern.memorystatus_vm_pressure_level').decode(),
                        probe.command('/usr/sbin/sysctl', 'vm.swapusage').decode())


def stop_reason(sample, baseline_swap, warning_seconds, jobs, generating=False):
    if sample['free_bytes'] <= 60 * GIB:
        return 'storage_floor'
    if sample['internal_free_bytes'] <= 10 * GIB:
        return 'internal_swap_headroom'
    growth = sample['swap_bytes'] - baseline_swap
    if sample['pressure'] == 4 or growth >= 4 * GIB:
        return 'memory_pressure'
    if not generating and warning_seconds >= 60 and jobs == 4:
        return 'reduce_to_two_jobs'
    if not generating and warning_seconds >= 180 and growth >= 2 * GIB:
        return 'memory_pressure'
    return None


def assert_mount(root, mount, device):
    if not os.path.ismount(mount) or os.stat(mount).st_dev != device or os.stat(root).st_dev != device:
        raise ValueError('Approved volume disconnected or changed')


def stop_process(process):
    for sig, timeout in ((signal.SIGINT, 45), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            pass
    raise RuntimeError('Build process did not stop')


def guarded(command, root, run, volume, probe, jobs, generating):
    mount = Path(volume.mount)
    device = os.stat(mount).st_dev
    baseline = memory(probe)
    warning_start = None
    process = None
    result = {'command': command, 'baseline_memory': baseline, 'state': 'starting'}
    with (run / 'command.log').open('x') as log, (run / 'resources.jsonl').open('x') as samples:
        try:
            while True:
                if process is not None and process.poll() is not None:
                    result.update(state='finished', exit_code=process.returncode)
                    break
                assert_mount(root, mount, device)
                stat = os.statvfs(root)
                internal = os.statvfs('/System/Volumes/Data')
                sample = dict(memory(probe), time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                              free_bytes=stat.f_bavail * stat.f_frsize,
                              internal_free_bytes=internal.f_bavail * internal.f_frsize)
                now = time.monotonic()
                warning = sample['pressure'] >= 2 or sample['swap_bytes'] >= baseline['swap_bytes'] + 2 * GIB
                warning_start = (warning_start if warning_start is not None else now) if warning else None
                reason = stop_reason(sample, baseline['swap_bytes'],
                                     now - warning_start if warning_start is not None else 0,
                                     jobs, generating)
                samples.write(json.dumps(sample) + '\n'); samples.flush()
                result.update(state='running', latest=sample)
                if reason:
                    result.update(state='stopped', reason=reason)
                    break
                if process is None:
                    process = subprocess.Popen(['/usr/bin/caffeinate', '-i', *command],
                        cwd=root / 'chromium/src', env=environment(root), stdout=log,
                        stderr=subprocess.STDOUT, start_new_session=True)
                    result['pid'] = process.pid
                (run / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
                time.sleep(5)
        except BaseException as exc:
            result.update(state='stopped', reason=str(exc))
        finally:
            if process is not None:
                stop_process(process)
                result['exit_code'] = process.returncode
    # Never reopen a log path on a disconnected or replaced mount.
    assert_mount(root, mount, device)
    (run / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return result


def inspect_args(root, run):
    gn = str(root / 'depot_tools/gn')
    kwargs = dict(cwd=root / 'chromium/src', env=environment(root), check=True,
                  capture_output=True, text=True, timeout=180)
    data = json.loads(subprocess.run([gn, 'args', 'out/TrinolDev', '--list', '--json'], **kwargs).stdout)
    values = {entry['name']: entry.get('current', entry['default'])['value'] for entry in data}
    for key, expected in EXPECTED.items():
        if values.get(key) != expected:
            raise ValueError(f'Unexpected effective GN argument {key}: {values.get(key)}')
    if values.get('use_siso') != 'true':
        raise ValueError('Expected hook-configured Siso; investigate before changing executor')
    (run / 'effective-args.json').write_text(json.dumps(values, indent=2) + '\n')
    target = subprocess.run([gn, 'desc', 'out/TrinolDev', '//chrome:chrome', '--format=json'], **kwargs)
    (run / 'chrome-target.json').write_text(target.stdout)
    print('Effective GN arguments:', json.dumps({k: values.get(k) for k in
          (*EXPECTED, 'use_siso', 'use_lld', 'host_os', 'host_cpu')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', required=True, type=Path)
    parser.add_argument('--generate', action='store_true', help='Generate and inspect GN files; do not compile')
    parser.add_argument('--jobs', choices=(2, 4), type=int, default=4)
    args = parser.parse_args()
    try:
        if platform.system() != 'Darwin' or platform.machine() != 'arm64':
            raise ValueError('ENVIRONMENT_MISMATCH: requires native macOS arm64')
        root = args.build_root.expanduser().resolve(strict=True)
        paths = {name: contained(root, name) for name in
                 ('chromium/src', 'chromium/src/out/TrinolDev', 'depot_tools', 'logs', 'logs/tmp',
                  'siso-cache', 'depot_tools/.cipd-cache', 'depot_tools/.vpython-root', 'depot_tools/.cache')}
        manifest = json.loads((ROOT / 'upstream/manifest.json').read_text())
        for line in verify(manifest, root / 'chromium', paths['depot_tools']): print(line, flush=True)
        probe = MacProbe(); volume = probe.volume(root)
        free = capacity(volume, probe, probe.images(), lambda *line: print(*line, flush=True))
        if volume.filesystem != 'apfs' or not volume.writable or not Path(volume.mount).is_mount():
            raise ValueError('Build requires mounted writable APFS')
        output = paths['chromium/src/out/TrinolDev']
        minimum = 250 * GIB if not output.exists() else 60 * GIB
        if free <= minimum:
            raise ValueError(f'Insufficient physical headroom: {free / GIB:.2f} GiB')
        for name in ('logs', 'logs/tmp', 'siso-cache'):
            paths[name].mkdir(exist_ok=True)
        run = Path(tempfile.mkdtemp(prefix='phase1c-' + ('gn-' if args.generate else 'build-'), dir=paths['logs']))
        print('Evidence directory:', run, flush=True)
        (run / 'preflight.json').write_text(json.dumps(vars(volume), indent=2) + '\n')
        if args.generate:
            template = (ROOT / 'config/macos-arm64.args.gn.example').read_text()
            if output.exists() and not (output / 'args.gn').is_file():
                raise ValueError('Existing output has no args.gn; inspect before modifying')
            if (output / 'args.gn').exists() and (output / 'args.gn').read_text() != template:
                raise ValueError('Existing GN arguments differ; preserve and inspect')
            output.mkdir(exist_ok=True)
            if not (output / 'args.gn').exists(): (output / 'args.gn').write_text(template)
            result = guarded([str(paths['depot_tools'] / 'gn'), 'gen', 'out/TrinolDev'],
                             root, run, volume, probe, args.jobs, True)
        else:
            if not (output / 'build.ninja').is_file():
                raise ValueError('GN generation must succeed before compilation')
            inspect_args(root, run)
            result = guarded([str(paths['depot_tools'] / 'autoninja'), '-C', 'out/TrinolDev',
                              '-j', str(args.jobs), '-cache_dir=' + str(paths['siso-cache']), 'chrome'],
                             root, run, volume, probe, args.jobs, False)
        if result['state'] != 'finished' or result.get('exit_code') != 0:
            return 75 if result.get('reason') == 'reduce_to_two_jobs' else 1
        if args.generate: inspect_args(root, run)
        return 0
    except (OSError, ValueError, KeyError, InspectionError, subprocess.SubprocessError) as exc:
        print('BLOCKED:', exc, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
