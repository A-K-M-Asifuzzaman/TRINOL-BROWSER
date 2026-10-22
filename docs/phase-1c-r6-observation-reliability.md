# Phase 1C-R6 — observation reliability

Date: 2026-10-23 (Asia/Dhaka). Verdict: **PARTIAL**. Phase 1C remains partial;
Phase 2 is not authorized. One authorized blank trial ran at tooling commit
`2876c0a5aabd3399390ad62068cceba2db8782f3`. Its actual browser exit was 0,
but an unexpected second compiled-app instance invalidated the isolation gate.
The conditional browsing trial was NOT TESTED. No additional trial is authorized
by this result; the active failure marker remains in place.

## Environment and preserved build

Native Darwin arm64; Chromium 155.0.8059.85, source
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`, depot_tools
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`. Both tracked checkout status checks
were clean. The existing thin arm64 executable and bundle identity/version
passed verification. The historical full build exit 0, 39,487 actions and zero
failures remain valid; no compile, GN generation, source patch, signing change
or security bypass occurred. Existing GN arguments remain as recorded in the
[build report](phase-1c-build-report.md) and manifest.

Build root: `/Volumes/ssd(mac)2/TrinolBuild`. External writable APFS UUID:
`47F505A1-126A-4EC6-8DB6-135813AA6111`; physical backing capacity passed preflight.
No browser/build process was present initially. Pressure was initially 2, so no
launch occurred until the operator reduced workload and pressure returned to 1.
Fresh operator presence/unlocked confirmation and Finder accessibility succeeded.
Prelaunch swap was 4,398,514,176 bytes. Runtime pressure reached 2, not critical 4;
no 2 GiB swap growth occurred. Minimum sampled space was 269,725,716,480 bytes.
Final post-cleanup pressure was 2, swap 4,381,736,960 bytes, free space
269,733,818,368 bytes, expected UUID unchanged and compiled-app processes empty.

## R5 gap investigation

R5 records remain unchanged under `logs/phase1cr5-lifecycle-iuh2y3f4`.
The 36.952-second completed-sample gap crossed event emissions around elapsed
6.766 and 41.584 seconds, before the next observation at 43.719 seconds.
R5 had synchronous event open/append/close operations in this path. That is a
verified blocking exposure, not proof that one SSD operation caused the pause.
The later 40.532-second report overlapped the same stale observation interval;
it is not evidence of a separate pause. Missing samples do not prove continuous U.

Ten idle synthetic probe iterations on October 22 were retained in
`logs/phase1cr6-probes-6fnrpkp2/probe-results.json`. Maximum durations: diskutil
0.172924 s, resource guard 0.178167 s, full ps 0.025001 s, self libproc lookup
0.001489 s, serialization 0.000087 s, legacy open/append/close 0.004163 s.
No long gap reproduced at idle. Host scheduling, startup I/O and inline writes
remain possible R5 contributors; no single cause is established. The R6 trial
shows improved continuity in one run, not a controlled causal isolation of the
R5 defect or proof of permanent recovery. There is no basis to blame the SSD.

| R5 hypothesis, ranked by evidence | Support / limitation | Confidence and next discriminator |
| --- | --- | --- |
| Inline filesystem work or scheduling around event emissions | Gap lay between synchronous writes; R6 writer itself took up to 2.180 s; no R5 per-call timings | Moderate exposure, low causal confidence; retain operation timings in a separately authorized uncontaminated trial |
| Startup scheduling/I/O contention | Transient U observations and startup-only timing; no kernel trace | Plausible, unconfirmed; correlate sampled states with independent scheduling/I/O diagnostics if a gap recurs |
| Process enumeration, libproc or diskutil | All were synchronous; R6 maxima were below 0.185 s individually | Low evidence for the R5 pause; a recurrent gap should expose the slow operation or timeout |
| Serialization/nested probe overhead | Inline serialization exists; R6 maximum 0.001524 s | Low; use measured execution and cycle-start delay instead of attributing elapsed time to JSON |

OS scheduling delay is not separable from every measured wall-clock syscall
without a kernel trace. That trace was not taken; cycle start delay is measured,
not presented as proof of scheduler or disk causality.

## Instrumentation and writer

Monotonic records separate execution duration, scheduled-cycle start delay,
subprocess invocation/wait duration, incomplete/error/timeout outcomes, completed
sample intervals and direct-child poll gaps. Subprocess measurements include
launch and wait overhead; they are not CPU-time measurements. Full process
collection, each executable lookup, ownership, APFS/device, capacity, memory,
readiness, native Quit, event creation, serialization and transport are timed.

The observer uses nonblocking pipes and a bounded queue feeding one dedicated
Python writer process. Limits are 128 outstanding records, 64 KiB per record and
2 MiB outstanding serialized payload (plus bounded metadata and pipe overhead).
The writer keeps evidence files open, checks canonical paths/device before each
write, acknowledges ordered writes, then fsyncs and acknowledges final flush.
The parent retains current UUID/resource checks each diagnostic cycle. Queue
full, dropped records, writer errors, missing flush or timeout invalidate PASS.
A race between child exit and its pending flush acknowledgment has an offline
regression test. No daemon silently discards records and no kill signal is used.

Child polling is lightweight between two-second diagnostic cycles. The 15-second
failure threshold remains unchanged. The observer still measures its own gaps,
so offloading writes cannot conceal an observer stall. Library loading is cached;
live process identities are not indefinitely cached. Quit rechecks only the
specific PID/start/executable rather than repeating a full process scan.
Native registration, readiness and Boolean Quit semantics are preserved.

Writer finish waits at most five seconds in normal scheduling. A kernel-stalled
writer may remain and is reported; this is not a real-time OS termination
guarantee. Serialization and synchronous diagnostic probes can still block the
observer. The gap checks report missing time rather than inventing samples.

## R5 marker and one-use recovery

The exact validated R5 marker was archived byte-for-byte as
`logs/TrinolLifecycle.r5-reviewed.json`, SHA-256
`64d564e0812b88b8ed8f201a69e038f077600c1a3e461f6a34c41aaeafd6a4ef`.
Its referenced result had actual exit 0, observation_delayed, no watchdog/dump
and empty remaining processes. All six evidence hashes matched the prior audit.
The archive hard link and atomic guard replacement left no unguarded interval.
Recovery refuses changed markers, inconsistent results, existing compiled-app
processes or an already consumed archive. The R4 option is rejected.

The R4 archive is preserved with SHA-256
`c2c2c21b47a933abcf91fc90aaa3573f3863fa6bc642ed7302deea5f2807ad5c`.
New active R6 failure marker SHA-256:
`ccc213f095ea07c8dc20fa086a00d87ce4297645a29a5b82bafbd6debdea5655`.
Neither the original R6 result nor its marker was rewritten after cleanup.

## Actual blank trial

Command (executed once):

```sh
python3 scripts/test_chromium_lifecycle_macos.py \
  --build-root '/Volumes/ssd(mac)2/TrinolBuild' \
  --volume-uuid 47F505A1-126A-4EC6-8DB6-135813AA6111 \
  --seconds 45 --grace-seconds 30 --reviewed-r5-retry
```

Evidence: `logs/phase1cr6-lifecycle-6kd2mrf5` under the build root.
Profile: `test-profile-r6-96cf7hzc`, isolated Crashpad via supported
`BREAKPAD_DUMP_LOCATION`. Main PID 84236, start Fri Oct 23 01:27:52 2026.
Normal sandbox, GPU, TLS and OS protections retained.

| Event | Elapsed seconds |
| --- | ---: |
| Spawn recorded | 0.002 |
| PID/start/executable verified | 0.132 |
| Native application unregistered | 0.278 |
| Registered | 11.181 |
| Ready for native Quit | 13.610 |
| Quit requested | 46.101 |
| Quit accepted, first attempt | 46.267 |
| Actual browser exit 0 observed | 48.657 |
| Owned helpers absent | 50.674 |

29 completed process samples; maximum sample gap **2.423274 s**, maximum direct
poll gap **0.424384 s**. Transient U states ended; no persistent U was established.
Supervisor exit **1**, verdict **FAIL**, failure **unexpected_compiled_app_process**.
Owned browser exit **0** does not override this failure. No watchdog text or new
dump appeared in the isolated trial. This does not assess a different profile.

Writer: 78 submitted/78 acknowledged, zero dropped/unacknowledged, final flush
acknowledged in 0.001125 s, maximum queued payload 48,477 bytes, no writer error
or remaining writer. Longest writer operation 2.180408 s, maximum queue wait
1.925441 s. Observer continuity remained valid during those writer delays.

| Timed operation | Maximum seconds |
| --- | ---: |
| Direct child poll | 0.000127 |
| Resource guard | 0.241143 |
| APFS diskutil inspection | 0.184860 |
| Mount/device check | 0.000452 |
| Capacity | 0.000063 |
| Memory/swap | 0.065489 |
| Full process list | 0.115465 |
| Per-process executable path | 0.000778 |
| Ownership matching | 0.000874 |
| Native readiness | 0.145891 |
| Native Quit | 0.166284 |
| Event creation | 0.000001417 |
| Serialization | 0.001524 |
| Queue submission | 0.000008833 |
| Nonblocking transport | 0.001480 |
| Observation-cycle execution | 0.422951 |

Full timing data and summaries remain local in timings.jsonl and
latency-summary.json. No sensitive runtime logs, dumps or profiles are published.

## Unexpected second instance and cleanup

During startup the agent selected the exact app path with `cua.getApp` after a
process check. On macOS this API can launch an application when it does not
recognize an existing instance. The observed UI was “Sign in to Chromium”, not
verified about:blank content. A second main process PID 84954, PPID 1, start
01:28:03, used the same executable **without the disposable-profile arguments**.
Its appearance coincided with that app-selection call. The evidence strongly
supports GUI app selection starting it; no process-creation trace was captured.
This was an agent orchestration error and violated the one-instance requirement.
It is not evidence of a Chromium shutdown defect. One harness launch plus this
unexpected GUI launch occurred; there was no conditional browsing trial.

A later accessibility request timed out at ten seconds; the independent
supervisor continued and captured the test child exit. The initial harness
correctly failed on unexpected processes but recorded only owned processes in
samples and reported cleanup_required=false after their exit. This omitted the
unexpected identity and understated operator cleanup needs. A post-trial local
snapshot preserved the extra identity. The operator was promptly asked for
normal GUI Quit, reported the window closed, and a fresh full snapshot at
2026-10-22T19:30:01.679Z found no compiled-app processes. The second process was
not our Popen child: its exit status is **unknown**, not 0. No signal was sent;
no default-profile data was inspected, deleted or republished.

The subsequent small harness correction records unexpected PID/start/executable
and requires operator cleanup without adopting or terminating that process.
Its synthetic regression passes; it was not rerun natively. The existing result
stays FAIL. Future trials must not use app-selection APIs that can launch. Use
an operator for GUI verification or a separately verified existing-process-only
binding. Do not clear the R6 marker or reuse the R5 recovery option.

## Tests, functional classification and delivery

183 offline tests passed before launch; **184** passed after the unexpected-
process reporting correction (49 lifecycle tests, 22 evidence/latency tests,
113 other repository tests). Coverage includes timing, slow probes, writer
queue/failure/timeout/flush, observation gaps with exit 0, U-state gaps, refusal,
registration, interruption, deadlines, helper cleanup, process identity,
isolation, mount/memory safety, one-use recovery and unexpected-process cleanup.
Offline tests launched diagnostic Python writer children only, never Chromium.
Foundation validation, Python compileall, shell syntax and diff checks passed.

| Check | R6 result |
| --- | --- |
| Preserved native build/pins/version metadata | PASS |
| Normal prelaunch memory and expected APFS | PASS |
| Observation continuity and evidence flush | PASS in this run |
| Accepted native Quit, actual owned-child exit 0 | PASS |
| Owned helper cleanup / isolated watchdog and dump checks | PASS |
| Single-instance blank lifecycle | FAIL |
| Responsive blank GUI/content | NOT TESTED conclusively |
| Local HTML/CSS/JS, HTTPS, tabs, runtime version UI | NOT TESTED in R6 |
| Conditional browsing lifecycle | NOT TESTED; ineligible |
| Final absence of all compiled-app processes | PASS after operator cleanup |

Historical R3 functional passes and R3/R4 failures are preserved in prior reports.
The original R3 main-thread GPU DestroyCommandBuffer wait and possible earlier
network budget consumption remain unresolved. No source correction is justified.

Authenticated owner A-K-M-Asifuzzaman (138548302); author preserved as
Asif Zman <138548302+asif4762@users.noreply.github.com>. Main was fetched and
reviewed, with no unrelated changes. Tooling commit
`2876c0a5aabd3399390ad62068cceba2db8782f3` was pushed and matched remote HEAD;
[its CI passed](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39840186260).
Reporting correction `58ee36dad5144cef8737823bf3f521156cce98dd` was pushed;
[its CI passed](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39840786922).
This document is delivered as a focused commit; final exact hashes, remote HEAD and CI are in the accompanying final
response. Foundation CI is not a Chromium build or production certification.

## Next review gate

Before another separately authorized trial: review the exact active R6 marker,
verify a GUI observation route that cannot launch a second app, require fresh
operator presence and normal memory, and audit the reporting correction.
Two independent passing fresh-profile blank/browsing lifecycles are still needed.
No retry, rebuild, source patch, security bypass or Phase 2 work was performed
after the failure. Improved monitoring alone does not complete Phase 1C.

PHASE 1C-R6 PARTIAL — AWAITING ARCHITECT REVIEW
