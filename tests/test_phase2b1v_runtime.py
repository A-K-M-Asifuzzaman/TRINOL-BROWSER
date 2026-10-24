"""Synthetic evidence only: never starts a browser or captures the real screen."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase2b1v_runtime as v
import capture_chromium_window_macos as c


class VisualGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.prior = self.root / v.PRIOR
        self.prior.mkdir(parents=True)
        self.result = dict(pid=20381, exit_code=0, failure=None, clean_shutdown='PASS',
            quit_requested=True, remaining=[], unexpected_remaining=[], watchdog=False,
            dumps=[], cleanup_required=False, max_poll_gap=.4, max_observation_gap=2.3,
            profile=str(self.root / 'test-profile-2b1-l0_1332k'), elapsed_seconds=243,
            evidence_writer=dict(error=None, flushed=True, dropped=0, unacknowledged=0,
                                 submitted=266, acknowledged=266, writer_remaining=False))
        self.exe = self.root / c.life.EXE
        launch = dict(pid=20381, profile=self.result['profile'], command=[str(self.exe)], start_time_unix=1)
        for name, value in [('result.json', self.result), ('launch.json', launch),
                            ('final-health.json', dict(remaining=[], volume_uuid=v.EXPECTED_VOLUME_UUID))]:
            (self.prior / name).write_text(json.dumps(value))
        hashes = {p.name:v.sha256(p) for p in self.prior.iterdir()}
        self.enterContext(patch.object(v, 'PRIOR_FILES', hashes))
        archives = {}
        for name in v.ARCHIVES:
            p = self.root / ('logs/TrinolLifecycle.' + name + '-reviewed.json')
            p.write_text('original ' + name); archives[name] = v.sha256(p)
        self.enterContext(patch.object(v, 'ARCHIVES', archives))
        self.manifest = dict(chromium=dict(revision='0e66b94549a8bd85f03fbdf189b752d6e7b63c32'),
            depot_tools=dict(revision='dca727ba1f8fa8f1e3b12a815d065818bb61d395'), customization={'id':'fixture'})
        self.enterContext(patch.object(v, 'CUSTOMIZATION_SHA256', hashlib.sha256(
            json.dumps(self.manifest['customization'], sort_keys=True, separators=(',',':')).encode()).hexdigest()))
        self.library = self.root / 'chromium/src/out/TrinolDev/libchrome_dll.dylib'
        self.library.parent.mkdir(parents=True); self.library.write_bytes(b'corrected native library')
        self.enterContext(patch.object(v, 'LIBRARY_SHA256', v.sha256(self.library)))
        self.exe.parent.mkdir(parents=True); self.exe.write_bytes(b'launcher')
        self.enterContext(patch.object(v, 'LAUNCHER_SHA256', v.sha256(self.exe)))
        args = self.library.parent/'args.gn'; args.write_bytes(b'preserved arguments')
        self.enterContext(patch.object(v, 'GN_ARGS_SHA256', v.sha256(args)))
        self.observer = self.root / 'observer'; self.observer.write_bytes(b'read-only utility'); self.observer.chmod(0o700)
        self.enterContext(patch.object(v, 'OBSERVER_SHA256', v.sha256(self.observer)))
        self.run = self.enterContext(patch.object(v.subprocess, 'run', return_value=
                    subprocess.CompletedProcess([], 2, b'', b'')))

    def review(self):
        return v.review(self.root, [], self.manifest, self.observer)

    def test_exact_successful_evidence_and_new_library_pass_without_mutation(self):
        before = {p.name:p.read_bytes() for p in (self.root/'logs').glob('*reviewed.json')}
        record = self.review()
        self.assertEqual(record['phase'], '2b1-v')
        self.assertEqual(before, {p.name:p.read_bytes() for p in (self.root/'logs').glob('*reviewed.json')})
        self.assertFalse((self.root/v.CLAIM).exists())
        self.run.assert_called_once_with([str(self.observer), '1'], capture_output=True, timeout=5)

    def test_modified_evidence_refused(self):
        (self.prior/'result.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'evidence changed'): self.review()

    def test_failed_writer_rejected_even_with_matching_fixture_hash(self):
        self.result['evidence_writer']['flushed'] = False
        p = self.prior/'result.json'; p.write_text(json.dumps(self.result)); v.PRIOR_FILES[p.name] = v.sha256(p)
        with self.assertRaisesRegex(ValueError, 'clean lifecycle'): self.review()

    def test_original_archive_change_refused(self):
        (self.root/'logs/TrinolLifecycle.r6-ui-reviewed.json').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'archive changed'): self.review()

    def test_unexpected_library_or_old_chronology_refused(self):
        original = self.library.read_bytes(); self.library.write_bytes(b'old library')
        with self.assertRaisesRegex(ValueError, 'library'): self.review()
        self.library.write_bytes(original); os.utime(self.library, (1, 1))
        with self.assertRaisesRegex(ValueError, 'chronology'): self.review()

    def test_arbitrary_revision_or_customization_refused(self):
        self.manifest['chromium']['revision'] = '0'*40
        with self.assertRaisesRegex(ValueError, 'revision'): self.review()
        self.manifest['chromium']['revision'] = '0e66b94549a8bd85f03fbdf189b752d6e7b63c32'
        self.manifest['customization']['id'] = 'another'
        with self.assertRaisesRegex(ValueError, 'two-patch'): self.review()

    def test_changed_launcher_or_gn_arguments_refused(self):
        original = self.exe.read_bytes(); self.exe.write_bytes(b'other launcher')
        with self.assertRaisesRegex(ValueError, 'launcher'): self.review()
        self.exe.write_bytes(original); (self.library.parent/'args.gn').write_text('changed arguments')
        with self.assertRaisesRegex(ValueError, 'GN arguments'): self.review()

    def test_live_processes_and_active_failure_refused(self):
        with self.assertRaises(ValueError): v.review(self.root, [dict(pid=12)], self.manifest, self.observer)
        (self.root/'logs/TrinolLifecycle.blocked.json').write_text('new failure')
        with self.assertRaisesRegex(ValueError, 'Active lifecycle'): self.review()

    def test_claim_is_permanent_and_second_claim_refused(self):
        authorization = self.review(); run = self.root/'run'; run.mkdir()
        v.claim(self.root, run, authorization)
        with self.assertRaisesRegex(ValueError, 'consumed'): self.review()
        with self.assertRaises(FileExistsError): v.claim(self.root, run, authorization)
        self.assertEqual(json.loads((self.root/v.CLAIM).read_text())['authorization'], authorization)

    def test_modified_observer_and_symlink_escape_refused(self):
        self.observer.write_text('other tool')
        with self.assertRaisesRegex(ValueError, 'nonlaunching'): self.review()
        self.observer.unlink(); self.observer.symlink_to('/bin/sh')
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.review()

    def test_observer_self_check_failure_refused(self):
        self.run.return_value.returncode = 0
        with self.assertRaisesRegex(ValueError, 'self-check'): self.review()

    def test_visual_pending_or_failure_never_clears_lifecycle_guard(self):
        run = self.root/'run'; run.mkdir(); latch = self.root/'logs/TrinolLifecycle.blocked.json'
        latch.write_text('in progress')
        v.retain_visual_guard(latch, run, dict(clean_shutdown='PASS', visual_validation='FAIL'))
        self.assertTrue(latch.exists())
        self.assertEqual(json.loads(latch.read_text())['result']['visual_validation'], 'FAIL')
        self.assertEqual(json.loads(latch.read_text())['visual_validation'], 'FAIL')

    def test_atomic_guard_replace_failure_preserves_in_progress_guard(self):
        run = self.root/'run'; run.mkdir(); latch = self.root/'logs/TrinolLifecycle.blocked.json'
        latch.write_text('in progress')
        with patch.object(v.os, 'replace', side_effect=OSError('write failed')):
            with self.assertRaises(OSError): v.retain_visual_guard(latch, run, {})
        self.assertEqual(latch.read_text(), 'in progress')


class CaptureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.run = self.root/'logs/run'; self.run.mkdir(parents=True)
        self.observer = self.root/'observer'; self.profile = self.root/'test-profile'; self.profile.mkdir()
        self.row = dict(pid=123, start='known start', executable=str(self.root/c.life.EXE),
                        command='browser --user-data-dir='+str(self.profile))
        authorization = {'phase':'2b1-v'}
        (self.run/'launch.json').write_text(json.dumps(dict(pid=123, profile=str(self.profile), visual_authorization=authorization)))
        (self.root/v.CLAIM).write_text(json.dumps(dict(evidence=str(self.run), authorization=authorization)))
        (self.run/'events.jsonl').write_text(json.dumps(dict(event='process_identity_verified', browser_identity=self.row))+'\n')
        lib = self.root/'chromium/src/out/TrinolDev/libchrome_dll.dylib'; lib.parent.mkdir(parents=True); lib.write_bytes(b'lib')
        self.enterContext(patch.object(v, 'LIBRARY_SHA256', v.sha256(lib)))
        self.enterContext(patch.object(v, 'check_observer', return_value=self.observer))
        self.snapshot = self.enterContext(patch.object(c.life, 'snapshot', return_value=[self.row]))
        self.output = self.enterContext(patch.object(c.subprocess, 'check_output', side_effect=[
            json.dumps([dict(window_id=42, bounds={})]).encode(), ('n'+str(lib)+'\n').encode()]))
        self.capture = self.enterContext(patch.object(c.subprocess, 'run'))
        self.capture.side_effect = lambda argv, **kw: Path(argv[-1]).write_bytes(
            b'\x89PNG\r\n\x1a\n' + b'\0'*8 + struct.pack('>II', 100, 80))

    def test_capture_targets_only_verified_pid_and_window_and_records_identity(self):
        target = c.capture(self.root, self.run, self.observer, 'dark')
        self.assertEqual(self.output.call_args_list[0].args[0], [str(self.observer), '123'])
        self.capture.assert_called_once_with(['/usr/sbin/screencapture','-x','-l','42',str(target)], check=True, timeout=5)
        self.assertEqual(self.snapshot.call_count, 3)
        self.assertEqual(json.loads((self.run/'dark.json').read_text())['browser_identity'],
                         [123, 'known start', self.row['executable']])

    def test_pid_reuse_prevents_capture(self):
        self.snapshot.return_value = [dict(self.row, start='new start')]
        with self.assertRaisesRegex(ValueError, 'identity'): c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called(); self.output.assert_not_called()

    def test_exit_during_capture_preflight_never_launches_an_app(self):
        self.snapshot.side_effect = [[self.row], []]
        with self.assertRaisesRegex(ValueError, 'identity'): c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_missing_window_fails_without_app_lookup(self):
        self.output.side_effect = [b'[]']
        with self.assertRaisesRegex(ValueError, 'verified owned window'): c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_ambiguous_windows_require_exact_owned_selection(self):
        self.output.side_effect = [b'[{"window_id":42},{"window_id":43}]']
        with self.assertRaisesRegex(ValueError, 'Choose one'): c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_unsafe_name_or_finished_session_refused(self):
        with self.assertRaises(ValueError): c.capture(self.root, self.run, self.observer, '../escape')
        (self.run/'result.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'finished'): c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_success_exit_without_png_is_not_capture_evidence(self):
        self.capture.side_effect = None
        with self.assertRaisesRegex(ValueError, 'PNG'): c.capture(self.root, self.run, self.observer, 'dark')
        self.assertFalse((self.run/'dark.json').exists())

    def test_capture_cannot_attach_to_a_different_claimed_session(self):
        (self.root/v.CLAIM).write_text(json.dumps(dict(evidence='another session', authorization={'phase':'2b1-v'})))
        with self.assertRaisesRegex(ValueError, 'claimed'): c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called(); self.output.assert_not_called()


if __name__ == '__main__':
    unittest.main()
