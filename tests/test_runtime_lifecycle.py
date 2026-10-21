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
            with self.assertRaises(ValueError):
                life.native_quit(self.row(), [self.row(start='changed')])
            self.assertEqual(life.native_quit(self.row(), []), 'exiting')
            self.assertEqual(life.native_quit(self.row(), [self.row(state='U')]), 'uninterruptible')
            cmd.assert_not_called()

    def test_native_quit_targets_existing_pid_and_exact_executable(self):
        with patch.object(life, 'command', return_value='accepted\n') as cmd:
            life.native_quit(self.row(), [self.row()])
            self.assertEqual(cmd.call_args.args[-3:], ('123', str(self.exe), 'quit'))
            self.assertIn('NSRunningApplication', cmd.call_args.args[4])

    def simulate(self, exit_at=None, code=0, state='S', guard=None, helpers=False,
                 interruption=False, delay=False, quit_error=False, quit_results=None,
                 inspect_app=None):
        now = [0.0]
        process = Mock(pid=123)
        process.poll.side_effect = lambda: code if exit_at is not None and now[0] >= exit_at else None
        def sample():
            if process.poll() is None:
                return [self.row(state=state(now[0]) if callable(state) else state)]
            return [self.row(pid=124, ppid=1, command='handler --database=' +
                    str(self.profile / 'Crashpad-isolated'))] if helpers else []
        quit_app = Mock(return_value='accepted', side_effect=ValueError('quit failed') if quit_error else quit_results)
        def sleep(seconds): now[0] += 20 if delay else seconds
        result = life.supervise(process, self.profile, self.root, 10, 10, sample,
            guard or Mock(), quit_app, clock=lambda: now[0], sleep=sleep,
            interrupted=lambda: interruption, inspect_app=inspect_app)
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

    def test_native_status_and_boolean_outcomes(self):
        for state in ('unregistered', 'registered', 'ready', 'exiting', 'accepted', 'refused'):
            with self.subTest(state=state), patch.object(life, 'command', return_value=state) as cmd:
                self.assertEqual(life.native_application(self.row(), [self.row()]), state)
                self.assertEqual(cmd.call_args.args[-1], 'inspect')
                script = cmd.call_args.args[4]
                self.assertIn('app.isNil()', script)
                self.assertIn('const accepted = app.terminate;', script)
                self.assertIn("typeof accepted !== 'boolean'", script)
        for bad in ('identity_mismatch', 'true', 'function', ''):
            with patch.object(life, 'command', return_value=bad):
                with self.assertRaises(ValueError): life.native_quit(self.row(), [self.row()])

    def test_registration_delay_then_ready(self):
        inspect_app = Mock(side_effect=['unregistered', 'registered', 'ready'])
        result, quit_app = self.simulate(exit_at=12, inspect_app=inspect_app)
        self.assertEqual(inspect_app.call_count, 3)
        self.assertEqual(result['quit_elapsed'], 10)
        self.assertIsNone(result['failure'])
        names = [e['event'] for e in result['events']]
        for name in ('process_spawned', 'process_identity_verified', 'browser_registered',
                     'browser_ready_for_native_quit', 'quit_requested', 'quit_accepted',
                     'browser_exited', 'helpers_exited'):
            self.assertIn(name, names)
        self.assertTrue(all('time_unix' in e and 'elapsed' in e and 'pid' in e for e in result['events']))

    def test_registration_never_ready_keeps_observing(self):
        result, quit_app = self.simulate(inspect_app=Mock(return_value='unregistered'))
        self.assertEqual(result['elapsed_seconds'], 20)
        self.assertIsNone(result['exit_code'])
        quit_app.assert_not_called()

    def test_transient_u_during_native_recheck_is_deferred(self):
        result, quit_app = self.simulate(exit_at=12,
            inspect_app=Mock(side_effect=['uninterruptible', 'ready']))
        self.assertIsNone(result['failure'])
        self.assertEqual(result['quit_elapsed'], 10)
        quit_app.assert_called_once()

    def test_transient_u_recovers_without_poisoning_pass(self):
        result, quit_app = self.simulate(exit_at=12, state=lambda t: 'U' if t < 6 else 'S')
        self.assertTrue(result['uninterruptible_observed'])
        self.assertFalse(result['persistent_uninterruptible'])
        self.assertIsNone(result['failure'])
        self.assertEqual(life.classify(result['exit_code'], result['quit_requested'],
                                      result['failure'], False, result['remaining']), 'PASS')
        ended = next(e for e in result['events'] if e['event'] == 'uninterruptible_ended')
        self.assertEqual(ended['observed_span'], 6)

    def test_persistent_u_latches_failure_after_recovery(self):
        result, quit_app = self.simulate(state=lambda t: 'U' if t < 18 else 'S')
        self.assertTrue(result['persistent_uninterruptible'])
        self.assertEqual(result['failure'], 'persistent_uninterruptible_process')
        self.assertEqual(result['quit_elapsed'], 18)
        quit_app.assert_called_once()

    def test_refusal_then_accepted_retry_can_pass(self):
        result, quit_app = self.simulate(exit_at=18, quit_results=['refused', 'accepted'])
        self.assertEqual(quit_app.call_count, 2)
        self.assertEqual(result['quit_errors'], ['refused'])
        self.assertIsNone(result['failure'])
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue(result['quit_requested'])

    def test_refusal_then_exit_preserves_status_without_inventing_acceptance(self):
        result, _ = self.simulate(exit_at=14, code=0, quit_results=['refused'])
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['quit_requested'])
        self.assertEqual(life.classify(0, False, result['failure'], False, []), 'FAIL')

    def test_refusal_while_alive_requires_cleanup(self):
        result, quit_app = self.simulate(quit_results=['refused', 'refused'])
        self.assertEqual(result['elapsed_seconds'], 20)
        self.assertTrue(result['cleanup_required'])
        self.assertIsNone(result['exit_code'])
        self.assertEqual(quit_app.call_count, 2)

    def test_unexpected_monitor_error_does_not_abandon_child(self):
        result, quit_app = self.simulate(exit_at=12, code=7,
                                        guard=Mock(side_effect=RuntimeError('unexpected')))
        self.assertEqual(result['exit_code'], 7)
        self.assertEqual(result['elapsed_seconds'], 20)
        self.assertEqual(result['failure'], 'unexpected')
        quit_app.assert_not_called()

    def test_temporary_monitor_error_recovers_but_invalidates_pass(self):
        guard = Mock(side_effect=[ValueError('mount changed')] + [{}] * 20)
        result, quit_app = self.simulate(exit_at=12, guard=guard)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['failure'], 'mount changed')
        quit_app.assert_called_once()

    def test_slow_inspection_cannot_send_quit_after_deadline(self):
        now = [0]
        process = Mock(pid=123, poll=Mock(return_value=None))
        quit_app = Mock(return_value='accepted')
        def guard(): now[0] += 25
        result = life.supervise(process, self.profile, self.root, 10, 10,
            lambda: [self.row()], guard, quit_app, clock=lambda: now[0], sleep=lambda _: None)
        self.assertEqual(result['elapsed_seconds'], 25)
        quit_app.assert_not_called()
        self.assertTrue(result['cleanup_required'])

    def test_runtime_command_obeys_remaining_deadline(self):
        with patch.object(life, 'COMMAND_DEADLINE', 10), patch.object(life.time, 'monotonic', return_value=8), \
                patch.object(life.subprocess, 'run', return_value=SimpleNamespace(stdout='ok')) as run:
            self.assertEqual(life.command('/bin/ps'), 'ok')
            self.assertEqual(run.call_args.kwargs['timeout'], 2)
        with patch.object(life, 'COMMAND_DEADLINE', 10), patch.object(life.time, 'monotonic', return_value=10), \
                patch.object(life.subprocess, 'run') as run:
            with self.assertRaises(TimeoutError): life.command('/bin/ps')
            run.assert_not_called()

    def test_helpers_observed_until_exit(self):
        now = [0]
        process = Mock(pid=123, poll=lambda: 0 if now[0] >= 12 else None)
        def sample():
            if now[0] < 12: return [self.row()]
            if now[0] < 16: return [self.row(pid=124, command='handler --database=' +
                                           str(self.profile / 'Crashpad-isolated'))]
            return []
        result = life.supervise(process, self.profile, self.root, 10, 10, sample, Mock(),
            Mock(return_value='accepted'), clock=lambda: now[0],
            sleep=lambda n: now.__setitem__(0, now[0]+n))
        self.assertEqual(result['elapsed_seconds'], 16)
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['remaining'])
        self.assertIsNone(result['failure'])

    def test_evidence_guard_failure_preserves_exit_observation(self):
        now = [0]
        process = Mock(pid=123, poll=lambda: 0 if now[0] >= 12 else None)
        result = life.supervise(process, self.profile, self.root, 10, 10,
            lambda: [self.row()] if now[0] < 12 else [], Mock(), Mock(return_value='accepted'),
            clock=lambda: now[0], sleep=lambda n: now.__setitem__(0, now[0]+n),
            evidence_guard=Mock(side_effect=ValueError('mount changed')))
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('evidence_write_failed', result['failure'])
        self.assertFalse((self.root / 'events.jsonl').exists())
        self.assertTrue(result['events'])

    def marker_fixture(self):
        import hashlib
        logs = self.root / 'logs'; logs.mkdir()
        evidence = logs / 'previous'; evidence.mkdir()
        result = dict(pid=123, profile=str(self.profile), clean_shutdown='FAIL')
        for name, value in [('result.json', result), ('launch.json', result),
                            ('cleanup-result.json', {'remaining_processes': []})]:
            (evidence / name).write_text(json.dumps(value))
        (evidence / 'samples.jsonl').touch(); (evidence / 'browser.log').touch()
        latch = logs / 'TrinolLifecycle.blocked.json'
        raw = json.dumps(dict(evidence=str(evidence), result=result)).encode()
        latch.write_bytes(raw)
        self.enterContext(patch.object(life, 'R4_MARKER_SHA256', hashlib.sha256(raw).hexdigest()))
        return latch, evidence, raw

    def test_reviewed_retry_preserves_bytes_and_never_clears_guard(self):
        latch, evidence, raw = self.marker_fixture()
        retry = life.review_r4_marker(self.root, latch, [])
        run = self.root / 'run'; run.mkdir()
        life.arm_latch(latch, run, retry)
        self.assertEqual(Path(retry['archive']).read_bytes(), raw)
        self.assertEqual(json.loads(latch.read_text())['state'], 'in_progress')
        self.assertEqual(json.loads(latch.read_text())['reviewed_retry'], retry)
        with self.assertRaises(ValueError): life.review_r4_marker(self.root, latch, [])

    def test_retry_rejects_live_process_and_missing_evidence(self):
        latch, evidence, raw = self.marker_fixture()
        with self.assertRaises(ValueError): life.review_r4_marker(self.root, latch, [self.row()])
        (evidence / 'launch.json').unlink()
        with self.assertRaises(OSError): life.review_r4_marker(self.root, latch, [])
        self.assertEqual(latch.read_bytes(), raw)

    def test_retry_rejects_other_failure_marker(self):
        latch, _, _ = self.marker_fixture()
        latch.write_text('{}')
        with self.assertRaises(ValueError): life.review_r4_marker(self.root, latch, [])
        self.assertEqual(latch.read_text(), '{}')

    def test_archive_replace_failure_preserves_original_guard(self):
        latch, _, raw = self.marker_fixture()
        retry = life.review_r4_marker(self.root, latch, [])
        run = self.root / 'run'; run.mkdir()
        with patch.object(life.os, 'replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError): life.arm_latch(latch, run, retry)
        self.assertEqual(latch.read_bytes(), raw)
        self.assertEqual(Path(retry['archive']).read_bytes(), raw)
        with self.assertRaises(ValueError): life.review_r4_marker(self.root, latch, [])

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
