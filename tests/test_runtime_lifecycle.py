"""Offline lifecycle tests: no real browsers, GUI requests or signals."""
import json
import os
from pathlib import Path
import plistlib
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import test_chromium_lifecycle_macos as life


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.profile = self.root / 'profile'
        self.app = self.root / life.APP
        self.exe = self.root / life.EXE

    def row(self, **changes):
        return dict(dict(pid=123, ppid=1, state='S', start='Wed Oct 21 13:00:00 2026',
                         executable=str(self.exe),
                         command=str(self.exe) + ' --user-data-dir=' + str(self.profile)),
                    **changes)

    def artifact(self):
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(struct.pack('<III', 0xfeedfacf, 0x100000c, 0))
        self.exe.chmod(0o700)
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps(dict(
            CFBundleShortVersionString='1.2.3.4', CFBundleIdentifier='org.chromium.Chromium',
            CFBundleExecutable='Chromium')))

    def test_exact_native_executable(self):
        self.artifact()
        self.assertEqual(life.verify_executable(self.root, '1.2.3.4'), self.exe)

    def test_missing_executable(self):
        with self.assertRaises(ValueError): life.verify_executable(self.root, '1.2.3.4')

    def test_wrong_architecture_version_and_permission(self):
        self.artifact()
        with self.assertRaises(ValueError): life.verify_executable(self.root, '9.0.0.0')
        self.exe.write_bytes(b'not a Mach-O')
        with self.assertRaises(ValueError): life.verify_executable(self.root, '1.2.3.4')
        self.exe.chmod(0o600)
        with self.assertRaises(ValueError): life.verify_executable(self.root, '1.2.3.4')

    def test_symlink_executable_escape(self):
        self.artifact()
        self.exe.unlink()
        self.exe.symlink_to('/bin/sh')
        with self.assertRaises(ValueError): life.verify_executable(self.root, '1.2.3.4')

    def test_fresh_isolated_profiles_and_crash_paths(self):
        p1, c1 = life.isolated_profile(self.root)
        p2, c2 = life.isolated_profile(self.root)
        self.assertNotEqual(p1, p2)
        self.assertTrue(c1.is_relative_to(p1) and c2.is_relative_to(p2))
        self.assertEqual(p1.stat().st_mode & 0o777, 0o700)
        with patch.dict(os.environ, {'DYLD_INSERT_LIBRARIES': 'bad', 'CHROME_LOG_FILE': 'bad'}):
            env = life.launch_environment(c1)
        self.assertEqual(env['BREAKPAD_DUMP_LOCATION'], str(c1))
        self.assertNotIn('DYLD_INSERT_LIBRARIES', env)
        self.assertNotIn('CHROME_LOG_FILE', env)

    def test_process_parser_uses_kernel_executable(self):
        text = f'123 1 S Wed Oct 21 13:00:00 2026 1.2 300 {self.exe} --foo\n'
        self.assertEqual(life.parse_processes(text, self.app, lambda _: str(self.exe))[0]['pid'], 123)
        self.assertEqual(life.parse_processes(text, self.app, lambda _: '/bin/sh'), [])
        self.assertEqual(life.parse_processes(text, self.app, lambda _: ''), [])

    def test_pid_reuse_not_ownership(self):
        original = self.row()
        replacement = self.row(start='new start', command='different profile')
        self.assertEqual(life.owned_processes([replacement], self.profile,
                         {life.identity(original)}), [])

    def test_helpers_and_crashpad_without_shared_group(self):
        browser = self.row()
        child = self.row(pid=124, ppid=123, command='helper')
        crash = self.row(pid=125, ppid=1, command='handler --database=' +
                        str(self.profile / 'Crashpad-isolated'))
        unrelated = self.row(pid=126, command='another --user-data-dir=/personal')
        known = set()
        self.assertEqual({r['pid'] for r in life.owned_processes(
            [browser, child, crash, unrelated], self.profile, known)}, {123, 124, 125})
        self.assertEqual(life.owned_processes([dict(child, ppid=1)], self.profile, known),
                         [dict(child, ppid=1)])

    def test_native_quit_refuses_reused_pid_or_uninterruptible(self):
        with patch.object(life, 'command') as cmd:
            for rows in [[], [self.row(start='changed')], [self.row(state='U')]]:
                with self.assertRaises(ValueError): life.native_quit(self.row(), rows)
            cmd.assert_not_called()

    def test_native_quit_targets_existing_pid_and_exact_executable(self):
        with patch.object(life, 'command', return_value='requested\n') as cmd:
            life.native_quit(self.row(), [self.row()])
            self.assertEqual(cmd.call_args.args[-2:], ('123', str(self.exe)))
            self.assertIn('NSRunningApplication', cmd.call_args.args[4])

    def simulate(self, exit_at=None, code=0, state='S', guard=None, helpers=False,
                 interruption=False, delay=False, quit_error=False):
        now = [0.0]
        process = Mock(pid=123)
        process.poll.side_effect = lambda: code if exit_at is not None and now[0] >= exit_at else None
        def sample():
            if process.poll() is None:
                return [self.row(state=state)]
            return [self.row(pid=124, ppid=1, command='handler --database=' +
                    str(self.profile / 'Crashpad-isolated'))] if helpers else []
        quit_app = Mock(side_effect=ValueError('quit failed') if quit_error else None)
        def sleep(seconds): now[0] += 20 if delay else seconds
        result = life.supervise(process, self.profile, self.root, 10, 10, sample,
            guard or Mock(), quit_app, clock=lambda: now[0], sleep=sleep,
            interrupted=lambda: interruption)
        return result, quit_app

    def test_genuine_zero_exit_after_quit(self):
        result, quit_app = self.simulate(exit_at=12)
        self.assertEqual(result['exit_code'], 0)
        self.assertIsNone(result['failure'])
        self.assertEqual(result['quit_elapsed'], 10)
        quit_app.assert_called_once()

    def test_genuine_nonzero_exit_preserved(self):
        result, _ = self.simulate(exit_at=12, code=2)
        self.assertEqual(result['exit_code'], 2)

    def test_independent_exit_not_clean_quit_pass(self):
        result, quit_app = self.simulate(exit_at=4)
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['quit_requested'])
        quit_app.assert_not_called()

    def test_timeout_is_bounded_without_signals(self):
        with patch('os.kill') as kill, patch('os.killpg') as killpg:
            result, quit_app = self.simulate()
        self.assertEqual(result['elapsed_seconds'], 20)
        self.assertEqual(result['failure'], 'lifecycle_timeout')
        self.assertIsNone(result['exit_code'])
        quit_app.assert_called_once()
        kill.assert_not_called(); killpg.assert_not_called()

    def test_uninterruptible_never_signalled_or_quit(self):
        result, quit_app = self.simulate(state='Us')
        self.assertTrue(result['uninterruptible_observed'])
        self.assertEqual(result['elapsed_seconds'], 20)
        quit_app.assert_not_called()

    def test_helper_leftover_fails(self):
        result, _ = self.simulate(exit_at=12, helpers=True)
        self.assertEqual(result['failure'], 'lifecycle_timeout')
        self.assertTrue(result['remaining'])

    def test_monitor_failure_does_not_guess_target(self):
        result, quit_app = self.simulate(guard=Mock(side_effect=ValueError('mount changed')))
        self.assertEqual(result['failure'], 'mount changed')
        quit_app.assert_not_called()

    def test_interrupt_requests_graceful_quit_and_fails(self):
        result, quit_app = self.simulate(exit_at=2, interruption=True)
        quit_app.assert_called_once()
        self.assertEqual(result['failure'], 'supervisor_interrupted')

    def test_delayed_observation_fails(self):
        result, _ = self.simulate(delay=True)
        self.assertEqual(result['failure'], 'observation_delayed')

    def test_delayed_sample_does_not_quit_during_startup(self):
        now = [0]
        calls = []
        process = Mock(pid=123, poll=Mock(return_value=None))
        def sleep(_): now[0] += 20
        life.supervise(process, self.profile, self.root, 45, 30,
            lambda: [self.row()], Mock(), lambda *_: calls.append(now[0]),
            clock=lambda: now[0], sleep=sleep)
        self.assertEqual(calls, [60])

    def test_quit_error_is_not_pass(self):
        result, quit_app = self.simulate(quit_error=True)
        self.assertEqual(result['failure'], 'native_quit_failed')
        self.assertEqual(result['elapsed_seconds'], 20)
        self.assertEqual(quit_app.call_count, 2)
        self.assertEqual(result['quit_errors'], ['quit failed', 'quit failed'])

    def test_quit_refusal_still_reaps_later_real_exit(self):
        result, _ = self.simulate(exit_at=14, code=2, quit_error=True)
        self.assertEqual(result['exit_code'], 2)
        self.assertEqual(result['failure'], 'native_quit_failed')
        self.assertEqual(result['elapsed_seconds'], 14)

    def test_quit_retry_has_backoff_and_absolute_bound(self):
        now = [0]
        calls = []
        process = Mock(pid=123, poll=Mock(return_value=None))
        def quit_app(*_):
            calls.append(now[0])
            raise ValueError('refused')
        result = life.supervise(process, self.profile, self.root, 10, 10,
            lambda: [self.row()], Mock(), quit_app, clock=lambda: now[0],
            sleep=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertEqual(calls, [10, 16])
        self.assertEqual(result['elapsed_seconds'], 20)

    def test_classification_watchdog_and_unrun(self):
        self.assertEqual(life.classify(None, False, None, False, []), 'NOT TESTED')
        self.assertEqual(life.classify(0, True, None, False, []), 'PASS')
        for args in [(0, True, None, True, []), (2, True, None, False, []),
                     (None, False, None, True, []),
                     (0, False, None, False, []), (0, True, 'U', False, []),
                     (0, True, None, False, [self.row()])]:
            self.assertEqual(life.classify(*args), 'FAIL')

    def test_build_lock_prevents_overlap_and_rejects_symlink(self):
        (self.root / 'logs').mkdir()
        with life.build_lock(self.root):
            with self.assertRaises(ValueError):
                with life.build_lock(self.root): self.fail('overlap')
        lock = self.root / 'logs/TrinolDev.lock'
        lock.unlink(); lock.symlink_to(self.root / 'other')
        with self.assertRaises(ValueError):
            with life.build_lock(self.root): self.fail('symlink')

    def test_storage_uuid_filesystem_writable_and_floor(self):
        volume = SimpleNamespace(filesystem='apfs', writable=True, device='disk7s2',
                                 mount='/Volumes/test')
        probe = Mock(volume=Mock(return_value=volume),
                     disk=Mock(return_value={'VolumeUUID': 'expected'}))
        with patch.object(life, 'capacity', return_value=100*life.GIB), \
                patch.object(life, 'assert_mount'):
            self.assertEqual(life.inspect_storage(self.root, 'expected', probe), volume)
            with self.assertRaises(ValueError): life.inspect_storage(self.root, 'wrong', probe)
            volume.filesystem = 'hfs'
            with self.assertRaises(ValueError): life.inspect_storage(self.root, 'expected', probe)
            volume.filesystem = 'apfs'; volume.writable = False
            with self.assertRaises(ValueError): life.inspect_storage(self.root, 'expected', probe)
            volume.writable = True
            with patch.object(life, 'capacity', return_value=60*life.GIB):
                with self.assertRaises(ValueError): life.inspect_storage(self.root, 'expected', probe)

    def run_main(self, rows=(), latch=False, outcome='PASS'):
        from contextlib import ExitStack
        (self.root / 'logs').mkdir()
        marker = self.root / 'logs/TrinolLifecycle.blocked.json'
        if latch:
            marker.write_text('{}')
        volume = SimpleNamespace(device='disk7s2', mount=str(self.root))
        probe = Mock(disk=Mock(return_value={'VolumeUUID': 'expected'}))
        result = dict(exit_code=0, quit_requested=True,
                      failure=None if outcome == 'PASS' else 'watchdog', remaining=[])
        with ExitStack() as stack:
            for target, value in [('platform.system', 'Darwin'), ('platform.machine', 'arm64'),
                                  ('inspect_storage', volume), ('verify', []),
                                  ('verify_executable', self.exe), ('snapshot', list(rows)),
                                  ('command', ''), ('MacProbe', probe), ('memory',
                                   {'pressure': 1, 'swap_bytes': 0}), ('supervise', result),
                                  ('assert_mount', None)]:
                stack.enter_context(patch.object(life, target, return_value=value)
                    if '.' not in target else patch('test_chromium_lifecycle_macos.' + target,
                                                   return_value=value))
            stack.enter_context(patch.object(life.os, 'statvfs', return_value=
                                            SimpleNamespace(f_bavail=100*life.GIB, f_frsize=1)))
            stack.enter_context(patch.object(life.signal, 'signal'))
            stack.enter_context(patch('builtins.print'))
            stack.enter_context(patch.object(sys, 'argv', ['lifecycle', '--build-root',
                                     str(self.root), '--volume-uuid', 'expected']))
            popen = stack.enter_context(patch.object(life.subprocess, 'Popen',
                                                    return_value=Mock(pid=123)))
            code = life.main()
            calls = popen.call_count
        return code, marker, calls

    def test_main_failure_latches_subsequent_launches(self):
        code, marker, calls = self.run_main(outcome='FAIL')
        self.assertEqual((code, calls), (1, 1))
        self.assertTrue(marker.exists())

    def test_main_pass_clears_only_its_in_progress_latch(self):
        code, marker, calls = self.run_main()
        self.assertEqual((code, calls), (0, 1))
        self.assertFalse(marker.exists())

    def test_main_existing_failure_refuses_launch(self):
        code, marker, calls = self.run_main(latch=True)
        self.assertEqual((code, calls), (2, 0))
        self.assertTrue(marker.exists())

    def test_main_existing_browser_refuses_launch(self):
        code, _, calls = self.run_main(rows=[self.row()])
        self.assertEqual((code, calls), (2, 0))


if __name__ == '__main__':
    unittest.main()
