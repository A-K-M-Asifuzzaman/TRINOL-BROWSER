"""Safe storage preflight tests: temporary paths and mocked native metadata only."""
from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_chromium_build_storage.py'
spec = importlib.util.spec_from_file_location('storage_preflight', SCRIPT)
s = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = s
spec.loader.exec_module(s)


class FakeProbe:
    def __init__(self):
        self.primary = s.Volume('disk7s2', '/Volumes/Build', 'apfs', 311*s.GIB,
                                477*s.GIB, True, ('disk6s2',), 'USB')
        self.backing = s.Volume('disk6s3', '/Volumes/Backing', 'hfs', 345*s.GIB,
                                477*s.GIB, True, ('disk6s3',), 'USB')
        self.image_list = []
        self.image_file = None
        self.physical = {'disk6'}
        self.metadata = {
            'disk6s2': {'ParentWholeDisk': 'disk6'},
            'disk6s3': {'ParentWholeDisk': 'disk6'},
            'disk6': {'VirtualOrPhysical': 'Physical'},
            'disk8s1': {'ParentWholeDisk': 'disk8'},
            'disk8': {'VirtualOrPhysical': 'Virtual'},
        }

    def volume(self, path):
        return self.backing if self.image_file == path else self.primary

    def images(self):
        return self.image_list

    def disk(self, device):
        return self.metadata[device]

    def physical_disks(self):
        return self.physical

    def use_image(self, path):
        path.touch()
        self.image_file = path.resolve()
        self.primary = replace(self.primary, device='disk9s1', stores=('disk8s1',))
        self.image_list = [{'image-path': str(path), 'writeable': True,
                            'system-entities': [{'dev-entry': '/dev/disk8'},
                                                {'dev-entry': '/dev/disk9s1'}]}]


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='trinol-storage-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.destination = self.root / 'future' / 'chromium'
        self.probe = FakeProbe()

    def run_check(self, **kwargs):
        defaults = dict(raw=str(self.destination), system='Darwin', machine='arm64', probe=self.probe)
        defaults.update(kwargs)
        return s.check(**defaults)

    def assertBlocked(self, findings, fragment):
        self.assertTrue(any(level == 'BLOCKED' and fragment in message
                            for level, message in findings), findings)

    def assertReady(self, findings):
        self.assertFalse(any(level == 'BLOCKED' for level, _ in findings), findings)

    def test_future_path_uses_existing_parent_without_creating_anything(self):
        self.assertReady(self.run_check())
        self.assertFalse(self.destination.parent.exists())

    def test_wrong_os(self):
        self.assertBlocked(self.run_check(system='Linux'), 'requires macOS')

    def test_rosetta_or_intel(self):
        self.assertBlocked(self.run_check(machine='x86_64'), 'arm64')

    def test_spaces_in_entered_path(self):
        self.assertBlocked(self.run_check(raw=str(self.root / 'space here')), 'whitespace')

    def test_tabs_in_path(self):
        self.assertBlocked(self.run_check(raw=str(self.root / 'tab\there')), 'whitespace')

    def test_symlink_cannot_hide_spaces(self):
        target = self.root / 'space here'
        target.mkdir()
        alias = self.root / 'alias'
        alias.symlink_to(target)
        self.assertBlocked(self.run_check(raw=str(alias / 'chromium')), 'Resolved checkout path')

    def test_symlink_loop_is_blocked(self):
        loop = self.root / 'loop'
        loop.symlink_to(loop)
        self.assertBlocked(self.run_check(raw=str(loop / 'chromium')), '')

    def test_missing_volume_is_not_internal_storage_success(self):
        self.assertBlocked(self.run_check(raw='/Volumes/TrinolUnitTestMissing/chromium'), 'not mounted')

    def test_actual_hfs_is_rejected_despite_apfs_sounding_name(self):
        self.probe.primary = replace(self.probe.primary, filesystem='hfs')
        self.assertBlocked(self.run_check(raw=str(self.root / 'APFSBuild')), 'not APFS')

    def test_readonly_volume(self):
        self.probe.primary = replace(self.probe.primary, writable=False)
        self.assertBlocked(self.run_check(), 'read-only')

    def test_capacity_below_combined_budget(self):
        self.probe.primary = replace(self.probe.primary, available=249*s.GIB)
        self.assertBlocked(self.run_check(), 'required budget 200')

    def test_exact_capacity_boundary(self):
        self.probe.primary = replace(self.probe.primary, available=250*s.GIB)
        self.assertReady(self.run_check())

    def test_cannot_lower_capacity_policy(self):
        self.assertBlocked(self.run_check(minimum_gib=1), 'at least 200')
        self.assertBlocked(self.run_check(headroom_gib=0), '50 GiB')

    def test_nonempty_destination_is_preserved(self):
        self.destination.mkdir(parents=True)
        item = self.destination / 'DEPS'
        item.write_text('existing work')
        self.assertBlocked(self.run_check(), 'nonempty')
        self.assertEqual(item.read_text(), 'existing work')

    def test_empty_destination_is_allowed(self):
        self.destination.mkdir(parents=True)
        self.assertReady(self.run_check())

    def test_ancestor_repository_conflict(self):
        (self.root / '.git').mkdir()
        self.assertBlocked(self.run_check(), 'existing repository')

    def test_ancestor_gclient_conflict(self):
        (self.root / '.gclient').touch()
        self.assertBlocked(self.run_check(), 'existing repository')

    def test_existing_file_parent(self):
        (self.root / 'future').touch()
        self.assertBlocked(self.run_check(), '')

    def test_access_denied(self):
        with patch.object(s.os, 'access', return_value=False):
            self.assertBlocked(self.run_check(), 'permission')

    def test_inspection_permission_exception(self):
        with patch.object(self.probe, 'volume', side_effect=PermissionError('permission denied')):
            self.assertBlocked(self.run_check(), 'permission denied')

    def test_missing_disk_inventory(self):
        with patch.object(self.probe, 'images', side_effect=s.InspectionError('inventory unavailable')):
            self.assertBlocked(self.run_check(), 'inventory unavailable')

    def test_unknown_physical_backing(self):
        self.probe.physical = set()
        self.assertBlocked(self.run_check(), 'no verified image backing')

    def test_physical_inventory_handles_unknown_virtual_flag(self):
        self.probe.metadata['disk6']['VirtualOrPhysical'] = 'Unknown'
        self.assertReady(self.run_check())

    def test_sparse_image_with_sufficient_physical_backing(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        result = self.run_check()
        self.assertReady(result)
        self.assertTrue(any('physical backing available 345.0' in message for _, message in result))

    def test_large_virtual_image_cannot_hide_low_physical_capacity(self):
        self.probe.use_image(self.root / 'build.sparseimage')
        self.probe.primary = replace(self.probe.primary, available=900*s.GIB, total=1000*s.GIB)
        self.probe.backing = replace(self.probe.backing, available=100*s.GIB)
        self.assertBlocked(self.run_check(), 'Effective available 100.0')

    def test_virtual_capacity_is_also_a_limit(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        self.probe.primary = replace(self.probe.primary, available=100*s.GIB)
        self.assertBlocked(self.run_check(), 'Effective available 100.0')

    def test_image_backing_path_can_contain_spaces(self):
        self.probe.use_image(self.root / 'backing image.sparsebundle')
        self.assertReady(self.run_check())

    def test_unmapped_image_is_blocked(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        self.probe.image_list = []
        self.assertBlocked(self.run_check(), 'no verified image backing')

    def test_readonly_image(self):
        self.probe.use_image(self.root / 'build.dmg')
        self.probe.image_list[0]['writeable'] = False
        self.assertBlocked(self.run_check(), 'Read-only')

    def test_shadow_image(self):
        self.probe.use_image(self.root / 'build.dmg')
        self.probe.image_list[0]['shadow-path'] = '/tmp/example.shadow'
        self.assertBlocked(self.run_check(), 'shadow-backed')

    def test_missing_backing_file(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        self.probe.image_file.unlink()
        self.assertBlocked(self.run_check(), '')

    def test_backing_filesystem_readonly(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        self.probe.backing = replace(self.probe.backing, writable=False)
        self.assertBlocked(self.run_check(), 'backing filesystem is read-only')

    def test_nested_images_blocked(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        self.probe.image_list.append({'system-entities': [{'dev-entry': '/dev/disk6s3'}]})
        self.assertBlocked(self.run_check(), 'Nested disk images')

    def test_ambiguous_backing_blocked(self):
        self.probe.use_image(self.root / 'build.sparsebundle')
        self.probe.image_list *= 2
        self.assertBlocked(self.run_check(), 'Ambiguous')


class NativeMetadataTests(unittest.TestCase):
    def setUp(self):
        self.probe = s.MacProbe()
        self.disk = dict(DeviceIdentifier='disk7s2', MountPoint='/Volumes/Build',
                         FilesystemType='apfs', Writable=True, TotalSize=477*s.GIB)
        self.container = dict(CapacityFree=300*s.GIB,
                              PhysicalStores=[{'DeviceIdentifier': 'disk6s2'}],
                              Volumes=[dict(DeviceIdentifier='disk7s2', CapacityQuota=0)])

    def volume(self):
        with patch.object(self.probe, 'command', return_value=b'Filesystem blocks used avail capacity mounted\n/dev/disk7s2 1 1 1 1 /Volumes/Build\n'), \
             patch.object(self.probe, 'disk', return_value=self.disk), \
             patch.object(self.probe, 'plist', return_value={'Containers': [self.container]}), \
             patch.object(s.os, 'stat', return_value=SimpleNamespace(st_dev=7)), \
             patch.object(s.os, 'statvfs', return_value=SimpleNamespace(f_bavail=311, f_frsize=s.GIB)):
            return self.probe.volume(Path('/example/future-parent'))

    def test_container_free_caps_accessible_free(self):
        self.assertEqual(self.volume().available, 300*s.GIB)

    def test_volume_quota_caps_free(self):
        self.container['Volumes'][0].update(CapacityQuota=300*s.GIB, CapacityInUse=100*s.GIB)
        self.assertEqual(self.volume().available, 200*s.GIB)

    def test_missing_apfs_mapping_fails_closed(self):
        self.container['Volumes'] = []
        with self.assertRaises(s.InspectionError):
            self.volume()

    def test_missing_writable_flag_fails_closed(self):
        del self.disk['Writable']
        with self.assertRaises(s.InspectionError):
            self.volume()

    def test_command_timeout_is_inspection_error(self):
        with patch.object(s.subprocess, 'run', side_effect=subprocess.TimeoutExpired('diskutil', 30)):
            with self.assertRaises(s.InspectionError):
                self.probe.disk('disk1')

    def test_invalid_plist_is_inspection_error(self):
        with patch.object(self.probe, 'command', return_value=b'invalid plist'):
            with self.assertRaises(s.InspectionError):
                self.probe.disk('disk1')

    def test_empty_df_record_is_inspection_error(self):
        with patch.object(self.probe, 'command', return_value=b'Filesystem\n \n'):
            with self.assertRaises(s.InspectionError):
                self.probe.volume(Path('/example'))

    def test_physical_inventory_parsing(self):
        data = {'AllDisksAndPartitions': [{'DeviceIdentifier': 'disk0'},
                                         {'DeviceIdentifier': 'disk6'}]}
        with patch.object(self.probe, 'plist', return_value=data):
            self.assertEqual(self.probe.physical_disks(), {'disk0', 'disk6'})

    def test_missing_physical_inventory_is_inspection_error(self):
        with patch.object(self.probe, 'plist', return_value={}):
            with self.assertRaises(s.InspectionError):
                self.probe.physical_disks()


if __name__ == '__main__':
    unittest.main()
