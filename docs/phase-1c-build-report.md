# Phase 1C — native build and runtime evidence

Prior Phase 1C verdict: **PARTIAL — memory-blocked**, verified 2026-10-19.
Current Phase 1C-R recovery evidence is appended below. GN generation passed,
and the missing Metal compiler was installed and its failing action recovered.
The latest two-job attempt completed 16,212 steps before the resource guard
interrupted it. The full browser target is incomplete. No application launch or
browser functionality is claimed. Phase 2 remains gated.

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
