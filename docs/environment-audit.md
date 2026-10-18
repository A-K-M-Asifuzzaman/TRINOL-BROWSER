# Phase 0 environment audit

Audit date: 2026-10-18 (Asia/Dhaka). Read-only local inspection; no Chromium
checkout, package installation, disk formatting or browser build performed.

## Findings

| Check | Observed | Assessment |
| --- | --- | --- |
| Host | Apple M3 Pro, Mac15,6, arm64, 11 CPU cores | Native arm64 target suitable |
| Memory | 19,327,352,832 bytes (18 GiB) | Constrain build concurrency; performance unmeasured |
| OS | macOS 26.6.2, build 25G83 | Installed; not a successful build claim |
| Xcode | 26.5, build 17F42; selected full Xcode | Present |
| SDK | macOS 26.5 | Present; compatibility must be checked against selected Chromium pin |
| Xcode first launch | `xcodebuild -checkFirstLaunchStatus` exited 0 | Setup check passed |
| Compiler | Apple clang 21.0.0 | Available; Chromium's pinned toolchain comes from its hooks |
| Git | 2.50.1 (Apple Git-155) | Available |
| Python | 3.12.6 | Available |
| Chromium tools | fetch, gclient, gn, ninja, autoninja absent from PATH | Provision in Phase 1 |
| Known tool locations | ~/depot_tools, ~/chromium, /opt/depot_tools absent | Not a full-disk search |
| Product workspace | External USB SSD, Journaled HFS+, about 345 GiB free | Fine for small product repository; unsuitable for Chromium checkout |
| Workspace path | Contains spaces | Chromium checkout must use a different path |
| Internal filesystem | APFS, about 65 GiB free at audit | Below this project's planned build headroom |
| GitHub | Owner authenticated, push/admin permission; target remote initially empty | Ready for foundation delivery |

Chromium's [macOS build instructions](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
require APFS and a space-free checkout path. Its [Arm Mac guidance](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_arm64.md)
supports native arm64 builds. Xcode/SDK presence alone does not establish
compatibility with a future pinned revision.

## Verdict and next-phase prerequisites

**READY for repository/documentation work; NOT READY for a Chromium checkout or
build at the current location.** Phase 0 audit is complete; Phase 1 is gated.

Use a separate APFS build volume and a path such as `/Volumes/TrinolBuild/chromium`.
Budget at least 200 GiB free initially, preferably 300+ GiB for source, one build,
intermediate files and upgrades. This is a conservative project planning budget,
not an upstream guaranteed minimum or measured consumption. The current internal
free space does not meet it. An APFS sparse image on the external drive is an
option to evaluate separately; no image was created and no disk was reformatted.
Do not erase or repartition storage as an incidental setup action.

After review: choose suitable storage, install depot_tools, select exact upstream
pins, check the pinned SDK/toolchain requirements, sync dependencies, then measure
an unmodified Chromium build with conservative parallelism (start around four
jobs and adjust from memory pressure). Keep a dedicated test profile.

## Evidence and limits

Commands: `sw_vers`, `uname -m`, `sysctl -n hw.memsize hw.ncpu hw.model
machdep.cpu.brand_string`, `df -h . /`, `diskutil info`, `xcode-select -p`,
`xcodebuild -version`, `xcodebuild -checkFirstLaunchStatus`,
`xcrun --show-sdk-version`, `clang --version`, `git --version`,
`python3 --version`, PATH lookups and three known-location checks.

Sandboxed network/keychain checks initially failed; authorized host checks
confirmed working GitHub authentication. Some hardware queries likewise needed
host access. These were sandbox restrictions, not evidence of invalid credentials
or broken hardware. No browser tests, signing, notarization, sustained disk speed,
network throughput or full source discovery were performed.

The related “Build Chromium Browser” chat established native Chromium, TrinolIT
branding and macOS-first scope. Its original Phase 0 prompt was embedded in an
unavailable reference; this audit follows the explicit supplied GitHub workflow
and the readable project context, without claiming an exact hidden checklist.
