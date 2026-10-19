# Phase 1C — native build and runtime evidence

Status: **IN PROGRESS**. GN generation is verified. Compilation has been started
but has not completed. No application launch or browser functionality is claimed.
Phase 2 remains gated.

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
pressure with at least 2 GiB additional swap for 180 seconds stops the attempt.
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
278,919,000,064 bytes (259.76 GiB); baseline pressure remained 2 with approximately
11.98 GiB swap. Its final outcome remains pending.

## Artifact and launch checks

No completed `Chromium.app` has been verified. Artifact architecture, executable
permissions, bundle metadata, linked libraries, version and signing checks await
a successful `chrome` build. A partial bundle must not be treated as a finished
browser. The dedicated `test-profile` has not been used; personal Chrome profiles
are outside scope.

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
# Only after a pressure stop, preserve output and resume with:
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --jobs 2
```

The generation command preserves an existing matching args.gn and refuses an
unexpected configuration. The build command requires generated files, inspects
effective GN arguments and verifies the browser target before compiling.
Each attempt writes a unique directory beneath external `logs/`, with command
output, resource samples, status and argument/target evidence. Do not rerun a
second build while an attempt remains active.

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
