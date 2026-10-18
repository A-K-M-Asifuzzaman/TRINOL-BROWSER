# Phase 1B — native Chromium checkout and toolchain report

Status: **COMPLETE — ready for architect review before Phase 1C**. The pinned
native source, dependency sync, hooks and toolchain provisioning are verified.
GN generation, compilation and browser execution remain unperformed and gated.

## Machine and storage observations

Rechecked on 2026-10-18: Apple M3 Pro, 11 CPU cores, native arm64, 18 GiB RAM;
macOS 26.6.2 (25G83), Xcode 26.5 (17F42), macOS SDK 26.5 (25F70).
Xcode first-launch check succeeded. Host Python is 3.12.6; Git is 2.50.1.

The existing external X900 Plus 1TB USB SSD is physical disk6. The approved
APFS volume is disk7s2, mounted at `/Volumes/ssd(mac)2`, in container disk7 backed
by disk6s2. Initial available capacity was **334,074,732,544 bytes (311.13 GiB)**.
This was measured available capacity, not the device label or purgeable storage.
Final measured physical/container free space is **283,203,772,416 bytes
(263.75 GiB)**, matching the volume's available-space measurement. The observed
initial-to-final reduction is 47.38 GiB; APFS capacity is shared and not reserved.
The existing read-only storage preflight passed before directory creation.
The dedicated root was checked for conflicts; a temporary file was written,
fsynced, read back and removed. No permissions or physical partitions changed.

These are **machine-specific observations**, not active configuration:

- Build root: `/Volumes/ssd(mac)2/TrinolBuild`
- depot_tools: `/Volumes/ssd(mac)2/TrinolBuild/depot_tools`
- gclient root: `/Volumes/ssd(mac)2/TrinolBuild/chromium`
- Source: `/Volumes/ssd(mac)2/TrinolBuild/chromium/src`
- Logs: `/Volumes/ssd(mac)2/TrinolBuild/logs`
- Planned Phase 1C output: `chromium/src/out/TrinolDev`
- Planned Phase 1C disposable profile: `test-profile`

Resolved build paths contain no whitespace. Parentheses are handled through
quoted shell arguments or Python subprocess argument arrays. Product Git remains
in its original HFS+ workspace, outside the source/tool checkout.

## Selected stable source and tooling

| Field | Verified selection |
| --- | --- |
| Chromium version | 155.0.8059.85 |
| Platform/channel | Mac / Stable |
| Release metadata timestamp | 2026-10-15T20:40:01.968Z |
| Tag | refs/tags/155.0.8059.85 |
| Chromium SHA | 0e66b94549a8bd85f03fbdf189b752d6e7b63c32 |
| depot_tools SHA | dca727ba1f8fa8f1e3b12a815d065818bb61d395 |
| DEPS SHA-256 | 23ef1ed90785da130901961e4f4179b4fc10adac957eee5622d7e67fe4b82ec5 |

The release was selected from the official
[ChromiumDash Mac Stable metadata](https://chromiumdash.appspot.com/fetch_releases?channel=Stable&platform=Mac&num=3).
`git ls-remote` against the official source repository resolved the tag to the
same full SHA. The source URL is
[chromium/src.git](https://chromium.googlesource.com/chromium/src.git).
This was the current returned Mac Stable baseline at selection time, rather than
a moving main revision or an older release chosen for convenience.

The depot_tools pin comes directly from this Chromium revision's
[DEPS](https://chromium.googlesource.com/chromium/src/+/0e66b94549a8bd85f03fbdf189b752d6e7b63c32/DEPS),
where it pins `src/third_party/depot_tools`. The separately installed command
checkout uses that exact commit from the official
[depot_tools repository](https://chromium.googlesource.com/chromium/tools/depot_tools.git).
Automatic updates are disabled in the session; the revision is not a moving tip.

## SDK and Apple Silicon assessment

Before acquisition, the selected source's
[mac_sdk.gni](https://chromium.googlesource.com/chromium/src/+/0e66b94549a8bd85f03fbdf189b752d6e7b63c32/build/config/mac/mac_sdk.gni)
was read from upstream. Its official SDK is **26.5, build 25F70**, exactly matching
the installed SDK. The minimum SDK override is 15 and the deployment/minimum
system versions are 13.0. The native arm64 route is documented by upstream's
[Apple Silicon guide](https://chromium.googlesource.com/chromium/src/+/0e66b94549a8bd85f03fbdf189b752d6e7b63c32/docs/mac_arm64.md).

The acquired SDK file and DEPS match the files inspected before download byte
for byte. The source's `should_use_hermetic_xcode.py mac` returns 0 on this host;
its Mac toolchain hook therefore uses the existing system Xcode rather than
installing another Xcode. These checks establish sufficient compatibility for
source/toolchain provisioning; they do not prove a successful compilation.

## Acquisition procedure and evidence

The [reproduction guide](upstream-workflow.md) records session-local setup and
commands. Both primary Git checkouts use shallow acquisition. `gclient config`
sets `managed=False` and `cache_dir=None`; sync requests the selected `src@SHA`
with `--no-history --nohooks --jobs=4`. No destructive `-D`, force/reset or cleanup
was used. Required hooks are a separate step after successful synchronization.

The standalone depot_tools checkout initially could not run `fetch` because its
Python bootstrap marker was absent while updates were disabled. Running upstream
`ensure_bootstrap` provisioned its runtime without changing its Git HEAD. The
`fetch` dry run and `gclient` command help then succeeded. Source selection used
`gclient config` plus revision-pinned sync because `fetch` does not expose a
pinned-revision option. It did not download a separate moving-main checkout.

CIPD, vpython, XDG caches and temporary downloads were directed into the external
build root. No shared Git cache was enabled. A temporary guard checks the mount
identity and available capacity every five seconds, stopping the acquisition
process group at 60 GiB free to protect the required 50 GiB floor. `caffeinate -i`
prevents idle sleep only for the active transfer process.

Logs are retained outside product Git: `bootstrap.log`, `fetch-dry-run.log`,
`gclient-sync-help.log`, `gclient-config-help.log`, `source-sync.log`,
`acquisition-status.json`, `sync-result.json`, `hooks.log`, `hooks-status.json`
and `dependency-head-verification.json`.

Source HEAD and `chrome/VERSION` match the selected revision/version, and the
source Git repository reports shallow history. `gclient sync` exited 0. Of 1,251
conditional entries in its result, 240 were processed: 151 Git repositories,
50 Google Storage entries and 39 CIPD entries. Every processed entry reports
successful synchronization. Inactive platform/internal entries were not acquired.
An independent readback of all 151 Git HEADs matched their recorded pins, with
zero mismatches (`dependency-head-verification.json`). The narrowly fetched local
release tag resolves to the same source SHA. Both tracked source/tool worktrees
are clean, and the product checkout verifier passes against the populated manifest.

`gclient runhooks` exited 0. Python setup, revision metadata, dsymutil download,
location tags, Reclient/Siso configuration and platform hooks completed. The Mac
hook explicitly reported that Xcode installation was skipped. The upstream
landmines hook created an empty `src/out/` directory and ignored metadata; neither
`out/TrinolDev` nor the test profile exists. No GN files were generated.

## Toolchain checks

All commands were resolved from the pinned external depot_tools session, with
version checks run from the source directory. Full output is retained in
`toolchain-verification.json` outside product Git.

| Tool | Observed result |
| --- | --- |
| fetch | Official dry run/help succeeded after bootstrap |
| gclient | Configuration/help, dependency sync and runhooks succeeded |
| GN | 2562 (cfcd774b98f3), version command exit 0 |
| Ninja | 1.12.1, version command exit 0 |
| autoninja | Wrapper ran and displayed Siso Ninja help; help exit 2, no build |
| Clang | 24.0.0git, target arm64-apple-darwin25.6.0, exit 0 |
| Clang package | llvmorg-24-init-7747-g62397f8b-27 |
| Rust | 1.100.0-nightly (1edd55dcf 2026-09-09), exit 0 |
| Siso | v1.6.1, version command exit 0 |

Clang reports LLVM commit `86922d51225db089fffb99475eefc4904f79e3c8`.
Siso reports CIPD instance `wHSv-2pZk04lFHSjykxe2cYAdLikzLeFqp6SVdrtMDUC` and
source commit `d38036b64e81c5fdb5d25a92081e6f98a020163d`. Its optional online commit
lookup returned HTTP 429 after displaying the installed version/package identity.
This is a metadata lookup warning, not a failed dependency install; no build was
used to test Siso. Autoninja's observed help exit 2 is recorded rather than
reported as an exit-0 check.

## Phase 1C configuration review

The six proposed arguments were inspected in the acquired source:

| Argument | Source evidence | Proposed value |
| --- | --- | --- |
| target_os | GN builtin consumed by build/config/BUILDCONFIG.gn | "mac" |
| target_cpu | GN builtin consumed by build/config/BUILDCONFIG.gn; arm64 Mac toolchain | "arm64" |
| is_debug | declare_args in build/config/BUILDCONFIG.gn | false |
| is_component_build | declare_args in build/config/BUILDCONFIG.gn | true |
| symbol_level | build/config/compiler/compiler.gni, allowed range 0–2 | 1 |
| is_official_build | declare_args in build/config/BUILDCONFIG.gn | false |

The [GN template](../config/macos-arm64.args.gn.example) is a proposed local
configuration. Source inspection confirms the names and values are supported;
GN has not evaluated an output directory. Phase 1C must generate GN files and
inspect effective arguments before compilation.

For 18 GiB RAM, begin with four local jobs, monitor memory pressure/swap and
reduce to two if necessary. Component libraries reduce monolithic link pressure;
level 1 retains basic symbols with less storage than full symbols. If measured
pressure requires it, level 0 is an explicit debugging tradeoff for a later run.
Upstream documents `use_lld=false` as a possible faster linker option for native
arm64 macOS; retain defaults initially and evaluate that only with build evidence.
`use_remoteexec` defaults false. Hooks configured Siso, which `autoninja` selects
and runs offline when remote execution is disabled. The wrapper maps `-j 4` to
Siso's four local jobs on this 11-core host. Confirm effective GN arguments and
executor in Phase 1C.

Siso help exposes an internal `Library/Caches/siso` default on macOS, despite
`XDG_CACHE_HOME`. No build cache was populated during these help/version checks.
For the planned Siso build, pass `-cache_dir="$BUILD_ROOT/siso-cache"` so its build
cache also stays on the external volume. The reproduction guide includes this
flag; omit it if explicitly selecting plain Ninja instead. None of these settings
requires disabling sandboxing, signing checks, TLS or platform security.

## Product changes and validation

Added a read-only manifest/checkout verifier and 26 offline tests, extended the
foundation validator for verified Phase 1B manifests, and updated engineering
phase boundaries. The 43 existing storage tests also pass (69 total).
The validator requires recorded sync/hook completion flags for a Phase 1B
manifest; these were set only after both commands exited 0. The checkout verifier
checks source/tool Git identities, tracked cleanliness,
local release tag, version file and DEPS digest; it does not independently verify
every dependency or repeat hooks.

Tooling milestone: `cd448f156b49fb2dedf1846f300830d22f1a96e8` —
`feat(build): add pinned upstream checkout verification`, pushed to `origin/main`.
[GitHub Actions](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39125009330)
passed for that exact commit. The approved Phase 1A commit
`eb2bf2556871f1c46aaca3e7320021797765c463` remains in history.
Git identity was preserved as Asif Zman with the owner's existing GitHub noreply
email. Authenticated GitHub account: `A-K-M-Asifuzzaman`.

The manifest now records verified source/tool SHAs, release metadata, DEPS digest,
sync/hook results, toolchain versions and the proposed GN template. Patches and
overlays remain empty. Updated files in this phase are `AGENTS.md`, `README.md`,
`docs/roadmap.md`, `docs/upstream-workflow.md`, this report, `upstream/manifest.json`,
`config/macos-arm64.args.gn.example`, `scripts/validate_foundation.py`, the new
`scripts/verify_upstream_checkout.py` and its new test file.

Final local checks passed:

- `python3 -m unittest discover -s tests -q`: 69 tests.
- `python3 scripts/validate_foundation.py`: populated Phase 1B manifest, empty
  customization contract, bounded repository files and local documentation links.
- `python3 scripts/verify_upstream_checkout.py` with explicit external paths:
  matching origins, HEADs, local tag, version, DEPS digest and clean tracked files.
- `python3 -m compileall -q scripts tests`, `bash -n scripts/audit_macos.sh`
  and `git diff --check`.
- Initial storage preflight, successful source/dependency sync and hooks,
  all 151 Git dependency HEADs, tool checks and final physical capacity.

Git delivery uses normal commits and `git fetch origin main`, ancestry checks,
`git push origin main` and `git ls-remote origin refs/heads/main`; no identity
changes or history rewriting. The final delivery commit and its Actions result
are reported with the phase handoff, since a commit cannot contain its own SHA.

## Limits and review gate

No Trinol source patches or overlays have been introduced. No GN generation,
Chrome compilation, browser launch, browser/unit/WebUI test execution, signing,
notarization or performance measurement has occurred. Foundation CI verifies
repository tooling, not Chromium. External USB stability, shared APFS capacity
and 18 GiB memory remain practical build risks; headroom must be measured again
before Phase 1C. The environment is ready to attempt Phase 1C after review;
compilation success, effective GN configuration, memory use and launch behavior
are not established. Do not proceed without explicit architect approval.
