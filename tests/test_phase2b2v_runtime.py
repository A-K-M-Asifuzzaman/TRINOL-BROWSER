"""Synthetic offline gate tests: no browser, real screen or external profile."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase2b2v_runtime as v
import test_chromium_lifecycle_macos as life
import capture_chromium_window_macos as c
import test_phase2b1v_runtime as previous_tests


class NewTabGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.enterContext(patch.object(v, 'BUILD_ROOT', self.root))
        self.manifest = dict(chromium=dict(version='155.0.8059.85',
            revision='0e66b94549a8bd85f03fbdf189b752d6e7b63c32'),
            depot_tools=dict(revision='dca727ba1f8fa8f1e3b12a815d065818bb61d395'),
            customization={'id': 'fixture'})
        self.enterContext(patch.object(v, 'CUSTOMIZATION_SHA256', hashlib.sha256(
            json.dumps(self.manifest['customization'], sort_keys=True).encode()).hexdigest()))
        for key in ('HISTORY', 'ARTIFACTS'):
            records = {}
            for name in getattr(v, key):
                path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name); records[name] = v.sha256(path)
            self.enterContext(patch.object(v, key, records))
        self.observer = self.root/v.OBSERVER
        self.observer.parent.mkdir(parents=True, exist_ok=True)
        self.observer.write_bytes(b'fixture observer')
        self.check = self.enterContext(patch.object(v, 'check_observer'))
        self.run = self.root/'logs/new-run'; self.run.mkdir()

    def review(self, rows=()):
        return v.review(self.root, rows, self.manifest, self.observer)

    def test_exact_review_is_read_only_and_checks_observer(self):
        before = {name:(self.root/name).read_bytes() for name in v.HISTORY}
        self.assertEqual(self.review()['phase'], '2b2-v')
        self.assertEqual(before, {name:(self.root/name).read_bytes() for name in v.HISTORY})
        self.check.assert_called_once_with(self.root, self.observer)
        self.assertFalse((self.root/v.CLAIM).exists())

    def test_each_changed_history_or_artifact_denied(self):
        for records in (v.HISTORY, v.ARTIFACTS):
            for name in records:
                with self.subTest(name=name):
                    path = self.root/name; original = path.read_bytes()
                    path.write_bytes(b'changed')
                    with self.assertRaisesRegex(ValueError, 'Reviewed file changed'): self.review()
                    path.write_bytes(original)

    def test_missing_evidence_and_symlink_escape_denied(self):
        path = self.root/next(iter(v.HISTORY)); path.unlink()
        with self.assertRaises(FileNotFoundError): self.review()
        path.symlink_to('/bin/sh')
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.review()

    def test_wrong_source_contract_or_pin_denied(self):
        for section, key in [('chromium', 'revision'), ('chromium', 'version'),
                             ('depot_tools', 'revision'), ('customization', 'id')]:
            original = self.manifest[section][key]; self.manifest[section][key] = 'wrong'
            with self.assertRaisesRegex(ValueError, 'three-patch'): self.review()
            self.manifest[section][key] = original

    def test_any_existing_compiled_process_denied(self):
        for state in ('S', 'U', 'Z'):
            with self.assertRaisesRegex(ValueError, 'overlapping'):
                self.review([dict(pid=123, start='other', state=state)])

    def test_wrong_observer_path_denied(self):
        with self.assertRaisesRegex(ValueError, 'observer path'):
            v.review(self.root, [], self.manifest, self.root/'other-observer')

    def test_another_build_root_is_denied(self):
        with self.assertRaisesRegex(ValueError, 'build root'):
            v.review(self.root/'another', [], self.manifest, self.observer)

    def test_permanent_exclusive_claim_and_guard_preserve_history(self):
        before = {name:(self.root/name).read_bytes() for name in v.HISTORY}
        record = self.review(); v.claim(self.root, self.run, record)
        with self.assertRaises(FileExistsError): v.claim(self.root, self.run, record)
        with self.assertRaisesRegex(ValueError, 'consumed'): self.review()
        guard = self.root/v.GUARD; guard.write_text('in progress')
        v.retain_visual_guard(guard, self.run, dict(clean_shutdown='PASS'))
        self.assertEqual(json.loads(guard.read_text())['visual_validation'], 'PENDING_REVIEW')
        self.assertEqual(before, {name:(self.root/name).read_bytes() for name in v.HISTORY})

    def test_existing_review_guard_blocks_even_without_claim(self):
        (self.root/v.GUARD).write_text('in progress')
        with self.assertRaisesRegex(ValueError, 'pending review'): self.review()

    def test_fixed_deadline_operator_and_no_legacy_flags(self):
        v.check_options(True, 360, 30, 'blank', False)
        for options in [(False,360,30,'blank',False), (True,540,30,'blank',False),
                        (True,360,60,'blank',False), (True,360,30,'browsing',False),
                        (True,360,30,'blank',True)]:
            with self.assertRaises(ValueError): v.check_options(*options)

    def test_only_fresh_private_profile_and_crash_directory_accepted(self):
        profile, crash = life.isolated_profile(self.root, 'test-profile-2b2v-')
        v.check_profile(self.root, profile, crash)
        for path in (profile/'Preferences', crash/'old.dmp'):
            path.write_text('old session')
            with self.assertRaisesRegex(ValueError, 'fresh private'): v.check_profile(self.root, profile, crash)
            path.unlink()
        profile.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'fresh private'): v.check_profile(self.root, profile, crash)
        profile.chmod(0o700)
        with self.assertRaises(ValueError): v.check_profile(self.root, profile, profile/'other-crash')
        crash.rmdir(); crash.symlink_to(self.run, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'): v.check_profile(self.root, profile, crash)


class NewTabCaptureTests(previous_tests.CaptureTests):
    def setUp(self):
        super().setUp()
        record = dict(phase='2b2-v')
        (self.run/'launch.json').write_text(json.dumps(dict(pid=123,
            profile=str(self.profile), visual_authorization=record)))
        (self.root/v.CLAIM).write_text(json.dumps(dict(evidence=str(self.run), authorization=record)))
        lib = self.root/'chromium/src/out/TrinolDev/libchrome_dll.dylib'
        self.enterContext(patch.object(v, 'LIBRARY_SHA256', v.sha256(lib)))

    def test_capture_cannot_attach_to_a_different_claimed_session(self):
        (self.root/v.CLAIM).write_text(json.dumps(dict(evidence='other', authorization={'phase':'2b2-v'})))
        with self.assertRaisesRegex(ValueError, 'claimed'):
            c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_extra_browser_blocks_capture(self):
        self.snapshot.return_value = [self.row, dict(self.row, pid=999)]
        with self.assertRaisesRegex(ValueError, 'extra browser'):
            c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_wrong_profile_identity_blocks_capture(self):
        event = dict(event='process_identity_verified',
                     browser_identity=dict(self.row, command='browser --user-data-dir=/other'))
        (self.run/'events.jsonl').write_text(json.dumps(event)+'\n')
        with self.assertRaisesRegex(ValueError, 'disposable-profile'):
            c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()

    def test_unmapped_library_blocks_capture(self):
        self.output.side_effect = [b'[{"window_id":42}]', b'n/other/library\n']
        with self.assertRaisesRegex(ValueError, 'not mapped'):
            c.capture(self.root, self.run, self.observer, 'dark')
        self.capture.assert_not_called()
