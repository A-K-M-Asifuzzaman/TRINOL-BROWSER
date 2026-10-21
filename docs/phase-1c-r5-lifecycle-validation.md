# Phase 1C-R5 — lifecycle validation

**Verdict: PARTIAL.** The single approved blank-session retry captured native
Quit acceptance, actual browser exit **0**, and complete helper cleanup. It
finished in 49.69 seconds without a watchdog or dump. However, a 36.95-second
startup observation gap invalidated the continuously supervised test. The
supervisor correctly returned **1 / FAIL**. No second launch is authorized by
this failed result; Phase 1C remains partial and Phase 2 remains gated.

## Approved baseline and initial checks

The product repository began clean on `main` at
`293d8422af27f3d3ca52d296026d7623f1f85e20`, equal to fetched origin/main.
GitHub owner `A-K-M-Asifuzzaman` (ID 138548302) and the existing author
`Asif Zman <138548302+asif4762@users.noreply.github.com>` were verified and preserved.
AGENTS, architecture, roadmap, build history, R4 investigation, upstream workflow,
manifest, lifecycle code/tests and the build runner were inspected. R3/R4 launch,
shutdown, cleanup, marker and dump-metadata records remain preserved externally.

Native Darwin arm64, writable APFS UUID
`47F505A1-126A-4EC6-8DB6-135813AA6111`, physical capacity, pressure and process
health passed preflight. Disk7s2/disk6s2 were observed identifiers, not the identity
contract. No compiled-app processes or active compiler existed before launch.
The initial read-only audit found 270,761,766,912 physical available bytes and
normal pressure (1). The later actual trial again passed preflight, recording
baseline swap 4,986,178,109 bytes and normal pressure. Swap level alone was not
classified as unsafe growth.

Final verification at 17:34:50 UTC found no task-owned browser/helpers, pressure
1, swap 4,969,400,893 bytes and physical available capacity 270,300,246,016 bytes.
The APFS UUID, executable and tracked source/tool verification still passed.

The verifier passed the unchanged Chromium version **155.0.8059.85**, source
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32` and depot_tools
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`, including tracked cleanliness, tag,
origins and DEPS digest. Exact launcher Mach-O architecture, executable permission
and bundle identity passed. The completed 39,487-action, exit-0 build is preserved.
No GN generation, source patch, dependency synchronization, signing change,
diagnostic-tool build or browser compilation occurred.

## Failure-marker review and one-use authorization

The existing `logs/TrinolLifecycle.blocked.json` was the original R4 failure:
PID 55645, no browser exit status, supervisor failure on native Quit refusal.
Its evidence, launch, samples, browser log, result and later cleanup record were
present and consistent. Current process inspection found no old browser or
Crashpad/helper instance. The original marker's SHA-256 is:

`c2c2c21b47a933abcf91fc90aaa3573f3863fa6bc642ed7302deea5f2807ad5c`.

The user's Phase 1C-R5 section 8 explicitly authorized **one reviewed retry**
after safety and offline-test gates. The implementation's `--reviewed-r4-retry`
accepts only that digest and consistent evidence. Under the shared exclusive
build/runtime lock, it preserves the original bytes at
`logs/TrinolLifecycle.r4-reviewed.json` and atomically replaces the active marker
with the new in-progress record. There is no unguarded deletion interval and no
general force/ignore-safety switch. Archive creation refuses an existing archive;
future failure markers cannot pass the fixed R4 digest check.

The archived digest was verified after the trial. The active marker now references
the failed R5 run; it remains present. Do not remove it or reuse the R4 option.
The new launch record retains the old evidence path, archive digest and authorization.

## Native Quit audit

The previous JXA expression `app.terminate` **did invoke** the zero-argument
Objective-C selector. A harmless local custom Objective-C class proved that
property access invokes Boolean selectors and produces JavaScript `true`/`false`.
The installed SDK's NSRunningApplication header documents `terminate` as a normal
Quit request: true means sent, not exited. Apple's [terminate documentation](https://developer.apple.com/documentation/appkit/nsrunningapplication/terminate())
provides the same distinction. No unrelated application was terminated by this audit.

A separate read-only probe established that an absent application's Objective-C
nil wrapper is truthy in JavaScript (`typeof` reports function); `.isNil()` is
required. Registration and finished-launching properties were checked locally.
The script now distinguishes unregistered, registered, ready, exiting, refused,
accepted and identity mismatch. It validates the exact live PID/start/executable,
checks executableURL, waits for finishedLaunching, invokes terminate once per
attempt and requires an actual Boolean. It never uses forceTerminate or signals.
Popen polling remains the authority for exit status.

The R4 refusal's underlying reason is still unknown. Correct JXA invocation does
not retrospectively establish whether R4 was ready, exiting or temporarily refusing.

## Supervisor changes and regression coverage

- Preserve the original startup deadline; do not move Quit earlier because of U
  states or a delayed observation.
- Track U entry/recovery by full identity. Brief observed U intervals are alerts,
  not automatic permanent failure. Repeated U observations spanning at least
  15 seconds mark a persistent-state failure. Sampling gaps cannot prove continuous
  U residence. Never request Quit while the checked target/helpers are currently U.
- Poll the direct child before inspection, continue after temporary refusal,
  registration delay or monitor exceptions, and retain the real exit status.
- Limit native attempts to two, with at least five seconds between attempts.
  A refusal followed by accepted Quit can pass if every other criterion passes.
- Use one monotonic runtime-plus-grace deadline. Runtime command timeouts are the
  lesser of five seconds and remaining budget, including storage/memory probes.
  Do not issue a late Quit after an inspection consumes the budget.
- Preserve profile/Crashpad containment, APFS UUID/device/capacity checks, memory
  guards, exclusive locking, full process identity and helper ancestry tracking.
- Record spawn, identity, registration/readiness, U transitions, Quit attempts and
  responses, exit, helper exit, monitor errors and timeout in timestamped events.
  Watchdog discovery in the final log is explicitly a detection time, not a precise
  watchdog firing timestamp.
- Preserve evidence and the blocking marker on failure. If still live at timeout,
  emit an immediate operator-cleanup requirement; never invent successful cleanup.

After the trial, one small race correction was added: a fresh native check that
finds the same process U now returns a deferred state; an absent target is exiting,
while a reused PID still fails identity validation. It does not send Quit. This
follow-up is offline-tested and **was not rerun natively**.

All **162 repository tests pass**, including **49 lifecycle tests** (19 added
in R5). Coverage includes native Boolean/status interpretation, registration,
transient/persistent U, delayed sampling, refusal/retry/late exit, hard deadlines,
real mocked exit values, helpers, isolation, locking, changed mount/evidence
writes, unexpected errors, previous evidence preservation, single-use recovery
and failure-marker retention. No offline test launches Chromium or signals a real
process. Foundation, Python syntax, Bash syntax and whitespace checks pass.

## Operator presence and actual runtime

The operator explicitly confirmed availability. Native UI access initially reported
that the Mac was locked; **no browser was launched then**. After the operator
confirmed it was unlocked, a fresh native inventory succeeded and showed Chromium
not running. Only then was the following command executed:

```sh
python3 scripts/test_chromium_lifecycle_macos.py \
  --build-root '/Volumes/ssd(mac)2/TrinolBuild' \
  --volume-uuid 47F505A1-126A-4EC6-8DB6-135813AA6111 \
  --seconds 45 --grace-seconds 30 --reviewed-r4-retry
```

The trial used milestone `fc0024bdc26aea41263ddd795536bbbba32a73c3`.
Recorded spawn wall time: **2026-10-21 17:32:08.153 UTC**, PID **51860**.
All durations below use the monotonic clock rather than wall-clock differences.
The exact existing executable launched directly with one about:blank tab, a fresh
profile `test-profile-r5-l2wwxb29`, isolated Crashpad and normal security settings.

Evidence directory: `logs/phase1cr5-lifecycle-iuh2y3f4` under the approved build
root. It contains launch.json, samples.jsonl, events.jsonl, browser.log, result.json
and final-health.json. These raw records and profiles stay outside product Git.

| Elapsed seconds | Direct observation |
| --- | --- |
| 0.002 | Spawn recorded; direct Popen ownership retained |
| 0.113 | PID/start/executable/profile identity verified |
| 0.253 | Native application not yet registered |
| 2.435–4.564 | Browser U observation recovered; 2.128-second sampled interval |
| 4.640 | Native application registered |
| 6.766 | Sample includes browser and several helpers in U |
| 43.719 | Next completed process sample: those processes sleeping; 36.952-second sample gap |
| 45.100 | Observation-delay failure recorded |
| 45.146 | Fresh native check encountered absent/changed/U condition; monitor retained ownership |
| 47.298 | Next process sample; continued observation |
| 47.393 | Native finished-launching/readiness verified |
| 47.425 / 47.514 | Quit requested / actual Boolean acceptance |
| 49.519 | Popen observed browser exit **0** |
| 49.691 | No tracked browser/helpers; supervisor finished **1 / FAIL** |

There was exactly one Quit attempt, no refused response, no watchdog text and no
new dump. Accepted Quit to observed browser exit was approximately **2.005 s**.
No forced cleanup, second browser instance, restart or signal was needed.
A native UI inspection during startup timed out and yielded no responsive-GUI
pass. It did not replace the running Popen supervisor. No new instance was launched
when UI inspection failed. No session was left open across a continuation gap.

## What the observation gap does and does not establish

The gap is **confirmed** and invalidates continuous supervision. Within the
6.766-second sample's U-transition loop, the first event timestamp is 6.766 and
subsequent sibling event timestamps are about 41.58. This localizes a long pause
between event emissions, which include synchronous external evidence writes;
it does not measure the syscall or establish why it stalled. Filesystem evidence
I/O or host scheduling is **possible**, not a proven defective SSD.

The later event reports 40.532 seconds because the prior monitor exception left
the last-success timestamp unchanged. This is not a second independent 40-second
gap; the actual consecutive process-sample gap is 36.952 seconds. U-end spans
across that gap are observation intervals, not proof of continuous kernel sleep.
The persistent-U Boolean stayed false, but continuous state was unobservable.

Command subprocess timeouts do not bound Python filesystem operations, native
proc_pidpath, scheduling pauses or uninterruptible kernel I/O. In this run the
75-second total deadline was respected, but uninterrupted bounded observation
was not. The report does not claim that a Python supervisor guarantees hard
real-time execution on a stalled host.

## R3/R4/R5 comparison and cause classification

| Finding | Classification | Evidence and limitation |
| --- | --- | --- |
| R3 shutdown failure | CONFIRMED | Teardown watchdog/dump; main in GPU destruction response wait; actual exit status unknown |
| R4 initial supervision defect | CONFIRMED | Premature request and abandonment on refusal; later cleanup had no exit code |
| R5 native Quit invocation and child reaping | CONFIRMED | Accepted Boolean, actual exit 0 and no helpers, within 49.69 s |
| R5 complete lifecycle validation | FAIL | Startup observation gap; therefore browsing session/repetition ineligible |
| R5 transient U recheck classification defect | CONFIRMED in code | U was treated as a monitor error; actual runtime error combined absent/changed/U reasons, so its exact trigger is unresolved; correction not rerun |
| R5 slow startup/event observation | CONFIRMED symptom | Long pause before Quit, not a measured shutdown stall |
| R3 overall watchdog-budget exhaustion | POSSIBLE / UNRESOLVED | Earlier network wait can use the overall ten-second budget; no stage timings |
| R3 missing/delayed GPU response | POSSIBLE / UNRESOLVED | Browser-only wait stack; no paired GPU evidence |
| External storage causes browser failure | UNRESOLVED | Concurrent U and evidence-writing pause do not prove storage causality |
| Permanent Chromium shutdown repair | NOT ESTABLISHED | No browser patch and only one actual exit-0 observation, with invalid supervision |

No fresh watchdog dump exists to symbolicate. No active shutdown stall was present
long enough to justify paired debugger/sample attachment; the browser exited about
two seconds after acceptance. The R3 dump and its competing hypotheses stand.
No GPU disablement, watchdog extension, security bypass or speculative IPC patch
was applied. Existing code-sign clone/cross-device warnings recurred in the log;
this run supplies no causal connection between those warnings and the gap.

## Functional matrix and next action

| Check | R5 result |
| --- | --- |
| Exact compiled version/architecture and pins | PASS, metadata/source checks |
| Native registration/readiness | PASS, NSRunningApplication observations |
| Responsive GUI rendering | NOT TESTED; native inspection timed out; R3 evidence retained |
| Actual native Quit, exit 0, helper cleanup | PASS for these individual observations |
| Whole blank-session acceptance criteria | FAIL due to observation gap |
| Local HTML/JavaScript, HTTPS and two-tab browsing session | NOT TESTED; first trial did not pass |
| Independent repetition / repeatable clean shutdown | NOT TESTED; new failure marker blocks another launch |

Next engineering action: review the preserved timeline and add measured timing
around native process inspection and evidence writes, with a logging strategy
that cannot block the child-observation loop on the external build volume.
Validate that change offline, then seek a separately reviewed, operator-present
retry of the new R5 failure marker. Do not silently extend deadlines or relax the
observation-gap criterion. If a future **shutdown** stalls, collect paired
browser/GPU/network observations early in the unchanged watchdog window.

This phase's single retry is consumed. The R4 archive and R5 failure marker must
remain. Compilation and R3 core browsing remain successful; repeatable valid
bounded shutdown is still missing. Phase 1C is PARTIAL; no Phase 2 work has begun.

## Delivery

The supervisor milestone was pushed to main as `fc0024b` with matching remote SHA;
[Actions run 39608244177](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39608244177)
passed. Follow-up `58dfe99247664833868eb2dbae872c6eca3a81f1` was pushed with
matching remote SHA and [Actions run 39645049860](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39645049860)
passed. Final documentation commit/CI evidence accompanies delivery. Author
identity and history are preserved; no force-push.
Only repository tooling, tests and sanitized documentation/manifest changes are
committed. Chromium outputs, source checkout, dump contents and private profiles
are not included.

PHASE 1C-R5 PARTIAL — AWAITING ARCHITECT REVIEW
