"""Synthetic Git repositories only; never touches a Chromium checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_product_patches import apply_contract, ContractError, git, verify_source_state, expected_outputs


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.product = self.root/'product'; self.product.mkdir()
        self.checkout = self.root/'checkout'; self.checkout.mkdir()
        git(self.checkout, 'init', '-q')
        git(self.checkout, 'config', 'user.name', 'Synthetic Test')
        git(self.checkout, 'config', 'user.email', 'test@example.invalid')
        (self.checkout/'file.txt').write_text('one\n')
        git(self.checkout, 'add', '.')
        git(self.checkout, 'commit', '-qm', 'test fixture')
        (self.product/'upstream').mkdir(); (self.product/'patches').mkdir()
        self.manifest = {'chromium':{'revision':git(self.checkout,'rev-parse','HEAD')},
                         'patch_series':'patches/series','overlays':[]}
        self.save()
        (self.product/'patches/series').write_text('first.patch\nsecond.patch\n')
        for name, before, after in [('first','one','two'),('second','two','three')]:
            (self.product/f'patches/{name}.patch').write_text(
                f'diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-{before}\n+{after}\n')
        self.declare()

    def declare(self):
        self.manifest['customization']={'schema_version':1,'id':'synthetic-test',
            'upstream_revision':self.manifest['chromium']['revision'],
            'patches':[{'path':name,'sha256':hashlib.sha256((self.product/'patches'/name).read_bytes()).hexdigest()}
                       for name in ('first.patch','second.patch')],
            'files':[{'path':'file.txt','mode':'100644','sha256':hashlib.sha256(b'three\n').hexdigest()}]+
              [{'path':e['destination'],'mode':'100644','sha256':e['sha256']} for e in self.manifest['overlays']]}
        self.save()

    def save(self):
        (self.product/'upstream/manifest.json').write_text(json.dumps(self.manifest))

    def test_dependent_check_is_read_only_and_apply_is_ordered(self):
        index = (self.checkout/'.git/index').read_bytes()
        objects = set((self.checkout/'.git/objects').rglob('*'))
        self.assertEqual(apply_contract(self.product,self.checkout)['applied'], [])
        self.assertEqual((self.checkout/'file.txt').read_text(),'one\n')
        self.assertEqual((self.checkout/'.git/index').read_bytes(),index)
        self.assertEqual(set((self.checkout/'.git/objects').rglob('*')),objects)
        result=apply_contract(self.product,self.checkout,True)
        self.assertEqual(result['applied'],['patches/first.patch','patches/second.patch'])
        self.assertEqual((self.checkout/'file.txt').read_text(),'three\n')
        with self.assertRaises(ContractError): apply_contract(self.product,self.checkout,True)

    def test_wrong_pin_and_dirty_or_untracked_checkout_rejected(self):
        self.manifest['chromium']['revision']='0'*40;self.save()
        with self.assertRaises(ContractError): apply_contract(self.product,self.checkout)
        self.manifest['chromium']['revision']=git(self.checkout,'rev-parse','HEAD');self.save()
        (self.checkout/'private.txt').write_text('preserve')
        with self.assertRaises(ContractError): apply_contract(self.product,self.checkout)
        self.assertEqual((self.checkout/'private.txt').read_text(),'preserve')

    def test_paths_duplicates_and_symlinks_rejected(self):
        series=self.product/'patches/series'
        for text in ['../secret.patch','/tmp/a','first.patch\nfirst.patch','a/../../x']:
            series.write_text(text+'\n')
            with self.assertRaises(ContractError): apply_contract(self.product,self.checkout)
        series.write_text('link.patch\n');(self.product/'patches/link.patch').symlink_to(self.product/'patches/first.patch')
        with self.assertRaises(ContractError): apply_contract(self.product,self.checkout)

    def overlay(self):
        source=self.product/'logo.svg';source.write_text('<svg/>')
        self.manifest['overlays']=[{'source':'logo.svg','destination':'trinol/assets/logo.svg',
                                  'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}];self.declare()
        return source

    def test_overlay_new_file_and_digest_validation(self):
        source=self.overlay()
        apply_contract(self.product,self.checkout)
        self.assertFalse((self.checkout/'trinol').exists())
        apply_contract(self.product,self.checkout,True)
        self.assertEqual((self.checkout/'trinol/assets/logo.svg').read_bytes(),source.read_bytes())

    def test_overlay_overwrite_collision_digest_and_escape_refused(self):
        self.overlay()
        for destination in ['../logo.svg','.git/hooks/a','file.txt','/tmp/logo.svg']:
            self.manifest['overlays'][0]['destination']=destination;self.save()
            with self.assertRaises(ContractError):apply_contract(self.product,self.checkout)
        self.manifest['overlays'][0]['destination']='trinol/logo.svg';self.manifest['overlays'][0]['sha256']='0'*64;self.save()
        with self.assertRaises(ContractError):apply_contract(self.product,self.checkout)

    def test_invalid_second_patch_does_not_mutate_checkout(self):
        (self.product/'patches/second.patch').write_text('broken')
        with self.assertRaises((ContractError, subprocess.SubprocessError)):apply_contract(self.product,self.checkout,True)
        self.assertEqual((self.checkout/'file.txt').read_text(),'one\n')

    def test_symlink_and_generated_target_patch_refused(self):
        patchfile=self.product/'patches/first.patch'
        patchfile.write_text('diff --git a/link b/link\nnew file mode 120000\n--- /dev/null\n+++ b/link\n@@ -0,0 +1 @@\n+/private\n')
        with self.assertRaises(ContractError):apply_contract(self.product,self.checkout)
        patchfile.write_text('diff --git a/out/a b/out/a\nnew file mode 100644\n--- /dev/null\n+++ b/out/a\n@@ -0,0 +1 @@\n+x\n')
        with self.assertRaises(ContractError):apply_contract(self.product,self.checkout)

    def test_pristine_and_applied_are_distinct(self):
        self.assertEqual(verify_source_state(self.product,self.checkout,self.manifest,'pristine'),'pristine')
        with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest)
        apply_contract(self.product,self.checkout,True)
        self.assertEqual(verify_source_state(self.product,self.checkout,self.manifest),'applied')
        with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest,'pristine')

    def test_applied_state_rejects_extra_tampered_missing_and_mode_changes(self):
        apply_contract(self.product,self.checkout,True)
        target=self.checkout/'file.txt'
        for data in ('unreviewed\n','one\n'):
            target.write_text(data)
            with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest)
        target.write_text('three\n');target.chmod(0o755)
        with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest)
        target.chmod(0o644)
        other=self.checkout/'unexpected.cc';other.write_text('unknown')
        with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest)
        self.assertEqual(other.read_text(),'unknown')

    def test_output_inventory_and_patch_digest_cannot_authorize_arbitrary_content(self):
        self.manifest['customization']['files'][0]['sha256']='0'*64;self.save()
        with self.assertRaises(ContractError):expected_outputs(self.product,self.checkout,self.manifest)
        self.declare();self.manifest['customization']['patches'][0]['sha256']='0'*64;self.save()
        with self.assertRaises(ContractError):expected_outputs(self.product,self.checkout,self.manifest)
        self.declare();self.manifest['customization']['files'].append({'path':'unrelated','mode':'100644','sha256':'0'*64});self.save()
        with self.assertRaises(ContractError):expected_outputs(self.product,self.checkout,self.manifest)

    def test_overlay_applied_state_rejects_symlink_and_tampering(self):
        self.overlay();apply_contract(self.product,self.checkout,True)
        self.assertEqual(verify_source_state(self.product,self.checkout,self.manifest),'applied')
        target=self.checkout/'trinol/assets/logo.svg';target.write_text('changed')
        with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest)
        target.unlink();target.symlink_to(self.product/'logo.svg')
        with self.assertRaises(ContractError):verify_source_state(self.product,self.checkout,self.manifest)

    def test_partial_write_failure_reports_completed_patches(self):
        import apply_product_patches as module
        real_git=module.git
        def failure(checkout,*args,**kwargs):
            if args==('apply',str(self.product/'patches/second.patch')):
                raise OSError('synthetic disk error')
            return real_git(checkout,*args,**kwargs)
        with patch.object(module,'git',side_effect=failure):
            with self.assertRaises(ContractError) as error:apply_contract(self.product,self.checkout,True)
        self.assertEqual(error.exception.applied,['patches/first.patch'])
        self.assertEqual((self.checkout/'file.txt').read_text(),'two\n')
