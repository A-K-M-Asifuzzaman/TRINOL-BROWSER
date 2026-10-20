"""Offline resource guard tests; never start compilers or mutate real checkouts."""
import json
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_chromium_macos as b


class ResourceTests(unittest.TestCase):
    def sample(self, **changes):
        result = dict(free_bytes=100*b.GIB, internal_free_bytes=40*b.GIB,
                      pressure=1, swap_bytes=15*b.GIB)
        return dict(result, **changes)

    def test_swap_and_pressure_parsing(self):
        self.assertEqual(b.parse_memory('2\n', 'total = 16384.00M used = 15360.00M free = 1024M'),
                         {'pressure': 2, 'swap_bytes': 15*b.GIB})

    def test_unknown_sensor_output_fails(self):
        for pressure, swap in [('9', 'used = 10M'), ('1', 'unavailable')]:
            with self.assertRaises(ValueError): b.parse_memory(pressure, swap)

    def test_old_swap_alone_does_not_stop(self):
        self.assertIsNone(b.stop_reason(self.sample(), 15*b.GIB, 0, 4))

    def test_external_floor_inclusive(self):
        self.assertEqual(b.stop_reason(self.sample(free_bytes=60*b.GIB), 15*b.GIB, 0, 4), 'storage_floor')

    def test_internal_swap_headroom(self):
        self.assertEqual(b.stop_reason(self.sample(internal_free_bytes=10*b.GIB), 15*b.GIB, 0, 4), 'internal_swap_headroom')

    def test_critical_pressure_stops_immediately(self):
        self.assertEqual(b.stop_reason(self.sample(pressure=4), 15*b.GIB, 0, 2), 'memory_pressure')

    def test_four_gib_swap_growth_stops(self):
        self.assertEqual(b.stop_reason(self.sample(swap_bytes=19*b.GIB), 15*b.GIB, 0, 2), 'memory_pressure')

    def test_sustained_warning_reduces_four_jobs(self):
        self.assertEqual(b.stop_reason(self.sample(pressure=2), 15*b.GIB, 60, 4), 'reduce_to_two_jobs')
        self.assertIsNone(b.stop_reason(self.sample(pressure=2), 15*b.GIB, 59, 4))

    def test_warning_at_two_jobs_requires_sustained_swap_growth(self):
        self.assertIsNone(b.stop_reason(self.sample(pressure=2), 15*b.GIB, 180, 2))
        self.assertIsNone(b.stop_reason(self.sample(pressure=2, swap_bytes=17*b.GIB), 15*b.GIB, 180, 2))
        self.assertEqual(b.stop_reason(self.sample(pressure=2, swap_bytes=17*b.GIB),
                         15*b.GIB, 180, 2, deterioration_seconds=180), 'memory_pressure')

    def test_supported_job_arguments(self):
        for jobs in (1, 2, 4):
            self.assertEqual(b.parse_args(['--build-root', '/external', '--jobs', str(jobs)]).jobs, jobs)
        self.assertEqual(b.parse_args(['--build-root', '/external']).jobs, 4)

    def test_stable_historical_swap_at_one_job(self):
        period = b.WarningPeriod(15*b.GIB)
        for now in (0, 60, 180, 3600):
            sample = self.sample(pressure=2)
            warning, deterioration = period.observe(sample, now)
            self.assertIsNone(b.stop_reason(sample, 15*b.GIB, warning, 1,
                                           deterioration_seconds=deterioration))

    def test_swap_spike_does_not_inherit_old_pressure_timer(self):
        period = b.WarningPeriod(15*b.GIB)
        period.observe(self.sample(pressure=2), 0)
        sample = self.sample(pressure=2, swap_bytes=17*b.GIB)
        warning, deterioration = period.observe(sample, 1000)
        self.assertEqual(deterioration, 0)
        self.assertIsNone(b.stop_reason(sample, 15*b.GIB, warning, 1,
                                       deterioration_seconds=deterioration))
        warning, deterioration = period.observe(sample, 1180)
        self.assertEqual(b.stop_reason(sample, 15*b.GIB, warning, 1,
                         deterioration_seconds=deterioration), 'memory_pressure')

    def test_normal_pressure_recovers_deterioration_period(self):
        period = b.WarningPeriod(15*b.GIB)
        high = self.sample(pressure=2, swap_bytes=17*b.GIB)
        period.observe(high, 0)
        period.observe(self.sample(pressure=1, swap_bytes=17*b.GIB), 170)
        self.assertEqual(period.observe(high, 180)[1], 0)

    def test_swap_hysteresis_then_recovery(self):
        period = b.WarningPeriod(15*b.GIB)
        period.observe(self.sample(pressure=2, swap_bytes=17*b.GIB), 0)
        self.assertEqual(period.observe(self.sample(pressure=2, swap_bytes=16.9*b.GIB), 60)[1], 60)
        self.assertEqual(period.observe(self.sample(pressure=2, swap_bytes=16.4*b.GIB), 90)[1], 0)

    def test_process_cpu_does_not_include_other_groups(self):
        probe = Mock(command=Mock(return_value=b'123 20.0\n456 80.0\n123 5.0\n'))
        self.assertEqual(b.process_cpu(probe, Mock(pid=123)), 25)

    def test_generation_does_not_offer_compiler_job_reduction(self):
        self.assertIsNone(b.stop_reason(self.sample(pressure=2), 15*b.GIB, 90, 4, generating=True))

    def test_mount_disconnection(self):
        with patch.object(b.os.path, 'ismount', return_value=False):
            with self.assertRaises(ValueError): b.assert_mount(Path('/build'), Path('/volume'), 7)

    def test_mount_replacement(self):
        with patch.object(b.os.path, 'ismount', return_value=True), \
             patch.object(b.os, 'stat', return_value=SimpleNamespace(st_dev=8)):
            with self.assertRaises(ValueError): b.assert_mount(Path('/build'), Path('/volume'), 7)

    def test_stop_signals_only_owned_process_group(self):
        process = Mock(pid=123, poll=Mock(return_value=None))
        with patch.object(b.os, 'killpg') as kill:
            b.stop_process(process)
        kill.assert_called_once_with(123, signal.SIGINT)
        process.wait.assert_called_once_with(timeout=45)

    def test_stop_escalates_only_after_wait_timeout(self):
        process = Mock(pid=123, poll=Mock(return_value=None))
        process.wait.side_effect = [b.subprocess.TimeoutExpired('compiler', 45), None]
        with patch.object(b.os, 'killpg') as kill:
            b.stop_process(process)
        self.assertEqual(kill.call_args_list,
                         [unittest.mock.call(123, signal.SIGINT), unittest.mock.call(123, signal.SIGTERM)])

    def test_finished_process_is_not_signalled(self):
        with patch.object(b.os, 'killpg') as kill:
            b.stop_process(Mock(poll=Mock(return_value=0)))
        kill.assert_not_called()

    def test_environment_is_session_local(self):
        with patch.dict(b.os.environ, {'PATH': '/usr/bin', 'SISO_PATH': '/other/siso'}):
            env = b.environment(Path('/external/build(mac)'))
            self.assertNotIn('SISO_PATH', env)
            self.assertEqual(b.os.environ['SISO_PATH'], '/other/siso')
            self.assertEqual(env['TMPDIR'], '/external/build(mac)/logs/tmp')
            self.assertEqual(env['DEPOT_TOOLS_UPDATE'], '0')


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='trinol-build(mac)-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def test_metacharacters_are_path_data(self):
        self.assertEqual(b.contained(self.root, 'cache'), self.root/'cache')

    def test_symlink_escape_rejected(self):
        (self.root/'cache').symlink_to(self.root.parent)
        with self.assertRaises(ValueError): b.contained(self.root, 'cache')

    def test_parent_traversal_rejected(self):
        with self.assertRaises(ValueError): b.contained(self.root, '../outside')

    def test_duplicate_build_rejected_and_stale_file_reusable(self):
        (self.root/'logs').mkdir()
        with b.build_lock(self.root):
            with self.assertRaisesRegex(ValueError, 'Another guarded build'):
                with b.build_lock(self.root): self.fail('Duplicate lock acquired')
        with b.build_lock(self.root): pass
        self.assertTrue((self.root/'logs/TrinolDev.lock').exists())

    def test_lock_release_after_exception(self):
        (self.root/'logs').mkdir()
        with self.assertRaises(RuntimeError):
            with b.build_lock(self.root): raise RuntimeError('test')
        with b.build_lock(self.root): pass

    def test_lock_rejects_symlink(self):
        (self.root/'logs').mkdir()
        (self.root/'logs/TrinolDev.lock').symlink_to(self.root/'other')
        with self.assertRaises(ValueError):
            with b.build_lock(self.root): self.fail('Symlink lock accepted')

    def test_progress_counts_are_attempt_local(self):
        log = self.root/'command.log'
        log.write_text('[9/100] 1s F CXX object.o\nwarning: example\n')
        p = b.read_progress(log)
        self.assertEqual((p['completed_steps'], p['remaining_steps']), (9, 91))
        self.assertEqual(p['last_warning_in_tail'], 'warning: example')
        log.write_text('Build Failure: 10 done, 0 failed, 90 remaining\n interrupt by signal\n')
        p = b.read_progress(log)
        self.assertEqual((p['completed_steps'], p['failed_steps'], p['remaining_steps']), (10, 0, 90))

    def test_siso_success_summary_supersedes_incomplete_live_counters(self):
        log = self.root/'command.log'
        log.write_text('[39486/39490] 23h51m17.50s F COPY_BUNDLE_DATA framework\n'
                       '23h51m20.23s Build Succeeded: 39487 steps - 0.46/s\n'
                       '    39487 build steps completed, average of 0.46/s\n')
        p = b.read_progress(log)
        self.assertEqual((p['completed_steps'], p['failed_steps'], p['remaining_steps']),
                         (39487, 0, 0))
        self.assertNotIn('scheduled_steps', p)

    def monitor(self, memories, child, times=(0, 5), mount_failure=None):
        volume = SimpleNamespace(mount=str(self.root))
        stat = SimpleNamespace(f_bavail=100, f_frsize=b.GIB)
        with patch.object(b, 'memory', side_effect=memories), \
             patch.object(b, 'assert_mount', side_effect=mount_failure), \
             patch.object(b.os, 'statvfs', return_value=stat), \
             patch.object(b, 'process_cpu', return_value=10), \
             patch.object(b.subprocess, 'Popen', return_value=child), \
             patch.object(b, 'stop_process') as stop, \
             patch.object(b.time, 'sleep'), \
             patch.object(b.time, 'monotonic', side_effect=times):
            result = b.guarded(['compiler'], self.root, self.root, volume, Mock(), 1, False, 42)
        return result, stop

    def test_monitor_failure_stops_child_and_is_not_compiler_failure(self):
        normal = {'pressure':1, 'swap_bytes':0}
        child = Mock(pid=123, returncode=-2, poll=Mock(return_value=None))
        result, stop = self.monitor([normal, normal, OSError('sensor unavailable')], child)
        stop.assert_called_once_with(child)
        self.assertEqual(result['outcome'], 'monitor_failure')

    def test_controlled_stop_records_real_child_status(self):
        normal = {'pressure':1, 'swap_bytes':0}
        child = Mock(pid=123, returncode=-2, poll=Mock(return_value=None))
        result, stop = self.monitor([normal, normal, {'pressure':4, 'swap_bytes':0}], child)
        stop.assert_called_once_with(child)
        self.assertEqual((result['outcome'], result['exit_code']), ('controlled_stop', -2))
        self.assertEqual(result['latest']['interval_seconds'], 5)

    def test_successful_browser_command_reports_completion(self):
        normal = {'pressure':1, 'swap_bytes':0}
        child = Mock(pid=123, returncode=0, poll=Mock(return_value=0))
        result, _ = self.monitor([normal, normal], child)
        self.assertEqual((result['state'], result['outcome'], result['exit_code']),
                         ('finished', 'completed', 0))

    def test_delayed_monitor_fails_closed(self):
        normal = {'pressure':1, 'swap_bytes':0}
        child = Mock(pid=123, returncode=-2, poll=Mock(return_value=None))
        result, stop = self.monitor([normal]*3, child, times=(0, 61))
        stop.assert_called_once_with(child)
        self.assertEqual(result['outcome'], 'monitor_failure')
        self.assertIn('61.0s', result['reason'])
        self.assertEqual(result['latest']['interval_seconds'], 61)

    def test_disconnection_stops_child_without_reopening_mount(self):
        normal = {'pressure':1, 'swap_bytes':0}
        child = Mock(pid=123, returncode=-2, poll=Mock(return_value=None))
        result, stop = self.monitor([normal]*2, child,
            mount_failure=[None, ValueError('Disconnected'), ValueError('Disconnected')])
        stop.assert_called_once_with(child)
        self.assertEqual(result['outcome'], 'monitor_failure')
        self.assertIn('evidence_error', result)

    def test_incremental_build_preserves_output_and_does_not_generate_gn(self):
        output = self.root/'chromium/src/out/TrinolDev'; output.mkdir(parents=True)
        files = {'args.gn': b'original args', 'build.ninja': b'existing graph', 'partial.o': b'object data'}
        for name, data in files.items(): (output/name).write_bytes(data)
        paths = {name:self.root/name for name in ('chromium/src/out/TrinolDev', 'logs', 'depot_tools', 'siso-cache')}
        paths['logs'].mkdir()
        args = b.parse_args(['--build-root', str(self.root), '--jobs', '1'])
        with patch.object(b, 'inspect_args'), \
             patch.object(b, 'guarded', return_value={'state':'finished', 'exit_code':0}) as guard:
            self.assertEqual(b.run_build(args, self.root, paths, SimpleNamespace(), Mock(), 42), 0)
        command = guard.call_args.args[0]
        self.assertEqual(command[-1], 'chrome')
        self.assertEqual(command[command.index('-j')+1], '1')
        self.assertEqual(Path(command[0]).name, 'autoninja')
        for name, data in files.items(): self.assertEqual((output/name).read_bytes(), data)

    def test_guard_does_not_launch_under_critical_pressure(self):
        volume = SimpleNamespace(mount=str(self.root))
        stat = SimpleNamespace(f_bavail=100, f_frsize=b.GIB)
        with patch.object(b, 'memory', return_value={'pressure':4, 'swap_bytes':0}), \
             patch.object(b, 'assert_mount'), patch.object(b.os, 'statvfs', return_value=stat), \
             patch.object(b.subprocess, 'Popen') as launch:
            result = b.guarded(['compiler'], self.root, self.root, volume, Mock(), 4, False)
        launch.assert_not_called()
        self.assertEqual(result['reason'], 'memory_pressure')
        self.assertEqual(json.loads((self.root/'status.json').read_text())['state'], 'stopped')

    def test_failed_child_is_never_reported_successful(self):
        volume = SimpleNamespace(mount=str(self.root))
        stat = SimpleNamespace(f_bavail=100, f_frsize=b.GIB)
        child = Mock(pid=123, returncode=7, poll=Mock(return_value=7))
        with patch.object(b, 'memory', return_value={'pressure':1, 'swap_bytes':0}), \
             patch.object(b, 'assert_mount'), patch.object(b.os, 'statvfs', return_value=stat), \
             patch.object(b.subprocess, 'Popen', return_value=child) as launch, \
             patch.object(b.time, 'sleep'):
            result = b.guarded(['compiler'], self.root, self.root, volume, Mock(), 4, False)
        self.assertEqual(result['exit_code'], 7)
        self.assertTrue(launch.call_args.kwargs['start_new_session'])

    def gn_data(self, **changes):
        values = dict(b.EXPECTED, use_siso='true', use_lld='true')
        values.update(changes)
        return json.dumps([{'name': k, 'default': {'value': v}} for k, v in values.items()])

    def test_gn_inspection_rejects_remote_execution(self):
        result = SimpleNamespace(stdout=self.gn_data(use_remoteexec='true'))
        with patch.object(b.subprocess, 'run', return_value=result) as run:
            with self.assertRaisesRegex(ValueError, 'use_remoteexec'):
                b.inspect_args(self.root, self.root)
        self.assertEqual(run.call_count, 1)

    def test_gn_inspection_rejects_unexpected_executor(self):
        result = SimpleNamespace(stdout=self.gn_data(use_siso='false'))
        with patch.object(b.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'Siso'):
                b.inspect_args(self.root, self.root)

    def test_gn_inspection_records_values_and_browser_target(self):
        results = [SimpleNamespace(stdout=self.gn_data()), SimpleNamespace(stdout='{"//chrome:chrome": {}}')]
        with patch.object(b.subprocess, 'run', side_effect=results):
            b.inspect_args(self.root, self.root)
        values = json.loads((self.root/'effective-args.json').read_text())
        self.assertEqual(values['target_cpu'], '"arm64"')
        self.assertTrue((self.root/'chrome-target.json').is_file())


if __name__ == '__main__':
    unittest.main()
