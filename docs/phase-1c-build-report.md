# Phase 1C — native build and runtime evidence

Current Phase 1C-R5 verdict: **PARTIAL — actual native exit 0 captured, but
bounded supervision acceptance failed**. The one approved blank-session retry
accepted native Quit, reaped browser exit 0 and verified helper cleanup within
49.69 seconds, without a watchdog or dump. A 36.95-second startup observation gap
invalidated the lifecycle trial, so no browsing session or repetition followed.
See the [R5 lifecycle report](phase-1c-r5-lifecycle-validation.md). The R4 marker
is archived byte-for-byte, and the new R5 failure marker remains active. Phase 2
is gated. Earlier phase checkpoints are preserved below.

The following earlier history is preserved: Phase 1C was **PARTIAL — memory-blocked**
on 2026-10-19. GN generation passed, and the missing Metal compiler was installed
and its failing action recovered. The two-job attempt completed 16,212 steps
before the resource guard interrupted it. At that checkpoint the full browser
target was incomplete and no application launch or browser functionality was claimed.

## Readiness and source identity

Observed 2026-10-18 on the actual local Mac: macOS 26.6.2 (25G83), M3 Pro arm64,
11 cores, 18 GiB RAM. Active developer directory is the installed Xcode's
`Contents/Developer`; Xcode 26.5 (17F42), SDK 26.5 (25F70). First-launch checks pass.
Chromium's compiler is Clang 24.0.0git, not the host Apple Clang reported by the
general audit. GN is 2562 (cfcd774b98f3), Ninja 1.12.1 and provisioned Siso 1.6.1.

Source version is 155.0.8059.85 at
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`; depot_tools remains
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`. The existing checkout verifier passes:
HEADs, origins, local tag, version, DEPS digest and tracked cleanliness match.
Phase 1B's successful dependency/hook records are retained. No new checkout,
source upgrade, patch or overlay was introduced.

Physical storage was freshly verified through the existing MacProbe/capacity
helpers: writable APFS disk7s2 at `/Volumes/ssd(mac)2`, container backed by disk6s2
on the external X900 Plus USB SSD. Initial available physical capacity was
**283,204,104,192 bytes (263.75 GiB)**. This is container/available capacity, not
purgeable storage or a logical image size. Product Git remains in its HFS+ workspace.
Output, cache and profile paths were absent before this phase.

The host already reported memory pressure level 2 (warning) and approximately
14.7 GiB swap before building. That is measured pre-existing host state, not
attributed entirely to Chromium. Internal free storage was about 62 GiB.

## Configuration and GN generation

The unchanged six-argument template was copied to `out/TrinolDev/args.gn`:

```gn
target_os = "mac"
target_cpu = "arm64"
is_debug = false
is_component_build = true
symbol_level = 1
is_official_build = false
```

`gn gen out/TrinolDev` exited 0 and reported **35,953 targets from 4,999 files in
23,632 ms**. `gn args ... --list --json` verified those values and these defaults:
`host_os="mac"`, `host_cpu="arm64"`, `use_siso=true`, `use_lld=true`,
`use_remoteexec=false`. `gn desc ... //chrome:chrome --format=json` resolves the
browser group with toolchain `//build/toolchain/mac:clang_arm64`.
No change to the reviewed arguments was necessary.

Machine-specific evidence directory (not active product configuration):
`/Volumes/ssd(mac)2/TrinolBuild/logs/phase1c-gn-01talp4q`.
It contains the actual command output, resource samples, status, effective GN
arguments and browser-target description.

## Build execution and resource protection

The tested [build runner](../scripts/build_chromium_macos.py) reuses the existing
checkout verifier and native storage inspection. It accepts an explicit build
root, quotes paths through subprocess argument arrays, uses session-local tools
and external caches/temp files, and preserves existing arguments and outputs.
It never downloads a replacement browser, cleans the output or resets source.

The first actual invocation was:

```text
autoninja -C out/TrinolDev -j 4 -cache_dir=/Volumes/ssd(mac)2/TrinolBuild/siso-cache chrome
```

This is an argument-list rendering, not an unquoted shell command to paste.
Autoninja printed its actual executor:
`siso ninja --offline -C out/TrinolDev -local_jobs=4` with the external cache flag.
The pinned help supports `-cache_dir`; the wrapper maps Ninja-style `-j` into
Siso's `-local_jobs`. Remote execution remains disabled by effective GN and the
observed `--offline` invocation.

The resource guard requests a sample every five seconds. Native probes/I/O can
add latency; actual first-attempt intervals reached roughly 37 seconds during
graph scheduling. Detailed timestamps are preserved, rather than claiming a
hard real-time sampling guarantee. It checks mount/device identity, accessible
space, host pressure level, swap growth and internal swap headroom. It interrupts
only its own process group, then escalates termination if needed to preserve safety.

Policy: stop at or below 60 GiB external free (buffer above the 50 GiB floor),
10 GiB internal free, critical pressure, or 4 GiB additional swap. At four jobs,
60 seconds of warning pressure requests a two-job retry. At two jobs, warning
pressure lasting 180 seconds plus a current swap increase of at least 2 GiB
stops the attempt; the swap increase itself need not last 180 seconds.
Old swap alone is not treated as evidence of new build-induced exhaustion.

The first attempt stopped for sustained warning pressure during Siso graph
scheduling, before any compiler task completed. The runner returned 75 (reduce
jobs); Siso returned 1 after the intentional interrupt, reporting 0 done and
0 failed compilation tasks. This is a controlled stop, not a compiler failure.
External free space was about 262.03 GiB. Its evidence directory is
`/Volumes/ssd(mac)2/TrinolBuild/logs/phase1c-build-07ejtz1n`.
The two-job attempt in `logs/phase1c-build-ho3zo349` exited 1 after 16m54.81s,
reporting **1,051 done, one failed and 76,403 remaining**. The earliest actionable
failure was ANGLE's `angle_metal_internal_shaders_to_air`: Xcode reported that
its Metal Toolchain was missing. This was a toolchain component failure, not an
observed C++ compiler, SDK-version, linker or disk-capacity failure. The last
sample recorded 280,174,493,696 available external bytes (260.93 GiB), warning
pressure 2 and about 15.81 GiB total host swap.

On 2026-10-19, the supported Apple command installed the matching component:

```bash
xcodebuild -downloadComponent MetalToolchain -exportPath "$BUILD_ROOT/metal-toolchain"
```

The installer exited 0, downloaded 687.9 MB and exported
`MetalToolchain-17F42.exportedBundle` on the approved external volume. Apple's
installer manages the installed asset under `/System/Library/AssetsV2`; this is
not a relocated Chromium cache or a change to the active Xcode selection.
`xcodebuild -showComponent MetalToolchain -json` reports installed build 17F42;
`xcrun metal --version` reports Apple Metal 32023.883. See
[Apple's component installation documentation](https://developer.apple.com/documentation/xcode/downloading-and-installing-additional-xcode-components).
The installation log is `logs/phase1c-metal-install.log`.

A third attempt resumed the same incremental output with **two local jobs**,
unchanged GN arguments and the same executor/cache. Evidence:
`logs/phase1c-build-4n1txr2_`. Starting external free space was
278,934,351,872 bytes (259.78 GiB); baseline pressure remained 2 with approximately
11.98 GiB swap. The previously failing ANGLE shader action completed at
5m40.67s in this retry, verifying that the component installation resolved the
original failure. C++/Rust compilation and generated resources then progressed.

At **2026-10-19 08:37:08 UTC (14:37:08 Asia/Dhaka)** the guard interrupted this
attempt for sustained warning pressure with swap growth above 2 GiB. Siso's final
result was **1h48m37.25s, 16,212 done, zero failed, 53,054 remaining**, followed by
`interrupt by signal`. Runner and Siso both exited 1. This was a resource safety
stop, not a reported compiler failure. The attempt used local execution only:
16,192 local steps, 20 no-exec steps, zero remote steps and zero cache hits.

The 1,105 resource samples recorded pressure levels 1 and 2, with no observed
critical level 4. Swap rose from 12,864,653,885 to 15,143,408,762 bytes: **2.12 GiB
additional swap**, total **14.10 GiB** at the stop. Warning pressure was sustained;
the final swap increase occurred shortly before the guard stopped the process.
Sampling intervals reached **44 seconds**, so the five-second request is not a
hard real-time guarantee. No volume replacement or storage-floor stop occurred.

A fresh check at approximately **11:49 UTC (17:49 Asia/Dhaka)** still showed
warning pressure 2 and **13.34 GiB total host swap**. No build/Siso/compiler process
remained in the process check. The build was not blindly restarted under the
continuing pressure. Close unnecessary memory-heavy applications or otherwise
free host memory, then recheck pressure/headroom before resuming at two jobs.
No unrelated user process was terminated and no system memory setting changed.

## Storage consumption and preserved output

The final external available space was **274,637,193,216 bytes (255.78 GiB)**,
about **7.98 GiB lower** than the initial Phase 1C snapshot. This is the observed
volume-wide change, not an attribution of every byte to the build. The third
attempt's available-space change was about 4.02 GiB. The mandatory 50 GiB floor
was maintained with substantial headroom.

`du -sk` reported **5,233,176 KiB (4.99 GiB allocated)** for `out/TrinolDev` and
zero allocated KiB for the external Siso cache. This is allocated disk usage,
not the sum of logical file sizes; cache configuration does not guarantee cache
hits or populated content. Outputs, source checkout and all attempt logs remain
preserved. No cleanup, executor switch, source modification or GN-argument change
was performed. The final checkout verifier again passed both pinned HEADs, tag,
version, DEPS digest and tracked cleanliness.

## Artifact and launch checks

The directory `out/TrinolDev/Chromium.app` exists, but the expected executable
`Chromium.app/Contents/MacOS/Chromium` **does not exist**. This is an incomplete
bundle. Architecture, executable permissions, complete bundle metadata, linked
libraries, runtime version and signing verification are **NOT TESTED** because
there is no completed executable. `file`, `lipo`, `otool` and `codesign` checks on
an absent browser would not establish artifact validity.

Native launch and GUI checks were not attempted. `test-profile` does not exist;
no personal Chrome profile was accessed. No browser crash result can be reported
because no browser was launched. GUI tooling availability was not used as the
blocker: compilation itself remains incomplete.

## Functional matrix

| Feature | Result | Evidence |
| --- | --- | --- |
| Native launch and chrome://version | NOT TESTED | Awaiting completed build |
| HTTPS navigation and HTML rendering | NOT TESTED | Awaiting completed build |
| JavaScript execution | NOT TESTED | Awaiting completed build |
| Back, forward and refresh | NOT TESTED | Awaiting completed build |
| New/multiple tabs, close and reopen | NOT TESTED | Awaiting completed build |
| Second window | NOT TESTED | Awaiting completed build |
| Incognito and private-state separation | NOT TESTED | Awaiting completed build |
| Bookmark creation and use | NOT TESTED | Awaiting completed build |
| History | NOT TESTED | Awaiting completed build |
| Small download and downloads interface | NOT TESTED | Awaiting completed build |
| Settings | NOT TESTED | Awaiting completed build |
| Local PDF | NOT TESTED | Awaiting completed build |
| Print preview without printing | NOT TESTED | Awaiting completed build |
| Standard site permission prompt | NOT TESTED | Awaiting completed build |
| Extensions management | NOT TESTED | Awaiting completed build |
| Session restoration | NOT TESTED | Awaiting completed build |
| HTTPS security indicator and sandbox status | NOT TESTED | Awaiting completed build |

## Reproduction

Use the [upstream workflow](upstream-workflow.md) and the existing pinned checkout.
Set `BUILD_ROOT` to the approved external build root, then from product Git:

```bash
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --generate
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --jobs 4
# After a four-job pressure stop, preserve output and resume with:
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --jobs 2
```

The generation command preserves an existing matching args.gn and refuses an
unexpected configuration. The build command requires generated files, inspects
effective GN arguments and verifies the browser target before compiling.
Each attempt writes a unique directory beneath external `logs/`, with command
output, resource samples, status and argument/target evidence. Do not rerun a
second build while an attempt remains active. After a two-job memory stop, first
relieve host memory pressure and recheck capacity; do not repeatedly restart to
reset the swap baseline. Symbol level remains 1 because the evidence does not
establish symbol generation as the cause. The native linker/executor was not
changed because no linker or Siso incompatibility was demonstrated.

## Repository checks and phase gate

The offline repository suite currently has **94 passing tests**, including
resource thresholds, mount changes, safe process-group interruption, path
containment, failed child status, GN remote/executor rejection and Phase 1C
completion gates. Foundation validation, Python compilation, shell syntax and
whitespace checks pass. CI remains repository tooling only, not a Chromium build.

The manifest records successful GN generation separately from compilation and
runtime evidence. Phase 1C cannot be marked complete on compilation alone.
Remaining checks include final build exit, application inspection, native launch
and the feasible functional matrix above. Proprietary services, personal
accounts, saved passwords, distribution signing/notarization and Trinol branding
are outside this baseline. Phase 2 requires a verified baseline and explicit
architect approval; it is not started.

## GitHub tooling milestone

`2a8bc15c17a9ce7ab30ecaaabb081fcce7898d8f` —
`build: add guarded native Chromium build runner` was pushed normally to `main`.
Authenticated owner was verified as `A-K-M-Asifuzzaman`; existing author
`Asif Zman <138548302+asif4762@users.noreply.github.com>` was preserved.
`git fetch origin main` showed 0/0 divergence before committing;
`git ls-remote origin refs/heads/main` matched the delivered SHA afterward.
[Foundation Actions run 39212004908](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39212004908)
completed successfully. This CI checks repository tooling, not the native browser.

The documentation/recovery milestone is
`74f4d0c29562edbd7df592a2c09ccbec6cfc9a6a` —
`docs: record Phase 1C GN and Metal toolchain recovery`.
Remote `main` matched this commit and
[Actions run 39212323138](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39212323138)
passed. The final partial-result update is a subsequent normal commit; its exact
SHA, remote verification and Actions result are reported in the delivery response.

## Product repository changes

- Added `scripts/build_chromium_macos.py` and `tests/test_build_chromium_macos.py`.
- Updated `scripts/verify_upstream_checkout.py` and its test file with Phase 1C
  completion gates; incomplete build/runtime evidence cannot mark Phase 1C complete.
- Updated `AGENTS.md` and `.github/workflows/foundation.yml` for authorized scope
  and repository-tooling checks without attempting Chromium compilation in CI.
- Updated `README.md`, `docs/roadmap.md`, `docs/upstream-workflow.md` and
  `upstream/manifest.json`; added this report.
- No source checkout, executable, object, cache, profile, local log, credential or
  signing material was staged. Staged file-type/known-credential-pattern scans
  complement manual diff review; they are not an exhaustive secret detector.

## Final verdict and Phase 2 prerequisites

**PARTIAL.** The native build is recoverable and the Metal issue is resolved,
but sustained host memory pressure stopped the two-job attempt. The 18 GiB host,
pre-existing swap usage and slow external file I/O remain practical constraints.
The resource guard is sampled and cannot guarantee instant response during I/O
stalls. No Chromium feature compatibility, production performance, distribution
signing or browser security runtime result is inferred from repository CI.

Phase 2 is **not ready**. Relieve host pressure, resume the preserved two-job
build, obtain a successful full `chrome` exit, verify the actual arm64 bundle,
launch with the dedicated profile, and complete the feasible functional matrix.
Then obtain architect review and explicit Phase 2 authorization.

PHASE 1C PARTIAL/BLOCKED — AWAITING ARCHITECT REVIEW


## Phase 1C-R recovery — 2026-10-19

Recovery status: **IN PROGRESS; Phase 1C remains PARTIAL**. Earlier attempts and
verdicts above are retained as history. The recovery request explicitly authorizes
one local job, guard improvements and incremental continuation without GN regeneration.

### Host diagnosis before recovery

Native Darwin arm64, macOS 26.6.2 (25G83), 18 GiB RAM and 11 CPUs were reverified.
At 12:22:51 and 12:24:12 UTC, with no compiler/Siso running, pressure was normal
(level 1). Swap remained exactly 13,131.44 MiB used out of 14,336 MiB allocated
(about 12.82 GiB used). Over those 81 seconds, swap-out counters did not increase;
pageouts increased by 273 pages, while compressed-memory occupancy decreased.
The machine still had unrelated applications running, so this was a no-build
observation rather than a claim that the whole host was idle.

The first `top` sample reported 44.31% CPU idle, 6.14% user and 49.54% system.
`vm_stat` reported approximately 5.13 GiB compressed-memory occupancy in the first
saved snapshot, decreasing by about 0.33 GiB in the second. These are point-in-time
host readings, not memory attributed to Chromium. External available space was
274,689,495,040 bytes (255.82 GiB); internal available space was about 62.18 GiB.
The 12:28:14 UTC prelaunch check again showed normal pressure and unchanged swap.

Largest application groups by summed `ps` RSS were Brave Browser (~2.36 GiB),
ChatGPT (~1.96 GiB), and Cursor (~1.01 GiB). Shared pages may be counted more than
once, so these are not precise physical footprints. Closing unused windows in
those applications may help; none was closed or terminated. No restart or system
memory change was needed for this observed recovery decision. Normal pressure,
unchanged swap and adequate disk headroom supported a tightly guarded one-job
attempt. High accumulated swap alone was not treated as exhaustion. Apple's
[memory reporting guidance](https://support.apple.com/en-lamr/guide/activity-monitor/actmntr1004/mac)
also distinguishes pressure from the amount of swap in use.

Sanitized local evidence: `logs/phase1cr-preflight-fpqndvnb/idle-first.json`,
`idle-second.json`, and `starting-state.json`. The starting state records unchanged
`args.gn` SHA-256 `cabeadd749736e664c312aca9303a57edd103c34fcc39d66d782128c4f44c1ab`
and existing `build.ninja` metadata, alongside the prior attempt's 16,212 done /
53,054 remaining. Those earlier counters are not added to a new attempt's counter
or treated as a permanent percentage.

### Guard correction and verification

The earlier guard correctly protected the host conservatively, but its stop did
not establish sustained new swap growth: the final ten seconds added about
1.12 GiB and immediately inherited an already-old warning timer. The recovery
policy times the combination of pressure and new growth, with small hysteresis.
The exact policy and exit meanings are in the
[recovery operating instructions](upstream-workflow.md#phase-1c-r-recovery).

The runner accepts 1, 2 and 4 jobs. It retains the critical-pressure stop, 4 GiB
new-swap cap, 60 GiB external stop floor, 10 GiB internal floor, mount checks,
owned-process-group termination and unchanged source/GN validation. At one or
two jobs, warning pressure plus 2 GiB new swap starts a 180-second timer; normal
pressure or growth below 1.5 GiB resets it. Four-job warning reduction remains.
An advisory lock prevents concurrent runner invocations against this output.
The live lock check rejected a second acquisition while the one-job build ran;
no second compiler was launched. The lock file is retained safely after release.

Samples now record actual intervals, pressure/swap growth, CPU observations and
bounded log-tail progress. Delays above 60 seconds stop conservatively when the
monitor regains control; blocking I/O can still delay response. Controlled stops,
monitor errors, user interruptions and command failures are distinguished while
retaining the actual child exit. No numeric hard resource threshold was raised.

**112 offline tests passed** (94 existing plus 18 added), including argument modes,
transient recovery, sustained deterioration, hysteresis, duplicate locking,
lock release/symlink protection, CPU/progress parsing, monitor delays/errors,
disconnection during an active child, controlled/successful exits, termination
escalation and preservation of existing output without GN regeneration.
Foundation validation, Python compilation, shell syntax, diff checks and staged
credential-pattern/file-type scanning passed.

### Recovery invocation and delivery

```bash
python3 scripts/build_chromium_macos.py --build-root '/Volumes/ssd(mac)2/TrinolBuild' --jobs 1
```

Fresh source/tool verification passed. GN values remained unchanged. No GN
regeneration was requested. Actual executor: Siso offline with `-local_jobs=1`
and the existing external `siso-cache`. Evidence: `logs/phase1c-build-dbqart3q`.
The attempt has begun actual native compilation; final exit and runtime results
are still pending. The full browser target, not a substitute, is being built.

`9ef87587af9cd6b828dad5dbd2baf67deb5cf05c` —
`fix(build): support guarded single-job Chromium recovery` was pushed normally
to `main`; remote HEAD matched. Authenticated owner and configured author were
verified and preserved. [Actions run 39252295892](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39252295892)
passed for this exact commit. Phase 2 has not started.


### Recovery checkpoint — 22:55 Asia/Dhaka, 2026-10-19

The same single-job attempt remained active after about 4h26m, with approximately
11,445 completed actions and 37,112 remaining in that attempt's current graph.
These are not cumulative project percentages. Inspection through 16:55:46 UTC
found no `FAILED:` action markers and no `warning:` diagnostic lines in the log;
there is still no final exit code or completed-browser claim.

Across 3,120 samples, pressure levels were 1 and 2, maximum new swap growth was
1.245 GiB, minimum external available space was 251.89 GiB, minimum internal
available space was 60.98 GiB, and the longest observed sampling interval was
41.20 seconds. The sustained-deterioration timer never started because new swap
stayed below 2 GiB. This supports continuing the same guarded attempt without
restarting or changing the GN configuration.

A process-tree inspection showed that Siso's compiler workers use separate
process groups. Therefore `process_group_cpu_percent` measures the runner/Siso
group and can omit compiler-worker CPU; it is not total build CPU utilization.
Host load and the separate process-tree snapshot provide additional activity
observations. Pressure and swap monitoring remain host-wide and unaffected by
that telemetry limitation.

The recovery diagnosis milestone was
`74a0bea5d9b9b3e438b8ef1efbac6a6047133df2` —
`docs: record single-job recovery diagnosis and baseline`.
Remote main matched and [Actions run 39252726092](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39252726092)
passed. The initial build/launch matrix remains NOT TESTED while compilation runs.

### Recovery checkpoint — 03:56 Asia/Dhaka, 2026-10-20

The same one-job Siso attempt remained running at 21:56:40 UTC on October 19,
after about 9h28m. Its current graph reported 16,082 completed actions and 32,244
remaining. Inspection of the command log found zero `FAILED:` action markers
and zero `warning:` diagnostic lines. These are observations of an unfinished
attempt, not a successful final exit or cumulative project percentages.

Across 6,702 resource samples, pressure levels were 1 and 2, maximum new swap
growth remained 1.245 GiB, and the longest sampling interval remained 41.20
seconds. The sustained-deterioration timer remained zero. At the checkpoint,
pressure was 2 and swap growth was 0.699 GiB; free space was 251.05 GiB external
and 63.59 GiB internal. Minimum available space over this attempt was 251.05 GiB
external and 60.98 GiB internal. Compilation continues under the existing guard;
the source, output directory, GN arguments and concurrency have not changed.

The earlier progress checkpoint was delivered in
`d34fdd963bbbdf3c88befdbe091d650c0643d041` —
`docs: record sustained single-job build progress`.
Remote main matched and [Actions run 39289887406](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39289887406)
passed. Compilation, native launch and functional smoke-test completion remain
unverified; Phase 1C remains PARTIAL and Phase 2 has not started.

### Recovery checkpoint — 12:56 Asia/Dhaka, 2026-10-20

The original one-job recovery attempt continued through the night. At
06:56:59 UTC, after about 18h28m, Siso reported 31,658 completed actions and
10,021 remaining. Its scheduled graph had changed to 41,679 actions; these
counts are not a permanent total-project progress percentage. The full command
log still contained zero `FAILED:` action markers and zero `warning:` diagnostic
lines. There is no final exit code yet.

Across 13,097 resource samples, observed pressure levels remained 1 and 2, peak
new swap remained 1.245 GiB, the longest interval remained 41.20 seconds, and the
sustained-deterioration timer never started. At this checkpoint, pressure was 2,
new swap was 0.880 GiB, and available space was 248.18 GiB external and 63.55 GiB
internal. Minimum space during the attempt was 248.18 GiB external and 60.98 GiB
internal. The same guard continues to permit compilation.

Chromium and depot_tools HEADs still match their pinned revisions. The `args.gn`
SHA-256 and `build.ninja` size/modification time still match the pre-recovery
records. The original process remains active, with no second build, GN
regeneration or configuration change. An earlier process-tree snapshot at about
22:02 UTC on October 19 observed one `clang++` worker at 88.3% CPU, confirming
compiler activity beyond the limited process-group metric described above.

The preceding checkpoint was delivered as
`64bcdcf3056a2687b0e3a62f0a06a9d5efcf103b` —
`docs: record nine-hour Chromium recovery checkpoint`.
Remote main matched and [Actions run 39331479613](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39331479613)
passed. Browser artifact, native launch and functional verification remain
pending full target completion. Phase 1C remains PARTIAL; Phase 2 is not ready.

## Phase 1C-R result — compilation complete, runtime blocked — 2026-10-20

**Verdict: PARTIAL.** The primary incremental compilation objective succeeded.
The unchanged `chrome` target exited **0** after **23h51m20.23s**, with Siso's
final summary reporting **39,487 completed steps**. There were no failed-action
markers or compiler-warning lines in the build log. Local execution remained
one job, remote execution remained zero, and all previously compiled output was
preserved. No GN regeneration, source change, executor switch or second build
was needed. The executable is now present, but responsive native launch and
functional verification are blocked as detailed below.

### Final build and resource evidence

The command remained:

```bash
python3 scripts/build_chromium_macos.py --build-root '/Volumes/ssd(mac)2/TrinolBuild' --jobs 1
```

The runner and child both returned 0. The log ends with `Build Succeeded: 39487
steps - 0.46/s`. Its executor statistics report `noexec:632 local:38855 remote:0
cache:0 skip:47494`; these categories are not added to prior attempts as a
permanent project percentage. Siso also reports filesystem-operation errors in
its internal statistics (`fs ops ... err:107145`), but read/write error counts
are zero and the executor's final outcome is success. This is disclosed without
treating internal operation counters as failed compilation actions.

Across **16,911** samples, pressure levels were 1 and 2, with no observed critical
level 4. Peak new swap was **1.388 GiB**; the final sample was **1.015 GiB** above
the 12.82 GiB starting baseline. The deterioration timer stayed zero. Minimum
available space during compilation was **247.03 GiB external** and **60.98 GiB
internal**; the longest sampling interval was **41.20 seconds**. Monitoring was
sampled, not real-time. Later runtime diagnostics observed about 238.60 GiB
external and 69.17 GiB internal free; these later host readings are not attributed
solely to the build. `du -sk` reported 13,501,524 KiB (12.88 GiB) allocated to
`out/TrinolDev` and 534,808 KiB to the disposable profile tree.

The original runner status retained stale live counters (four remaining) even
though its exit/outcome correctly recorded success. The observed Siso success
format differs from its failure summary. The parser now recognizes the actual
success line, reports 39,487 completed / zero failed / zero remaining, and drops
the obsolete scheduled-graph total. A regression test reproduces the exact log
shape. **113 offline tests pass**, including all resource safeguards. Original
logs/status remain untouched; a separately parsed final summary is preserved.

Build evidence remains `logs/phase1c-build-dbqart3q`. Runtime and corrected
summary evidence is `logs/phase1c-runtime-v5u4akhv`, including
`build-final-summary.json`, `artifact-checks.json`, `launch.json`, `browser.log`,
`version.stderr.log`, `runtime-result.json`, and `cleanup.json`. These local
artifacts, profiles and binaries are not committed to the product repository.

### Artifact inspection and actual launch attempt

- `Chromium.app/Contents/MacOS/Chromium` exists, is executable, and is a 35,008-byte
  Mach-O arm64 launcher. The component framework/libraries are separate outputs.
- `file` and `lipo -archs` confirm native arm64. `plutil -lint` passes.
- Bundle identifier is `org.chromium.Chromium`, short version is
  **155.0.8059.85**, bundle version is `8059.85`, minimum macOS is 13.0.
- `otool -L` records the Chromium framework, `libc++_chrome.dylib`, and system
  library dependencies. Runtime logs demonstrate component-library loading, but
  complete runtime dependency/behavior verification is not claimed.
- `codesign -dv` reports **ad hoc, linker-signed**, with no team identifier or
  sealed resources. `codesign --verify --deep --strict` exits 1: “code has no
  resources but signature indicates they must be present.” No signing,
  quarantine removal, sandbox bypass or notarization claim was added.

The actual compiled executable was launched as PID 30458 with:

```text
--user-data-dir=/Volumes/ssd(mac)2/TrinolBuild/test-profile
--no-first-run --no-default-browser-check chrome://version
```

Process inspection confirmed the exact compiled executable and renderer/helper
paths. This proves process creation, not a responsive browser window. Computer
Use full-path app inspection returned `timeoutReached` (-10005), including a
bounded retry. Bundle-ID lookup was ambiguous with an unrelated installed
Chromium; that other application was not selected or used.

A separate CLI smoke attempt used the same binary, `--headless --dump-dom
--timeout=15000 --allow-chrome-scheme-url chrome://version`, and the isolated
`test-profile/headless-smoke` subprofile. It produced zero DOM bytes and exceeded
a 45-second process deadline. SIGTERM then SIGKILL were sent only to that owned
test group; exit waits also timed out, but PID 45076 was absent on subsequent
inspection. The planned HTML/JavaScript and HTTPS checks did not execute after
this first test aborted. No sandbox or TLS protection was disabled.

Both runtime logs report duplicate Objective-C implementations of
`ANGLESwapCGLLayer` and `CrashpadHTTPBodyStreamTransport`, a quarantine-attribute
error, and a signing-clone `Cross-device link (18)` error when cloning from the
external build volume to macOS's internal translocation directory. These are
observed diagnostics, not an established root cause of the hang. Inspection of
the pinned clone code shows an error-return path; no workaround was applied.

The GUI browser and three helpers were later observed in `UE` state. The local
macOS `ps(1)` manual defines `U` as uninterruptible wait and `E` as trying to
exit. A bounded `sample` attempt returned -10 without creating a sample file.
SIGTERM to the verified test-browser group removed its renderers, but the
uninterruptible processes remained. Clean shutdown is therefore unverified.
Only task-owned test processes were signalled; no unrelated apps were closed.

### Recovery functional matrix

| Check | Result | Evidence |
| --- | --- | --- |
| Full native `chrome` compilation | PASS | Child and runner exit 0; Siso success summary |
| arm64 executable and bundle metadata | PASS | `file`, `lipo`, `plutil`; pinned version metadata |
| Native process creation with dedicated profile | PASS | PID 30458 and exact build/profile paths |
| Responsive GUI startup | FAIL / blocked | Computer Use timeout; browser later in `UE` state |
| `chrome://version` runtime page | FAIL / timeout | Headless deadline; zero DOM bytes |
| Clean shutdown | NOT VERIFIED | SIGTERM left uninterruptible test processes |
| HTTPS navigation / HTML rendering | NOT TESTED | Smoke sequence stopped at version timeout |
| JavaScript execution | NOT TESTED | Fixture prepared but browser check did not execute |
| Multiple tabs / second window / back / forward / refresh | NOT TESTED | Responsive GUI unavailable |
| Private browsing / private-state separation | NOT TESTED | Responsive GUI unavailable |
| Bookmarks / history | NOT TESTED | Responsive GUI unavailable |
| Test download / downloads interface | NOT TESTED | Responsive GUI unavailable |
| Settings / extensions management | NOT TESTED | Responsive GUI unavailable |
| Local PDF / print preview | NOT TESTED | Responsive GUI unavailable |
| Site permission prompts | NOT TESTED | Responsive GUI unavailable |
| Session restore | NOT TESTED | Clean shutdown and responsive GUI unavailable |
| HTTPS security indicators / sandbox status | NOT TESTED | Protections retained; runtime status not verified |
| Distribution bundle signature | FAIL | Strict verification exits 1; ad hoc development signing |

### Next boundary and delivery

No build restart is needed: preserve the successful output. Save open work and
perform a normal **user-controlled macOS restart** before another runtime
attempt if these uninterruptible processes remain. No restart is executed by
this task. Then recheck host/storage health and investigate the runtime/signing
diagnostics without weakening protections or changing upstream source blindly.
Repeat dedicated-profile native launch and feasible functional checks after
the host/process blocker is cleared.

Phase 1C remains PARTIAL and Phase 2 is **not ready**. The manifest records
compilation separately from responsive launch and smoke-test completion. No
Trinol branding, UI customization, AI feature or Phase 2 work was started.

The preceding checkpoint commit was
`4bcd502846a29632341074411f5cd68510f92f1f`, with remote main matched and
[Actions run 39383518583](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39383518583)
passing. The success-summary parser fix is
`9857171ef7d2a7739f221ee0308540e9464bb531`, with remote main matched and
[Actions run 39463750154](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39463750154)
passing. Final documentation delivery verification accompanies this report.
Repository CI is not evidence that browser runtime checks passed.

PHASE 1C RECOVERY PARTIAL/BLOCKED — AWAITING ARCHITECT REVIEW

## Phase 1C-R2 — host recovery gate blocked — 2026-10-21 Asia/Dhaka

**BLOCKED at the mandatory host recovery gate; Phase 1C remains PARTIAL.**
The R2 instruction says to stop if uninterruptible Chromium processes remain.
No new browser instance, executable version command, GUI inspection, headless
test, process signal, rebuild or signing change was attempted. The successful
39,487-step compilation and all previous runtime evidence remain preserved.
Only this report and the manifest's new R2 checkpoint are changed.

### Host and process evidence

At **2026-10-20 18:08:19 UTC / 2026-10-21 00:08:19 Asia/Dhaka**, uptime was
28 days, 46 minutes. Boot time is Unix `1790097734`, September 22 at 23:22:14
Asia/Dhaka, before the failed October 20 runtime test. The Mac has not restarted.

| PID | Start time (Asia/Dhaka, October 20) | State | Verified identity |
| --- | --- | --- | --- |
| 30458 | 18:22:33 | UEs | Built Chromium executable, original external test-profile, PGID 30458 |
| 32662 | 18:23:57 | UE | Built Aperitif helper, GPU process, same profile and group |
| 32663 | 18:23:57 | UE | Built Aperitif helper, network service, same profile and group |
| 32670 | 18:23:57 | UE | Built Aperitif helper, storage service, same profile and group |

All four executable paths resolve in the command lines to the original
`/Volumes/ssd(mac)2/TrinolBuild/chromium/src/out/TrinolDev/Chromium.app` tree.
PID, full command line, start time, parent and process group were inspected
together; this is not a PID-only match. Browser start time matches `launch.json`.
The earlier `cleanup.json` records these same four stuck processes after SIGTERM.
`U` means uninterruptible wait and `E` means trying to exit in the local `ps(1)`
manual. The unresolved host/process condition is **CONFIRMED**; its underlying
kernel or application cause is not established.

Crashpad PIDs 32638 and 32640 also remain, both starting at 18:23:56 from this
build's framework. PID 32638 was running at 91.5–96.1% CPU across two snapshots;
32640 was sleeping at 0%. Their command lines specify the default user-library
Chromium Crashpad database, not the disposable browser profile. No database
contents were inspected and neither process was signalled. Future test isolation
must account for Crashpad's database separately from `--user-data-dir`.

Memory pressure is **2 (warning)**; swap used is **8,744.69 MiB (8.54 GiB)**.
Available storage is **246.48 GiB external** and **72.89 GiB internal**.
The mount is case-sensitive APFS at `/Volumes/ssd(mac)2`, volume UUID
`47F505A1-126A-4EC6-8DB6-135813AA6111`, currently `disk10s2` in container
`disk10`, physical store `disk6s2`. Earlier preflight recorded `disk7s2` with the
same physical-store identifier, but no UUID. Therefore uninterrupted mount
identity is not proven; device-number changes alone do not establish replacement
or the cause of the hang. Revalidate identity after restart.

Shell probes and evidence reads returned promptly. WindowServer PID 454 has
remained running since September 22; observed CPU was 8.2–22.2%. These snapshots
do not prove GUI responsiveness or rule out GPU/WindowServer/filesystem faults.
Deeper system-log, crash-report and main-thread diagnostics were deferred at the
explicit stop gate. No Siso/compiler process was observed in the process snapshot.

Fresh evidence is outside product Git:
`/Volumes/ssd(mac)2/TrinolBuild/logs/phase1cr2-host-qy8pb5u3/host-check.json`
and `mount-check.json`. The first `diskutil info` call used the build subdirectory
and exited 1; the corrected mount-point call succeeded. Both outcomes are
retained. Existing `logs/phase1c-runtime-v5u4akhv` files were read, not modified.

### Artifact and suspected causes at this stop gate

The earlier artifact evidence confirms a 35,008-byte arm64 component launcher,
valid plist, version 155.0.8059.85 and identifier `org.chromium.Chromium`.
It records framework/libc++ dependencies and ad hoc linker signing. These are
prior observations, not a fresh comprehensive R2 artifact verification.
Framework/resource completeness, symlinks, xattrs/quarantine and pinned signing
rules still require investigation after host recovery.

| Diagnostic | Classification | Evidence and limit |
| --- | --- | --- |
| Signing-clone cross-device failure | CONFIRMED occurrence; POSSIBLE contributor | Prior browser logs show `clonefile` from the external app to internal translocation storage failing with errno 18 at `code_sign_clone_manager.mm:326`. Caller/fallback behavior and causal connection remain unresolved. |
| Duplicate Objective-C classes | CONFIRMED occurrence; POSSIBLE contributor | Logs name `ANGLESwapCGLLayer` in libgl_init/libblink_modules and `CrashpadHTTPBodyStreamTransport` in libbrowser_ui_views/libchrome_dll. Source definitions, expected component behavior and search-path correctness are not yet established. |
| Strict bundle verification failure | CONFIRMED occurrence; POSSIBLE contributor | Prior `codesign --verify --deep --strict` exited 1 with missing-resource-seal diagnostics. This does not prove launch failure or justify re-signing. |
| Persistent uninterruptible browser/helpers | CONFIRMED current blocker | Start-time/path/profile/group matches and current UE states; no successful cleanup or host restart. |

None of the three logged diagnostics is promoted to a confirmed hang cause.
The prior 45-second headless timeout occurred while the failed GUI instance
remained; it is not an independent test proving that the binary cannot start.
No source, GN, dependency, security or launch workaround is justified by this
checkpoint. No new runtime utility or regression test is needed for this
documentation-only stop decision.

### Full runtime matrix

`NOT TESTED` below means no functional evidence, including no new R2 attempt.
The startup/lifecycle failure carries forward the earlier attempted test.

| # | Feature | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Browser startup and shutdown | FAIL | Earlier GUI inspection timed out; same browser/helpers still UE |
| 2 | HTML rendering | NOT TESTED | Host recovery gate |
| 3 | JavaScript execution | NOT TESTED | Host recovery gate |
| 4 | HTTPS navigation | NOT TESTED | Host recovery gate |
| 5 | Multiple tabs | NOT TESTED | Host recovery gate |
| 6 | Back, forward and reload | NOT TESTED | Host recovery gate |
| 7 | Second window | NOT TESTED | Host recovery gate |
| 8 | Incognito | NOT TESTED | Host recovery gate |
| 9 | Bookmarks | NOT TESTED | Host recovery gate |
| 10 | History | NOT TESTED | Host recovery gate |
| 11 | Test download | NOT TESTED | Host recovery gate |
| 12 | Downloads management | NOT TESTED | Host recovery gate |
| 13 | Settings | NOT TESTED | Host recovery gate |
| 14 | Extensions management | NOT TESTED | Host recovery gate |
| 15 | Local PDF rendering | NOT TESTED | Host recovery gate |
| 16 | Print preview | NOT TESTED | Host recovery gate |
| 17 | Permission prompts | NOT TESTED | Host recovery gate |
| 18 | Session restoration | NOT TESTED | Host recovery gate |
| 19 | Browser version at runtime | NOT TESTED | Metadata matches; prior page attempt timed out without DOM |
| 20 | Sandbox/security status | NOT TESTED | No bypasses used; runtime enforcement not verified |

### Required recovery and delivery

Save open work and perform a **normal user-controlled macOS restart**.
No automatic restart is authorized or performed. Then confirm a newer boot time,
absence of the old process identities, acceptable memory pressure, APFS volume
identity and storage headroom before continuing R2 artifact/source diagnosis.
Only after that gate passes, run isolated sequential tests with fresh profiles,
tracked process start times and bounded observation/cleanup. Preserve compiled
outputs; do not rebuild merely because runtime failed.

Before these edits, `git fetch origin main` succeeded and both local and remote
tracking HEAD were `987d91af099aaa9ec5701cd66a22e0e45bcb7917`, with a clean tree.
Authenticated owner `A-K-M-Asifuzzaman` and configured author
`Asif Zman <138548302+asif4762@users.noreply.github.com>` were verified and retained.
All **113 offline tests pass** for this checkpoint. Foundation validation,
Python compilation, shell syntax and `git diff --check` also pass. No new test
logic was added; no real compiler or browser was started by these offline tests.
The commit, push and Actions results accompany delivery.
Phase 2 is not ready and has not started.

PHASE 1C-R2 PARTIAL/BLOCKED — RUNTIME DIAGNOSIS REPORTED — AWAITING ARCHITECT REVIEW

## Phase 1C-R3 — post-restart runtime findings (2026-10-21)

### Verdict and recovery gate

**PARTIAL.** The existing native Chromium now has direct responsive desktop,
version, rendering and navigation evidence. Clean shutdown **failed**: the native
Quit command reached teardown, its watchdog expired, and the browser terminated
with a diagnostic dump. No new browser was launched after an uninterruptible
state was observed. No termination signals were sent by this R3 investigation.

At 2026-10-20 22:05:53 UTC (October 21 04:05:53 Asia/Dhaka), boot time was
October 21 02:05:55 Asia/Dhaka (Unix 1792526755), newer than the previous failure.
The former browser/helpers were absent; executable/profile/start-time inspection
found no equivalent leftover compiled Chromium process. WindowServer and native
UI inventory responded. Pressure was normal (1), swap used was 0 MiB, and
internal free storage was approximately 89.57 GiB. The restart gate passed.

The external mount remained writable, case-sensitive APFS at `/Volumes/ssd(mac)2`,
UUID `47F505A1-126A-4EC6-8DB6-135813AA6111`, then disk7s2 in container disk7 with
physical store disk6s2. Initial external availability was 274,790,305,792 bytes
(255.92 GiB); the final check found 273,946,517,504 bytes (255.13 GiB), the same
UUID/device, normal pressure and zero swap. Source, tools and outputs remained
accessible. No disk or filesystem configuration was changed.

### Artifact, source and configuration

The existing checkout verifier passed again: Chromium
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`, depot_tools
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`, version 155.0.8059.85, matching DEPS
digest and clean tracked source. This did not rerun the historical dependency
sync. The successful one-job build's exit 0 and 39,487 completed steps remain
valid. No build, GN generation, source customization or tool upgrade occurred.
Effective GN arguments remain those recorded above, including component build,
arm64, `symbol_level=1`, `is_debug=false` and remote execution disabled.
`args.gn` SHA-256 remained
`cabeadd749736e664c312aca9303a57edd103c34fcc39d66d782128c4f44c1ab`.

The 35,008-byte launcher is executable (0755), Mach-O arm64. Info.plist validates,
identifies org.chromium.Chromium and version 155.0.8059.85. All five inspected
framework symlinks resolve through Versions/Current to 155.0.8059.85; required
PAKs, ICU data and the arm64 V8 snapshot exist. Direct `otool` dependencies of the
framework and selected major component libraries resolve to the existing output
or system paths. This was not an exhaustive recursive dependency/architecture
audit. No DYLD_/LD_ overrides were present. Recursive native `xattr` inspection
found no `com.apple.quarantine`; provenance attributes were left intact.

### Investigation of earlier warnings

All source references below refer to the pinned local Chromium checkout.

- **Signing:** `codesign -dv --verbose=2` reports an ad hoc linker signature,
  no TeamIdentifier, unbound Info.plist and no sealed resources. Strict deep
  verification still exits 1: "code has no resources but signature indicates
  they must be present". `chrome/BUILD.gn` and `build/config/mac/rules.gni`
  construct this development component app without the full distribution
  resource-sealing workflow. `chrome/installer/mac/signing/README.md` requires
  a non-component build for distribution signing. The unchanged app rendered
  successfully, so strict verification failure is not demonstrated as a startup
  blocker here. Distribution readiness is not claimed; no re-signing or security
  bypass was performed.
- **Cross-volume clone — UNRELATED to blocking startup in this R3 run:**
  `chrome/browser/chrome_browser_main_mac.mm` constructs CodeSignCloneManager.
  `chrome/browser/mac/code_sign_clone_manager.mm` obtains an internal
  `_dirhelper` user-local translocation directory under `/private/var/folders/`
  and attempts `clonefile` from the external Chromium.app into its X directory.
  EXDEV (18) is the expected cross-filesystem failure. `CloneApp` returns false;
  the asynchronous manager cleans up and invokes its callback with an empty
  path, allowing startup to continue. There is no copying fallback. The pinned
  `FailedClone` unit test documents this failure path (read, not executed).
  The quarantine-message context is this translocation directory; it does not
  establish that the source app is quarantined. The clone supports code-signing
  validation during app updates, not Crashpad. This warning recurred before the
  successful GUI checks, which rules out treating its presence alone as a
  startup-failure diagnosis. Its relationship to the old hang remains unproven.
- **Duplicate classes — component linkage confirmed; causal relationship UNKNOWN:**
  ANGLESwapCGLLayer comes from
  `third_party/angle/src/libANGLE/renderer/gl/cgl/WindowSurfaceCGL.mm`.
  Generated `init.ninja` and `modules.ninja` link the same WindowSurfaceCGL.o
  into libgl_init.dylib and libblink_modules.dylib. CrashpadHTTPBodyStreamTransport
  comes from `third_party/crashpad/crashpad/util/net/http_transport_mac.mm`;
  generated `net.ninja` places its object in libnet.a, which is in both the
  browser UI views and chrome_dll link inputs. Runtime warnings name these
  libraries in the same output directory. This explains the duplicate origins
  without evidence of a foreign library search path. It does not prove that
  duplicates are harmless or caused either hang; no library was changed.
- **Crashpad — previous high-CPU cause UNKNOWN:** `chrome/common/chrome_paths.cc`
  intentionally derives crash storage from the default user-data directory,
  independently of `--user-data-dir`. The supported `BREAKPAD_DUMP_LOCATION`
  override in `chrome/app/chrome_crash_reporter_client.cc` supplies the dedicated
  external location used by `components/crash/core/app/crashpad_mac.mm`.
  Both new handler command lines confirm the isolated database. Observed handlers
  slept at 0% CPU in the sampled windows; the old one-core spin did not recur in
  those samples. Restart, new profile and isolation changed together, so no
  single cause or cure can be inferred. Normal crash databases were not opened,
  deleted or changed. The teardown dump was successfully saved in isolation.

### One native launch and its observation limits

Exact launch at 2026-10-20 22:09:35.767 UTC (04:09:35 Asia/Dhaka), PID/PGID 61136:

```sh
BREAKPAD_DUMP_LOCATION='/Volumes/ssd(mac)2/TrinolBuild/test-profile-r3-15a6r33u/Crashpad-isolated' \
'/Volumes/ssd(mac)2/TrinolBuild/chromium/src/out/TrinolDev/Chromium.app/Contents/MacOS/Chromium' \
  --user-data-dir='/Volumes/ssd(mac)2/TrinolBuild/test-profile-r3-15a6r33u' \
  --no-first-run --no-default-browser-check about:blank
```

This is the already-executed command, not an instruction to relaunch. The profile
was new and external. The only environment override was the supported dump
location. No sandbox, web-security, certificate, permission or Gatekeeper bypass
was introduced, and no normal browser profile or credentials were used.
A scoped runner lock prevented overlapping controlled launches.

Native accessibility trees and screenshots in the task conversation demonstrate
the real Chromium desktop window and subsequent interactions. Early UI lookup
returned process-not-found before registration; later lookup and interaction
succeeded. This was a tooling/startup timing observation, not proof of failure.
`chrome://version` displayed 155.0.8059.85 Developer Build arm64, V8 15.5.35.25,
macOS 26.6.2, and the exact executable/profile paths above. Its embedded Revision
field showed zero hashes; source identity is independently verified by Git,
not by that missing runtime metadata.

The initial observer stopped at 22:10:46 UTC after one browser `Us` sample.
A following snapshot returned `Ss`, with GUI interaction still responsive.
No second browser instance or signal was used. A separate read-only observer
ran through the original 22:19:35 UTC observation deadline. CPU/process states
and available memory observations are retained in the evidence files. These
samples do not establish uninterrupted health throughout the session.

There was a long gap between GUI work around 04:13 and continuation around
12:01 Asia/Dhaka. The browser stayed open for about 7 hours 53 minutes, beyond
the ten-minute observation window. This run was **not continuously monitored or
bounded to ten minutes**. The observer had exited without reaping the eventual
browser exit, so its numeric exit status is unknown. Future approved runtime
work needs bounded lifecycle supervision as well as bounded observation; this
ad hoc observer is not being promoted to a reusable tested harness.

### Functional matrix and direct evidence

PASS means only the behavior described in the evidence column. It does not
imply comprehensive Chromium regression or security coverage.

| Feature | Result | Direct evidence / limit |
| --- | --- | --- |
| Native startup | PASS | Native window, accessibility tree and repeated GUI interaction from the compiled app |
| Clean shutdown | FAIL | Native Quit led to teardown watchdog expiry and a crash dump; details below |
| Version verification | PASS | GUI version 155.0.8059.85 arm64 and exact executable/profile; Git pins verified separately |
| Local HTML/CSS | PASS | Local fixture heading and green CSS panel visibly rendered |
| JavaScript | PASS | Script changed DOM text to `PASS: JavaScript updated the DOM` and the document title |
| HTTPS | PASS | Public https://example.com rendered; site information said `Connection is secure`; HTTPS-specific script assertion not tested |
| Multiple tabs | PASS | Version, fixture/PDF, HTTPS and internal pages opened in tabs |
| Back and forward | PASS | Second local page, back to fixture, forward to second page |
| Reload | PASS | Reload action on local second page retained rendered content; no network/cache semantics tested |
| Second window | NOT TESTED | Stopped additional runtime work after shutdown failure |
| Incognito | NOT TESTED | No private window opened |
| Bookmarks | PASS | Toolbar changed to `Edit bookmark for this tab`; history identified the fixture as bookmarked |
| History | PASS | chrome://history rendered the dedicated profile's test visits |
| Test downloads | PASS | `trinol-r3-smoke.txt`, 28 B, Done; chrome://downloads showed its entry and management controls |
| Settings | PASS | chrome://settings rendered sections; no settings changed |
| Extensions management | NOT TESTED | chrome://extensions not visited |
| PDF viewing | PASS | Local one-page PDF rendered its test text and finished loading |
| Print preview | PASS | One-page preview finished rendering; Cancel used, no print submitted |
| Site permission prompts | NOT TESTED | Fixture's permission control was not exercised |
| Session restoration | NOT TESTED | No relaunch after uninterruptible-state observation |
| Security indicators | PASS | HTTPS connection-security popup available; no security-bypass flags; sandbox enforcement/invalid-certificate tests not run |

The download used the browser's default destination, not an explicitly external
download directory. Its completion is UI evidence; no personal Downloads listing
or downloaded-file content inspection was performed. Test fixtures/profile/dump
are external. Local JavaScript execution was explicitly verified; separate
HTTPS JavaScript execution was not. Typed internal-page URLs initially lost their
prefix and became search queries; selecting the address field and pasting the
complete URL corrected input and made history/downloads render. This was an
interaction-timing correction, not a source or URL-handler fix.

### Shutdown failure and final host state

Cmd+Q did not promptly remove the window. The native Chromium application menu
was then opened and **Quit Chromium** selected. The subsequent UI call timed out.
At 06:02:46.816 UTC, browser 61136 was `Us` and renderer 96349 was `U`; isolated
Crashpad and other helpers were still present. The profile had already written
`exit_type: Normal`, which alone did not prove completion.

The next log evidence was:

```text
Teardown watchdog expired; recording dump and terminating.
```

Crashpad read warnings are timestamped 06:02:47 UTC; a renderer then reported
that its parent rendezvous server was gone. Pinned
`chrome/browser/shutdown_watchdog_mac.cc:64-80` waits for the shutdown-complete
event, writes exactly that diagnostic, calls DumpWithoutCrashing, then
`_exit(content::RESULT_CODE_HUNG)`. This **confirms watchdog termination**,
not the underlying cause of the stalled shutdown. The process exit code was not
captured and must not be reported as an observed 0 or inferred numeric status.

At **06:05:43 UTC**, a full process-command scan found no compiled-app or test-
profile processes, including the separately grouped Crashpad handlers. Pressure
was 1 and swap 0 MiB. The isolated pending dump
`e3d061ab-c5f7-487d-9abf-7e84bd01be89.dmp` exists and is preserved. No existing
minidump stackwalk utility was found in this output directory; the dump was not
symbolicated and no speculative repair or tool build was attempted. Its stack
analysis is the next useful investigation for architect review. No additional
restart, launch, signal, GN generation or compilation is needed merely to
preserve or review this evidence.

### Evidence, delivery scope and remaining gate

Raw local evidence remains outside Git at
`/Volumes/ssd(mac)2/TrinolBuild/logs/phase1cr3-runtime-kvtjt2bm`:
artifact/host and dependency checks, duplicate-link inputs, launch command,
browser log, process samples, observation outcome, intermediate shutdown checks
and `shutdown-completed-check.json`. The latter filename means processes are
absent, **not** that shutdown passed. GUI evidence is in this task's native
accessibility/screenshot transcript; screenshots were not exported into Git.
The isolated profile and crash dump remain preserved outside the repository.
Earlier R/R2 evidence has not been replaced or deleted.

Repository changes are limited to this report, README.md, docs/roadmap.md and
upstream/manifest.json. The manifest now records responsive launch, failed clean
shutdown and incomplete smoke baseline while retaining `chromium_compiled=true`
and all historical attempts. No runtime source, library, harness, test, fixture,
build argument or distribution configuration was added to the repository.

The original startup-hang cause, old Crashpad CPU spin and new teardown stall
remain unresolved. The R3 GUI success does not establish production readiness
or a safe repeat-launch workflow. Secondary untested cases are listed above.
**Phase 2 is not authorized; await architect review of the shutdown evidence.**

### R3 repository validation and Git delivery

All local checks passed after the documentation/manifest changes:

```text
python3 -m unittest discover -s tests -q     # 113 tests, OK
python3 scripts/validate_foundation.py      # Phase 1b completion gate retained
python3 -m compileall -q scripts tests      # exit 0
bash -n scripts/audit_macos.sh               # exit 0
git diff --check                           # exit 0
```

These offline checks validate repository tooling and documentation, not native
shutdown or production readiness. No new test logic was needed for this evidence-
only update. Chromium unit/browser suites were not built or run in R3.

Delivery is on `main`, authenticated as `A-K-M-Asifuzzaman`, retaining author
`Asif Zman <138548302+asif4762@users.noreply.github.com>`. `git fetch origin main`
confirmed no divergence from base `9dfd18ee41bfc048a0b99918a7cc628dab7487fa`.
Working and staged diffs are reviewed before the focused Conventional Commit;
only the four listed text files are staged. The delivered commit SHA, verified
remote HEAD and exact-commit GitHub Actions outcome accompany the final report.

## Phase 1C-R4 — shutdown investigation and lifecycle tooling

The [complete R4 report](phase-1c-r4-shutdown-investigation.md) records dump
validation, module UUID matches, symbolicated stacks, shutdown ordering and
ranked hypotheses. Local LLDB recovered the actual R3 browser main-thread wait:
ImageTransportFactory/Viz context destruction -> synchronous GPU
DestroyCommandBuffer -> Mojo response event. This locates the wait at capture;
it does not prove its duration or a deadlock cycle. The whole teardown watchdog
and an earlier network-process wait each allow ten seconds, so aggregate deadline
exhaustion is also plausible. No source patch or rebuild was justified.

R4 launched one fresh-profile blank session. The first harness recorded transient
U states, advanced Quit during startup and returned on native Quit refusal at
39.17 seconds (supervisor exit 1; browser exit unknown). The access interruption
and continuation gap left that instance open about 4h34m. Native-menu cleanup
later removed all test processes by 12:07:11 UTC, without another watchdog/dump,
but did not recover the missing process exit status. This is not a passing
bounded lifecycle. No additional instance was launched after failure.

The delivered harness preserves the startup deadline, continues bounded
supervision after refusal, limits native requests, retains real exit status
when available and blocks subsequent trials after failure. **143 offline tests
pass**, including 30 lifecycle tests; its corrected native path was not rerun.
The existing failure marker and all raw evidence remain external. No Chromium
source, GN, pin, security setting or compiled output was changed.
Compilation remains complete and R3 responsive-browsing passes stand; clean
shutdown and the remaining secondary checks are still gated on architect review.

PHASE 1C-R4 PARTIAL — AWAITING ARCHITECT REVIEW

## Phase 1C-R5 — native exit captured; supervision gate still partial

The [R5 report](phase-1c-r5-lifecycle-validation.md) records the exact reviewed
retry, native Quit audit, marker archive and lifecycle timeline. JXA property
access correctly invokes the zero-argument terminate selector; registration,
readiness, Boolean acknowledgment and process exit are now distinguished.
Transient U states defer native operations, monitor failures retain child
observation, and the original monotonic deadline remains fixed.

The only browser trial returned actual browser exit **0**, accepted Quit at
47.514 s and helper cleanup by 49.691 s, with no new watchdog or crash dump.
However, a **36.952-second observation gap before Quit** made the overall result
FAIL (supervisor exit 1). It cannot establish repeatable valid bounded shutdown.
The new failure marker blocks more launches; the conditional browsing trial was
not run. No browser remained after the test. R3's underlying watchdog cause
remains unresolved; R5 did not reproduce a shutdown stall.

All **162 offline tests pass**, including 49 lifecycle tests. The final small
native-state race correction was not rerun against Chromium. No source, pin,
GN, signing, security or compiled-output changes occurred. Next: investigate
per-operation monitoring/evidence-write latency before another reviewed retry.

PHASE 1C-R5 PARTIAL — AWAITING ARCHITECT REVIEW

## Phase 1C-R6 — improved observation; isolation gate failed

The [R6 report](phase-1c-r6-observation-reliability.md) records the bounded writer,
per-operation latency, exact R5 marker archive and one failed blank trial. The
owned browser accepted Quit at 46.267 s, exited 0 at 48.657 s and its helpers
were gone at 50.674 s. Maximum observation gap was 2.423 s; 78/78 evidence
records were acknowledged with final flush, no drops, watchdog or isolated dump.

The GUI app-selection call apparently started an unexpected second compiled-app
instance without the test profile. The supervisor correctly failed isolation.
The operator used normal Quit and all compiled-app processes were then absent;
that second process's exit status is unknown. Browsing was NOT TESTED. A small
offline-tested reporting correction now records unexpected identities and flags
operator cleanup needs. All 184 repository tests pass. R5 recovery is consumed,
the R6 failure marker remains active, and no further launch occurred. Existing
build outputs, pins and GN arguments are preserved. Phase 1C remains PARTIAL;
next review must establish a GUI observation route that cannot launch an app.

PHASE 1C-R6 PARTIAL — AWAITING ARCHITECT REVIEW
