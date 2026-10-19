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
        self.assertEqual(b.stop_reason(self.sample(pressure=2, swap_bytes=17*b.GIB), 15*b.GIB, 180, 2), 'memory_pressure')

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
