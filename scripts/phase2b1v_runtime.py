"""Exact, one-use Phase 2B1-V authorization; no browser launch or retry bypass."""
import hashlib
import json
import os
import subprocess

from build_chromium_macos import EXPECTED_VOLUME_UUID, contained

LIBRARY_SHA256 = 'f4f64292a78c8758c2be665177dfc39103432105ecc4deacd9dfc4baec619afe'
LAUNCHER_SHA256 = '62fa3b0be1ef7404d53911c5b28777da7ce441483b00b6271f4a4da494501fae'
GN_ARGS_SHA256 = 'cabeadd749736e664c312aca9303a57edd103c34fcc39d66d782128c4f44c1ab'
CUSTOMIZATION_SHA256 = '4283d491ae001bae8da9c083928dfb89af32adf396f011fb5acc738c91dcd29c'
OBSERVER_SHA256 = '3f328dc3cfb4ad60109ce8c2d68a62c66ba6470763da2b5e2a99c4511a819b29'
ARCHIVE_SHA256 = 'ccc213f095ea07c8dc20fa086a00d87ce4297645a29a5b82bafbd6debdea5655'
ARCHIVES = {'r6-ui': ARCHIVE_SHA256,
            'r4': 'c2c2c21b47a933abcf91fc90aaa3573f3863fa6bc642ed7302deea5f2807ad5c',
            'r5': '64d564e0812b88b8ed8f201a69e038f077600c1a3e461f6a34c41aaeafd6a4ef'}
CLAIM = 'logs/TrinolLifecycle.phase2b1v-authorization.json'
PRIOR = 'logs/phase2b1-ui-end3_z48'
PRIOR_FILES = {
    'result.json': '2e385a4db157be3d121c4e9ea21aa391f39ef162cff81354411d77fb486b9c42',
    'launch.json': 'd2634ae29151ada9551575251a398cf795064578bc8e3cb7d15ac0dc9a78a315',
    'events.jsonl': 'fbda2059909312643f5a868eee5629c988e4ec6587972a5062dd941fc8d6f0b1',
    'samples.jsonl': '23ea037e6af29966c1e8a1bbc69051c0a57c5fcc70738c001a6dd6a023ee47c6',
    'final-health.json': '7ae6cd07d46bf995cfce2e070afeac109cbf1dc4d0eeaa6aa8e5df433810bfbd',
    'browser.log': 'fb578ec22e78755cd580a000c3243e6606fd350f13ae7750cab27cbc42e3ae40',
    'timings.jsonl': '196829b3e9f8bef428d38bff8d36687a6cc234726d9afb8c5416e408954d1b29',
    'rendering.html': '1e41095f8ad6a2d34db277b295ef5f203091f60788788ea59908775eb138c993',
    'window-metadata.json': '389eb73b3d07666a9492bacdf552bc2b8cd66ae1b3b1d979799006a900617aab',
    'native-initial.png': 'ebdea59caef193001479f512fb8f87b7f098f0a1d8ea9902973f15629775481e',
    'native-middle.png': '3935ee9fe565306d7ab048983034031a69a2972f6fdd5ccfd35e8b1d7e645eb0',
    'native-late.png': '2ec07451fb5e5f3609b5dc7cdbe35897c3b7f45c0513c8317e12337f3e3913db',
}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_observer(root, observer):
    observer = contained(root, observer.relative_to(root))
    if sha256(observer) != OBSERVER_SHA256 or not os.access(observer, os.X_OK):
        raise ValueError('Observer differs from the nonlaunching utility tested in Phase 2B1')
    result = subprocess.run([str(observer), '1'], capture_output=True, timeout=5)
    if result.returncode != 2 or result.stdout or result.stderr:
        raise ValueError('Read-only observer invalid-PID self-check failed')
    return observer


def review(root, rows, manifest, observer):
    if rows or contained(root, CLAIM).exists():
        raise ValueError('Phase 2B1-V already consumed or previous compiled processes remain')
    if contained(root, 'logs/TrinolLifecycle.blocked.json').exists():
        raise ValueError('Active lifecycle/visual failure requires separate review')
    if (manifest['chromium']['revision'] != '0e66b94549a8bd85f03fbdf189b752d6e7b63c32'
            or manifest['depot_tools']['revision'] != 'dca727ba1f8fa8f1e3b12a815d065818bb61d395'
            or hashlib.sha256(json.dumps(manifest['customization'], sort_keys=True,
                separators=(',', ':')).encode()).hexdigest() != CUSTOMIZATION_SHA256):
        raise ValueError('Phase 2B1-V requires the exact reviewed revision and two-patch state')
    for name, digest in ARCHIVES.items():
        if sha256(contained(root, 'logs/TrinolLifecycle.' + name + '-reviewed.json')) != digest:
            raise ValueError('Earlier immutable marker archive changed')
    for name, digest in PRIOR_FILES.items():
        if sha256(contained(root, PRIOR + '/' + name)) != digest:
            raise ValueError('Previous 2B1 evidence changed: ' + name)
    result = json.loads(contained(root, PRIOR + '/result.json').read_text())
    launch = json.loads(contained(root, PRIOR + '/launch.json').read_text())
    health = json.loads(contained(root, PRIOR + '/final-health.json').read_text())
    writer = result['evidence_writer']
    if (result['clean_shutdown'] != 'PASS' or result['exit_code'] != 0 or result['failure']
            or not result['quit_requested'] or result['remaining'] or result['unexpected_remaining']
            or result['watchdog'] or result['dumps'] or result['cleanup_required']
            or result['pid'] != launch['pid'] or result['pid'] != 20381
            or result['profile'] != launch['profile']
            or launch['command'][0] != str(root / 'chromium/src/out/TrinolDev/Chromium.app/Contents/MacOS/Chromium')
            or launch['profile'] != str(root / 'test-profile-2b1-l0_1332k')
            or result['max_poll_gap'] > 15 or result['max_observation_gap'] > 15
            or health['remaining'] or health['volume_uuid'] != EXPECTED_VOLUME_UUID
            or writer['error'] or not writer['flushed'] or writer['dropped']
            or writer['unacknowledged'] or writer['submitted'] != writer['acknowledged']
            or writer['writer_remaining']):
        raise ValueError('Previous bounded session does not establish the reviewed clean lifecycle')
    library = contained(root, 'chromium/src/out/TrinolDev/libchrome_dll.dylib')
    if (sha256(library) != LIBRARY_SHA256 or
            library.stat().st_mtime <= launch['start_time_unix'] + result['elapsed_seconds']):
        raise ValueError('Corrected library digest/after-session chronology mismatch')
    if (sha256(contained(root, 'chromium/src/out/TrinolDev/Chromium.app/Contents/MacOS/Chromium')) != LAUNCHER_SHA256
            or sha256(contained(root, 'chromium/src/out/TrinolDev/args.gn')) != GN_ARGS_SHA256):
        raise ValueError('Reviewed launcher or preserved GN arguments changed')
    observer = check_observer(root, observer)
    return dict(phase='2b1-v', authorization='User Phase 2B1-V sections 6 and 11; ONE corrected-palette trial',
                previous_evidence=PRIOR, previous_sha256=PRIOR_FILES,
                r6_archive_sha256=ARCHIVE_SHA256, corrected_library_sha256=LIBRARY_SHA256,
                observer=str(observer), observer_sha256=OBSERVER_SHA256)


def claim(root, run, authorization):
    # Caller holds the shared build/runtime lock. This permanent exclusive claim
    # blocks all modes before the active marker is created, including on a crash.
    with contained(root, CLAIM).open('x') as stream:
        json.dump(dict(evidence=str(run), authorization=authorization), stream, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def retain_visual_guard(latch, run, result):
    # Lifecycle PASS is independent of visual acceptance. Never clear this gate.
    temporary = run / 'visual-review-marker.json'
    with temporary.open('x') as stream:
        json.dump(dict(evidence=str(run), result=result,
                       visual_validation=result.get('visual_validation', 'PENDING_REVIEW')), stream)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, latch)
