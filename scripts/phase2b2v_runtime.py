"""One exact-build Orbit New Tab trial; historical gates remain immutable."""
import hashlib
import json
import os
from pathlib import Path

from build_chromium_macos import contained
import phase2b1v_runtime as previous

CLAIM = 'logs/TrinolLifecycle.phase2b2v-authorization.json'
BUILD_ROOT = Path('/Volumes/ssd(mac)2/TrinolBuild')
GUARD = 'logs/TrinolLifecycle.phase2b2v-review.json'
PRIOR = 'logs/phase2b1v-visual-xg70p26t'
OBSERVER = 'logs/phase2b1v-audit-2qxmjhtz/window-info'
CUSTOMIZATION_SHA256 = '041b497f44285a8e2708f8f20de0a9adede7555eb5c38bcd4363ace2d4ce147d'
LIBRARY_SHA256 = '1ae9d063141a0dedd309cde33fb5312ac7ca2caa3697c759b25e90043581d527'
OUT = 'chromium/src/out/TrinolDev/'
RESOURCES = 'Chromium Framework.framework/Versions/155.0.8059.85/Resources/'
PACK_SHA256 = '31e7050a1e730ab9720a9c03f309e9affa943c5eeba887d5490a79cbd984ed5e'
LOCALE_SHA256 = '8fb0e6cf49da6023c917062d142b0e37814a86f01a930e5564b280133a7ff72c'
ARTIFACTS = {
    OUT + 'Chromium.app/Contents/MacOS/Chromium': previous.LAUNCHER_SHA256,
    OUT + 'libchrome_dll.dylib': LIBRARY_SHA256,
    OUT + 'args.gn': previous.GN_ARGS_SHA256,
    OUT + RESOURCES + 'resources.pak': PACK_SHA256,
    OUT + RESOURCES + 'en.lproj/locale.pak': LOCALE_SHA256,
    OUT + 'Chromium.app/Contents/Frameworks/' + RESOURCES + 'resources.pak': PACK_SHA256,
    OUT + 'Chromium.app/Contents/Frameworks/' + RESOURCES + 'en.lproj/locale.pak': LOCALE_SHA256,
}
HISTORY = {
    'logs/TrinolLifecycle.phase2b1v-authorization.json': 'cae04f8a5f18d88e501c0f3878d0c3f0f1b378c756d5d626c1adbff474dda054',
    'logs/TrinolLifecycle.blocked.json': '9fc11c9eff52b98bd122b8b61edf9a92e99eb6df4ade438203664ee24380623b',
    PRIOR + '/result.json': 'd179c23b785e7095d78415a35d70385ff931b74165023d08d69180459dc5270e',
    PRIOR + '/launch.json': '0cea02aebc02889f44f487f5fde146d8ddae91c4f96a1e48beb10a2040083065',
    PRIOR + '/events.jsonl': '0482c73f28d0185dfc15a87c45b0eb763d9bbf80afe4522704b8aff4ede3fd70',
    PRIOR + '/samples.jsonl': 'b5cc117a12c9921dd085151b8cf9cac583cf052d814c33cdcba90099cc292fa9',
    PRIOR + '/final-health.json': 'ca05ce82af837cce9231f459954fbe92a0b555057440739534491c9a2e92ca82',
    PRIOR + '/browser.log': '8f04786a9fc1b5192af3cad0b450c5233c7b77286fcf7f4f0098c570ff2cd96c',
    PRIOR + '/timings.jsonl': '6ff5b0e2e62da196bb8df8a0f1666d3c09ad98325a32a028fae34117c81cb3a5',
    PRIOR + '/visual-review.json': 'b285e24a000383dd6524598e365ec4eea2d4979c092a9fe9bea870301506fca9',
    **{'logs/TrinolLifecycle.' + name + '-reviewed.json': digest
       for name, digest in previous.ARCHIVES.items()},
    **{previous.PRIOR + '/' + name: digest for name, digest in previous.PRIOR_FILES.items()},
}
sha256 = previous.sha256
check_observer = previous.check_observer
retain_visual_guard = previous.retain_visual_guard


def check_options(operator, seconds, grace, workload, legacy):
    if not operator:
        raise ValueError('2B2-V requires fresh present/unlocked operator confirmation')
    if legacy or (seconds, grace, workload) != (360, 30, 'blank'):
        raise ValueError('2B2-V requires its own flag, 360 seconds, 30-second grace and blank workload')


def check_records(root, records):
    for name, digest in records.items():
        if sha256(contained(root, name)) != digest:
            raise ValueError('Reviewed file changed: ' + name)


def review(root, rows, manifest, observer):
    # Caller holds the existing exclusive build/runtime lock and verifies the
    # full applied source contract; this adds immutable exact-build identities.
    if root != BUILD_ROOT:
        raise ValueError('Exact reviewed build root required')
    if rows:
        raise ValueError('Existing compiled-app processes; no overlapping launch')
    if contained(root, CLAIM).exists() or contained(root, GUARD).exists():
        raise ValueError('Phase 2B2-V consumed or pending review; no retry')
    if (manifest['chromium']['revision'] != '0e66b94549a8bd85f03fbdf189b752d6e7b63c32'
            or manifest['chromium']['version'] != '155.0.8059.85'
            or manifest['depot_tools']['revision'] != 'dca727ba1f8fa8f1e3b12a815d065818bb61d395'
            or hashlib.sha256(json.dumps(manifest['customization'], sort_keys=True).encode()).hexdigest()
            != CUSTOMIZATION_SHA256):
        raise ValueError('Exact reviewed three-patch/two-overlay source contract required')
    check_records(root, HISTORY)
    check_records(root, ARTIFACTS)
    if observer != contained(root, OBSERVER):
        raise ValueError('Exact previously reviewed observer path required')
    check_observer(root, observer)
    return dict(phase='2b2-v', authorization='Phase 2B2-V section 5; ONE exact-build New Tab trial',
                source_contract_sha256=CUSTOMIZATION_SHA256, artifact_sha256=ARTIFACTS,
                historical_sha256=HISTORY, observer=str(observer),
                observer_sha256=previous.OBSERVER_SHA256,
                corrected_library_sha256=LIBRARY_SHA256)


def check_profile(root, profile, crash):
    profile = contained(root, profile.relative_to(root))
    if (profile.parent != root or not profile.name.startswith('test-profile-2b2v-')
            or not profile.is_dir() or profile.stat().st_uid != os.getuid()
            or profile.stat().st_mode & 0o777 != 0o700
            or crash != contained(root, (profile / 'Crashpad-isolated').relative_to(root))
            or not crash.is_dir() or crash.stat().st_mode & 0o777 != 0o700
            or list(profile.iterdir()) != [crash] or list(crash.iterdir())):
        raise ValueError('Expected a fresh private Phase 2B2-V profile and empty isolated Crashpad')


def claim(root, run, authorization):
    # Exclusive creation precedes the new active guard; no historical file moves.
    with contained(root, CLAIM).open('x') as stream:
        json.dump(dict(evidence=str(run), authorization=authorization), stream, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
