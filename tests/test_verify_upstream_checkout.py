"""Offline fixture tests; no upstream downloads or real repository mutations."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_upstream_checkout.py'
spec = importlib.util.spec_from_file_location('checkout_verifier', SCRIPT)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def manifest(phase='1b'):
    return {'schema_version': 1, 'phase': phase,
            'chromium': {'url': v.URLS['chromium'], 'revision': 'a'*40 if phase=='1b' else None,
                         'version': '155.0.1.2', 'tag': 'refs/tags/155.0.1.2', 'channel': 'Stable'},
            'depot_tools': {'url': v.URLS['depot_tools'], 'revision': 'b'*40 if phase=='1b' else None},
            'patch_series': 'patches/series', 'overlays': [],
            'verification': {'source_head': True, 'depot_tools_head': True,
                             'dependencies_synced': True, 'hooks_completed': True,
                             'deps_sha256': hashlib.sha256(b'fixture DEPS').hexdigest()}}


class ManifestTests(unittest.TestCase):
    def test_precheckout_null_pins_remain_valid(self):
        for phase in (0,'1a'):
            v.validate_manifest(manifest(phase))

    def test_complete_baseline(self):
        v.validate_manifest(manifest())

    def test_nonobject_manifest_rejected(self):
        with self.assertRaises(ValueError): v.validate_manifest([])

    def test_unverified_completion_rejected(self):
        for field in ('source_head','depot_tools_head','dependencies_synced','hooks_completed'):
            data=manifest(); data['verification'][field]=False
            with self.subTest(field=field), self.assertRaises(ValueError):
                v.validate_manifest(data)

    def test_bad_sha_rejected(self):
        for value in (None,'main','a'*7,'g'*40,'A'*40):
            data=manifest(); data['chromium']['revision']=value
            with self.subTest(value=value), self.assertRaises(ValueError):
                v.validate_manifest(data)

    def test_pin_in_precheckout_phase_rejected(self):
        data=manifest('1a'); data['depot_tools']['revision']='b'*40
        with self.assertRaises(ValueError): v.validate_manifest(data)

    def test_origin_change_rejected(self):
        data=manifest(); data['chromium']['url']='https://example.com/source.git'
        with self.assertRaises(ValueError): v.validate_manifest(data)

    def test_wrong_release_tag_rejected(self):
        data=manifest(); data['chromium']['tag']='refs/heads/main'
        with self.assertRaises(ValueError): v.validate_manifest(data)

    def test_nonstable_baseline_rejected(self):
        data=manifest(); data['chromium']['channel']='Canary'
        with self.assertRaises(ValueError): v.validate_manifest(data)

    def test_customization_rejected(self):
        data=manifest(); data['overlays']=[{'source':'example'}]
        with self.assertRaises(ValueError): v.validate_manifest(data)

    def test_bad_phase_or_schema(self):
        for key,value in (('phase','2'),('schema_version',2)):
            data=manifest(); data[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): v.validate_manifest(data)

    def test_missing_deps_digest(self):
        data=manifest(); data['verification'].pop('deps_sha256')
        with self.assertRaises(ValueError): v.validate_manifest(data)

    def phase1c(self):
        data=manifest(); data['phase']='1c'
        data['verification'].update(gn_generated=True, chromium_compiled=True)
        data['build']={'status':'complete','browser_launched':True,'smoke_tests_completed':True}
        return data

    def test_verified_phase1c(self):
        v.validate_manifest(self.phase1c())

    def test_compilation_alone_cannot_complete_phase1c(self):
        for key in ('browser_launched','smoke_tests_completed'):
            data=self.phase1c(); data['build'][key]=False
            with self.subTest(key=key), self.assertRaises(ValueError): v.validate_manifest(data)

    def test_unbuilt_or_partial_phase1c_is_rejected(self):
        for key in ('gn_generated','chromium_compiled'):
            data=self.phase1c(); data['verification'][key]=False
            with self.subTest(key=key), self.assertRaises(ValueError): v.validate_manifest(data)
        data=self.phase1c(); data['build']['status']='in_progress'
        with self.assertRaises(ValueError): v.validate_manifest(data)


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='trinol-upstream-')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve()
        self.checkout=self.root/'chromium'; self.source=self.checkout/'src'
        self.depot=self.root/'depot_tools'
        self.source.mkdir(parents=True); self.depot.mkdir()
        for name in ('.gclient','.gclient_entries'): (self.checkout/name).touch()
        for name in ('chrome','content','components','third_party','build'): (self.source/name).mkdir()
        (self.source/'chrome/VERSION').write_text('MAJOR=155\nMINOR=0\nBUILD=1\nPATCH=2\n')
        (self.source/'DEPS').write_bytes(b'fixture DEPS')
        self.product=self.root/'product'; (self.product/'patches').mkdir(parents=True)
        (self.product/'patches/series').write_text('# empty baseline\n')
        self.data=manifest()
        self.overrides={}
        fake=patch.object(v,'git',side_effect=self.git);fake.start();self.addCleanup(fake.stop)

    def git(self,path,*args):
        path=Path(path)
        if (path,args) in self.overrides:return self.overrides[(path,args)]
        name='chromium' if path==self.source else 'depot_tools'
        if args==('rev-parse','--show-toplevel'):return str(path)
        if args==('remote','get-url','origin'):return v.URLS[name]
        if args[0]=='rev-parse':return self.data[name]['revision']
        if args[0]=='status':return ''
        raise AssertionError(args)

    def verify(self):return v.verify(self.data,self.checkout,self.depot,product_root=self.product)

    def test_valid_fixture(self):self.assertEqual(len(self.verify()),5)

    def test_wrong_head(self):
        self.overrides[(self.source,('rev-parse','HEAD'))]='c'*40
        with self.assertRaisesRegex(ValueError,'HEAD mismatch'):self.verify()

    def test_tracked_changes(self):
        self.overrides[(self.source,('status','--porcelain','--untracked-files=all'))]=' M DEPS'
        with self.assertRaisesRegex(ValueError,'tracked modifications'):self.verify()

    def test_untracked_source_and_modified_tool_source_rejected(self):
        self.overrides[(self.source,('status','--porcelain','--untracked-files=all'))]='?? unexpected.cc'
        with self.assertRaises(ValueError):self.verify()
        self.overrides.clear()
        self.overrides[(self.depot,('status','--porcelain','--untracked-files=no'))]=' M autoninja.py'
        with self.assertRaises(ValueError):self.verify()

    def test_customized_build_verification_requires_exact_applied_state(self):
        self.data['customization']={'schema_version':1,'id':'fixture',
            'upstream_revision':self.data['chromium']['revision'],'patches':[],'files':[]}
        with patch('apply_product_patches.verify_source_state',side_effect=ValueError('unauthorized contents')) as check:
            with self.assertRaisesRegex(ValueError,'unauthorized'):self.verify()
            check.assert_called_once()
        with patch('apply_product_patches.verify_source_state',return_value='applied'):
            self.assertIn('Source state: applied',self.verify()[3])

    def test_actual_origin_mismatch(self):
        self.overrides[(self.depot,('remote','get-url','origin'))]='https://example.com'
        with self.assertRaisesRegex(ValueError,'origin mismatch'):self.verify()

    def test_missing_gclient_metadata(self):
        (self.checkout/'.gclient_entries').unlink()
        with self.assertRaisesRegex(ValueError,'metadata'):self.verify()

    def test_deps_modified(self):
        (self.source/'DEPS').write_text('changed')
        with self.assertRaisesRegex(ValueError,'digest mismatch'):self.verify()

    def test_wrong_version(self):
        (self.source/'chrome/VERSION').write_text('MAJOR=154\nMINOR=0\nBUILD=1\nPATCH=2\n')
        with self.assertRaisesRegex(ValueError,'VERSION mismatch'):self.verify()

    def test_wrong_tag(self):
        self.overrides[(self.source,('rev-parse','refs/tags/155.0.1.2^{commit}'))]='c'*40
        with self.assertRaisesRegex(ValueError,'Local release tag'):self.verify()

    def test_missing_source_directory(self):
        (self.source/'content').rmdir()
        with self.assertRaisesRegex(ValueError,'source directory'):self.verify()

    def test_product_overlap(self):
        with patch.object(v,'ROOT',self.checkout):
            with self.assertRaisesRegex(ValueError,'separate'):self.verify()

    def test_source_tools_overlap(self):
        with self.assertRaisesRegex(ValueError,'separate'):
            v.verify(self.data,self.checkout,self.source)

    def test_requires_verified_manifest(self):
        self.data=manifest('1a')
        with self.assertRaisesRegex(ValueError,'no verified'):self.verify()

    def test_shell_metacharacters_are_path_data(self):
        target=self.root/'checkout(mac)'
        self.checkout.rename(target);self.checkout=target;self.source=target/'src'
        self.assertEqual(len(self.verify()),5)

    def test_spaces_in_resolved_checkout_rejected(self):
        target=self.root/'checkout space'
        self.checkout.rename(target);self.checkout=target
        with self.assertRaisesRegex(ValueError,'whitespace'):self.verify()


if __name__=='__main__':unittest.main()
