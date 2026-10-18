#!/usr/bin/env python3
"""Read-only macOS Chromium checkout preflight. Exit 0 ready, 1 blocked, 2 usage.

Uses actual df/diskutil/hdiutil metadata and f_bavail, never volume names as
filesystem evidence. Does not create directories, probe writes, mount images,
install tools or download sources. A pass is a point-in-time capacity check.
"""
import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import plistlib
import subprocess

GIB = 1024 ** 3


class InspectionError(Exception):
    """Missing, contradictory or unsupported storage evidence."""


@dataclass
class Volume:
    device: str
    mount: str
    filesystem: str
    available: int
    total: int
    writable: bool
    stores: tuple
    protocol: str


class MacProbe:
    """All native commands are read-only and bounded; no shell interpolation."""

    def command(self, *args):
        try:
            return subprocess.run(args, check=True, capture_output=True,
                                  timeout=30).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            raise InspectionError(f'{args[0]} inspection failed: {exc}') from exc

    def plist(self, *args):
        try:
            value = plistlib.loads(self.command(*args))
            if not isinstance(value, dict):
                raise ValueError('expected dictionary')
            return value
        except (ValueError, plistlib.InvalidFileException) as exc:
            raise InspectionError(f'Invalid {args[0]} metadata') from exc

    def disk(self, device):
        return self.plist('/usr/sbin/diskutil', 'info', '-plist', device)

    def images(self):
        data = self.plist('/usr/bin/hdiutil', 'info', '-plist')
        if not isinstance(data.get('images'), list):
            raise InspectionError('Disk image inventory unavailable')
        return data['images']

    def physical_disks(self):
        # Apple Silicon can report VirtualOrPhysical=Unknown for its real SSD.
        # Use diskutil's physical-device inventory instead of guessing by bus/name.
        data = self.plist('/usr/sbin/diskutil', 'list', '-plist', 'physical')
        if not isinstance(data.get('AllDisksAndPartitions'), list):
            raise InspectionError('Physical disk inventory unavailable')
        return {disk['DeviceIdentifier'] for disk in data['AllDisksAndPartitions']}

    def volume(self, path):
        # diskutil info does not accept arbitrary directory paths; df identifies
        # the actual containing device, including APFS Data-volume firmlinks.
        lines = self.command('/bin/df', '-P', str(path)).decode().splitlines()
        fields = lines[1].split() if len(lines) == 2 else []
        if not fields or not fields[0].startswith('/dev/'):
            raise InspectionError('Cannot identify local containing device')
        info = self.disk(fields[0])
        required = ('DeviceIdentifier', 'MountPoint', 'FilesystemType', 'Writable', 'TotalSize')
        if any(key not in info for key in required) or not info['MountPoint']:
            raise InspectionError('Incomplete mounted-filesystem metadata')
        if os.stat(path).st_dev != os.stat(info['MountPoint']).st_dev:
            raise InspectionError('Containing filesystem changed during inspection')
        stat = os.statvfs(path)
        free = stat.f_bavail * stat.f_frsize
        stores = (info['DeviceIdentifier'],)
        if info['FilesystemType'].lower() == 'apfs':
            containers = self.plist('/usr/sbin/diskutil', 'apfs', 'list', '-plist')
            matches = [(container, volume)
                       for container in containers.get('Containers', [])
                       for volume in container.get('Volumes', [])
                       if volume.get('DeviceIdentifier') == info['DeviceIdentifier']]
            if len(matches) != 1:
                raise InspectionError('Cannot resolve APFS volume to its container')
            container, volume = matches[0]
            if 'CapacityFree' not in container:
                raise InspectionError('APFS container free capacity unavailable')
            free = min(free, container['CapacityFree'])
            quota = volume.get('CapacityQuota', 0)
            if quota:
                free = min(free, max(0, quota - volume['CapacityInUse']))
            stores = tuple(s['DeviceIdentifier'] for s in container.get('PhysicalStores', []))
            if not stores:
                raise InspectionError('APFS physical store mapping unavailable')
        return Volume(info['DeviceIdentifier'], info['MountPoint'],
                      info['FilesystemType'].lower(), free, info['TotalSize'],
                      info['Writable'] is True, stores, info.get('BusProtocol', 'unknown'))


def capacity(volume, probe, images, report, nested=False):
    """Conservatively bound virtual free space by backing physical free space."""
    devices = {volume.device}
    whole_disks = []
    for store in volume.stores:
        devices.add(store)
        store_info = probe.disk(store)
        whole = store_info.get('ParentWholeDisk')
        if not whole:
            raise InspectionError('Physical store parent is unknown')
        devices.add(whole)
        whole_disks.append(whole)
    matches = [image for image in images
               if devices & {entity.get('dev-entry', '').removeprefix('/dev/')
                             for entity in image.get('system-entities', [])}]
    if len(matches) > 1:
        raise InspectionError('Ambiguous disk-image backing mapping')
    if not matches:
        physical = probe.physical_disks()
        if not whole_disks or not set(whole_disks) <= physical:
            raise InspectionError('Virtual/unknown storage has no verified image backing')
        report('PASS', f'Physical backing verified; protocol {volume.protocol}')
        return volume.available
    if nested:
        raise InspectionError('Nested disk images require separate review')
    image = matches[0]
    if image.get('writeable') is not True or any('shadow' in k and v for k, v in image.items()):
        raise InspectionError('Read-only or shadow-backed images are not supported')
    raw = image.get('image-path')
    if not raw or not Path(raw).is_absolute():
        raise InspectionError('Image backing file path unavailable')
    backing_path = Path(raw).resolve(strict=True)
    if not os.access(backing_path, os.R_OK | os.W_OK):
        raise InspectionError('Image backing file is not readable/writable')
    backing_volume = probe.volume(backing_path)
    if not backing_volume.writable:
        raise InspectionError('Image backing filesystem is read-only')
    backing_free = capacity(backing_volume, probe, images, report, nested=True)
    report('WARNING', f'Disk image: {backing_path}; virtual volume total '
           f'{volume.total / GIB:.1f} GiB, virtual available {volume.available / GIB:.1f} GiB; '
           f'physical backing available {backing_free / GIB:.1f} GiB')
    report('WARNING', 'Conservative growth bound; allocated image space is not added '
           'to backing free space. Disconnects/exhaustion can damage the image.')
    return min(volume.available, backing_free)


def resolve_destination(raw):
    entered = Path(raw).expanduser().absolute()
    if any(c.isspace() for c in str(entered)):
        raise InspectionError('Checkout path contains whitespace')
    resolved = entered.resolve(strict=False)
    if any(c.isspace() for c in str(resolved)):
        raise InspectionError('Resolved checkout path contains whitespace')
    ancestor = resolved
    while True:
        try:
            ancestor.stat()
            break
        except FileNotFoundError:
            if ancestor == ancestor.parent:
                raise InspectionError('No existing parent directory')
            ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise InspectionError('Destination or existing parent is not a directory')
    # Do not accidentally validate a missing /Volumes mount against internal APFS.
    if len(resolved.parts) > 2 and resolved.parts[1] == 'Volumes':
        expected_mount = Path(*resolved.parts[:3])
        if not os.path.ismount(expected_mount):
            raise InspectionError(f'Expected volume is not mounted: {expected_mount}')
    if not os.access(ancestor, os.W_OK | os.X_OK):
        raise InspectionError(f'No write/search permission on existing parent: {ancestor}')
    if ancestor == resolved and next(resolved.iterdir(), None) is not None:
        raise InspectionError('Destination is nonempty; inspect existing checkout/data manually')
    for parent in (ancestor, *ancestor.parents):
        if any(os.path.lexists(parent / marker) for marker in ('.git', '.gclient', '.gclient_entries')):
            raise InspectionError(f'Destination overlaps an existing repository/checkout: {parent}')
        if os.path.ismount(parent):
            break
    return resolved, ancestor


def check(raw, minimum_gib=200, headroom_gib=50, probe=None,
          system=None, machine=None):
    findings = []

    def report(level, message):
        findings.append((level, message))

    try:
        if minimum_gib < 200 or headroom_gib < 50:
            raise InspectionError('Policy requires at least 200 GiB plus 50 GiB safety headroom')
        if (system or platform.system()) != 'Darwin':
            raise InspectionError('This preflight requires macOS')
        if (machine or platform.machine()) != 'arm64':
            raise InspectionError('Run natively on Apple Silicon (arm64), not under Rosetta')
        report('PASS', 'macOS with native Apple Silicon execution')
        destination, ancestor = resolve_destination(raw)
        report('PASS', f'Resolved destination: {destination}; existing parent: {ancestor}')
        probe = probe or MacProbe()
        volume = probe.volume(ancestor)
        if volume.filesystem != 'apfs':
            raise InspectionError(f'Actual containing filesystem is {volume.filesystem}, not APFS')
        if not volume.writable:
            raise InspectionError('Containing volume is read-only')
        report('PASS', f'Actual APFS volume {volume.device} mounted at {volume.mount}; '
               f'accessible free {volume.available / GIB:.1f} GiB')
        effective_free = capacity(volume, probe, probe.images(), report)
        usable = max(0, effective_free - headroom_gib * GIB)
        report('PASS' if usable >= minimum_gib * GIB else 'BLOCKED',
               f'Effective available {effective_free / GIB:.1f} GiB; '
               f'safety headroom {headroom_gib} GiB; budget after headroom '
               f'{usable / GIB:.1f} GiB; required budget {minimum_gib} GiB')
        if usable >= minimum_gib * GIB:
            report('WARNING', 'Capacity is shared and not reserved. Recheck before downloads/builds. '
                   'Read-only access checks do not prove a write will succeed; no write probe was made.')
    except (InspectionError, OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        report('BLOCKED', str(exc))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout_path', help='Explicit proposed fresh Chromium checkout directory')
    parser.add_argument('--minimum-free-gib', type=int, default=200)
    parser.add_argument('--headroom-gib', type=int, default=50)
    args = parser.parse_args()
    findings = check(args.checkout_path, args.minimum_free_gib, args.headroom_gib)
    for level, message in findings:
        print(f'{level}: {message}')
    blocked = any(level == 'BLOCKED' for level, _ in findings)
    print('RESULT: BLOCKED' if blocked else 'RESULT: PASS WITH WARNINGS (storage only)')
    return 1 if blocked else 0


if __name__ == '__main__':
    raise SystemExit(main())
