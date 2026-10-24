# Fresh-machine reproduction and upstream maintenance

This guide separates source/toolchain provisioning in Phase 1B from the gated
Phase 1C build. See the [checkout report](phase-1b-checkout-report.md) for actual
verification status. Patches and overlays remain empty. Do not substitute a
moving branch for a reviewed pin.

## Preparation

1. Clone this product repository and select a known product commit.
2. Provision macOS/Xcode and an APFS build volume with a space-free checkout path.
   Use the audit and storage budget in [environment-audit.md](environment-audit.md).
3. Review the current [upstream macOS instructions](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
   and the SDK requirements at the proposed source revision. macOS arm64 is the
   first target; do not treat this guide as Windows/Linux setup.
4. Select a Chromium baseline from upstream stable release information, resolve
   it to a full commit SHA, and record the selection rationale/version. Select
   and record an exact depot_tools SHA too, preferably the selected DEPS pin.
   Verify local HEADs, sync and hooks before populating upstream/manifest.json.

## Checkout and dependency sync (Phase 1B only)

Run the fresh-destination storage preflight before creating directories. Confirm
an APFS volume with physical capacity of at least 200 GiB plus 50 GiB headroom,
a whitespace-free resolved path, no conflicting data and a successful temporary
write/readback test. The preflight deliberately rejects nonempty destinations;
inspect an existing checkout separately before resuming it.

The following is a **generic reproduction example**, not active machine
configuration. Set `BUILD_ROOT` to an approved existing build root, and set both
revision variables to the full SHAs in the reviewed manifest. The machine used
for Phase 1B and the observed outcomes are in the
[checkout report](phase-1b-checkout-report.md). Run commands one at a time and stop
on any failure. Create the sibling directories only after verifying they do not
contain existing work.

```bash
: "${BUILD_ROOT:?Set the approved external APFS build root}"
: "${CHROMIUM_REVISION:?Set the manifest Chromium SHA}"
: "${DEPOT_TOOLS_REVISION:?Set the manifest depot_tools SHA}"
: "${CHROMIUM_TAG:?Set the manifest refs/tags/version}"

mkdir "$BUILD_ROOT/depot_tools" "$BUILD_ROOT/chromium" "$BUILD_ROOT/logs"
mkdir "$BUILD_ROOT/logs/tmp"
git init "$BUILD_ROOT/depot_tools"
git -C "$BUILD_ROOT/depot_tools" remote add origin https://chromium.googlesource.com/chromium/tools/depot_tools.git
git -C "$BUILD_ROOT/depot_tools" fetch --depth=1 origin "$DEPOT_TOOLS_REVISION"
git -C "$BUILD_ROOT/depot_tools" checkout --detach "$DEPOT_TOOLS_REVISION"

# This shell session only; no startup files or global Git cache changes.
export DEPOT_TOOLS_UPDATE=0 DEPOT_TOOLS_METRICS=0
export PATH="$PATH:$BUILD_ROOT/depot_tools"
export CIPD_CACHE_DIR="$BUILD_ROOT/depot_tools/.cipd-cache"
export VPYTHON_VIRTUALENV_ROOT="$BUILD_ROOT/depot_tools/.vpython-root"
export XDG_CACHE_HOME="$BUILD_ROOT/depot_tools/.cache"
export TMPDIR="$BUILD_ROOT/logs/tmp"
unset GIT_CACHE_PATH
"$BUILD_ROOT/depot_tools/ensure_bootstrap"

cd "$BUILD_ROOT/chromium"
gclient config --name=src --unmanaged --cache-dir=None https://chromium.googlesource.com/chromium/src.git
caffeinate -i gclient sync --no-history --nohooks --revision "src@$CHROMIUM_REVISION" --jobs=4 --output-json "$BUILD_ROOT/logs/sync-result.json"
git -C src rev-parse HEAD
git -C src fetch --depth=1 origin "$CHROMIUM_TAG:$CHROMIUM_TAG"
git -C src rev-parse "$CHROMIUM_TAG^{commit}"
caffeinate -i gclient runhooks
```

This uses the official `gclient` configuration/sync commands underlying `fetch`.
The verified `fetch` interface has no pinned-revision option; configuring first
and passing `src@SHA` to sync avoids initially downloading the moving main branch.
`--no-history` requests shallow source/dependency Git acquisition; individual
upstream-managed dependencies can have their own requirements. No shared Git
cache is enabled. `--nohooks` separates synchronization evidence from the required
hook execution. `ensure_bootstrap` provisions depot_tools' pinned runtime without
advancing its Git revision; disabling updates before bootstrapping otherwise
leaves `python3_bin_reldir.txt` missing.

During both sync and hooks, log output outside product Git and monitor physical
free space and the mounted device. Phase 1B used a temporary process-group guard
checking every five seconds and stopping at 60 GiB free, ten GiB above the hard
floor. The example commands above do **not** install that guard. Arrange equivalent
monitoring before using them; never continue below the required headroom. A
process-local `caffeinate -i` prevents idle sleep without persistent power changes.

If interrupted, inspect the existing source HEAD, tracked modifications, mount
and space before reissuing the same pinned sync command. Preserve partial files
for supported resumptions. Do not delete the checkout, reset unknown edits, add
`-D`/force flags, or change the selected revision to make a retry succeed.

After successful sync/hooks, from the product repository run:

```bash
python3 scripts/verify_upstream_checkout.py --checkout-root "$BUILD_ROOT/chromium" --depot-tools "$BUILD_ROOT/depot_tools"
```

The verifier checks the manifest, source/tool origins and HEADs, local release
tag, version file, expected source layout, tracked cleanliness and DEPS digest.
Dependency/hook success is recorded evidence: the verifier does not independently
prove every dependency is unchanged and does not rerun downloads or hooks.

## Applying Trinol customizations

Through Phase 1B there are none: patches/series contains only comments and overlays is
empty. Phase 2A adds the tested `scripts/apply_product_patches.py` infrastructure with
these rules (no application to the actual checkout is authorized in 2A):

- Verify the upstream HEAD equals the manifest SHA and the working tree is clean.
- Resolve each series entry strictly beneath patches/; reject path traversal and
  symlinks escaping the directory. Apply the listed patches sequentially, using
  `git apply --check` then `git apply` for each patch. Do not check all dependent
  patches against the unmodified base. Stop at the first failure, report which
  patches were applied, and preserve the checkout for inspection.
- Copy only declared overlay mappings after validating their source/destination
  containment, collisions and expected existing content. See
  [overlay rules](../overlays/README.md). Never silently overwrite local work.
- Capture the final source diff and manifest, and ensure GN integration patches
  explicitly include Trinol modules/resources. The applicator is now covered by synthetic dependent-patch, failure and
  reapplication tests.

For Phase 1's initial baseline, keep both customization lists empty and prove the
unmodified build before adding product changes.

## Build and launch (Phase 1C only)

From product Git, use the resource-monitored runner with an approved build root:

```bash
xcrun metal --version
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --generate
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --jobs 4
# After a pressure stop, resume the same output at two jobs:
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --jobs 2
```

If Xcode reports a missing Metal compiler, install its supported matching component
with `xcodebuild -downloadComponent MetalToolchain -exportPath "$BUILD_ROOT/metal-toolchain"`,
then verify `xcrun metal --version`. Xcode manages the installed component location.
The runner verifies pins and APFS capacity, preserves matching GN arguments,
checks resolved values, keeps Siso's cache external and stops on unsafe resource
conditions. Never run concurrent builds against the same output. If the two-job attempt also
stops for memory pressure, relieve the host pressure before retrying; do not
reset the swap baseline repeatedly to work around the safety guard. See the
[Phase 1C report](phase-1c-build-report.md) for commands, failures and actual results.

### Phase 1C-R recovery

After read-only memory/process diagnostics and a no-build trend sample show
normal pressure or stable elevated pressure with adequate host disk headroom,
resume the existing output without regenerating GN:

```bash
python3 scripts/build_chromium_macos.py --build-root "$BUILD_ROOT" --jobs 1
```

The runner accepts 1, 2 or 4 jobs and uses an exclusive advisory lock at
`logs/TrinolDev.lock`. A stale file is harmless; an active lock rejects another
runner, including GN generation. Do not bypass it with a manual concurrent build.

Critical pressure, 4 GiB swap growth, the 60 GiB external floor and 10 GiB internal
floor still stop immediately at the next sample. Four jobs still request a
reduction after 60 seconds of warning. At one or two jobs, the 180-second
memory timer now starts only when warning pressure and at least 2 GiB new swap
coincide. Normal pressure or growth below 1.5 GiB resets that timer; the small
hysteresis band avoids noise at 2 GiB. The original attempt showed a brief swap
spike inheriting an old warning timer, which did not prove sustained new growth.
No hard resource threshold was raised. Monitor errors stop the owned process.

Resource samples include actual monotonic intervals, swap growth, pressure,
process-group CPU percentage from `ps`, host load, and bounded log-tail progress.
CPU percentage is a `ps` observation, not a benchmark; action counters are local
to each Siso attempt, not a fixed percentage of the entire project. Detailed
command logs preserve warnings that fall outside the sampled tail. Sampling is
requested every five seconds, not guaranteed in real time. A measured gap over
60 seconds stops the build conservatively once the monitor regains control;
uninterruptible I/O can delay even that response.

Status distinguishes `completed`, `command_failure`, `controlled_stop`,
`interrupted` and `monitor_failure`, retaining the actual child exit code.
The CLI returns 75 for controlled resource stops, 1 for other failures, and 0
only for successful command completion and required inspection. None of these
build statuses alone establishes browser launch or functional success.

Only after the entire `chrome` target finishes successfully, validate the bundle
and launch the newly compiled executable with its dedicated profile:

```bash
"$BUILD_ROOT/chromium/src/out/TrinolDev/Chromium.app/Contents/MacOS/Chromium" --user-data-dir="$BUILD_ROOT/test-profile"
```

Keep generated output outside product Git. Record exact artifact, launch and
functional checks; successful compilation alone does not establish runtime or
release readiness.

## Updating upstream

Monitor upstream security releases; prioritize security updates over UI work.
Select a candidate revision, preserve the current known-good product commit, and
use a clean separate checkout to validate the upgrade. Sync its dependencies,
reapply the ordered patch series, resolve drift in small reviewed changes, and
run compilation plus relevant browser and product regression checks. Record
removed/reworked patches, compatibility changes and test evidence alongside the
new manifest. Promote only after review; roll back through a normal revert/new
commit rather than rewriting shared main.

Do not commit upstream source, build outputs, caches, test profiles, machine paths
as active configuration, or credentials. Maintain licensing notices and a manifest
for any redistributed third-party assets. Public releases additionally require a
secure updater, signing/notarization and an incident response process.

## Phase 1A preparation refinements

Run the read-only preflight before provisioning or downloading. It requires an
explicit fresh checkout path, verifies actual APFS/device/image backing and uses
at least 200 GiB for the build environment plus 50 GiB safety headroom. Exit 0
means storage passed with warnings, 1 means blocked, 2 means invalid CLI usage.
It cannot reserve capacity or prove write access without writing. It deliberately
rejects nonempty destinations and existing repository/gclient ancestors; use a
separate reviewed inspection procedure to maintain an existing checkout.

Keep sibling directories for `chromium/` (fetch root; source in `chromium/src/`),
`depot_tools/`, `test-profile/` and logs under the approved build root. Generated
GN/Ninja output stays in `chromium/src/out/TrinolDev/`. None belongs in product Git.
Paths with shell metacharacters must be quoted even when they have no spaces.

Phase 1A performed no downloads and retained null manifest pins. Phase 1B selects
an official stable release, records exact source/tool SHAs only after local
verification, and retains dependency/hook evidence. Before any new acquisition,
inspect the selected revision's `build/config/mac/mac_sdk.gni`, compare it with
installed Xcode/SDK details, and read the current upstream instructions. SDK
compatibility and source verification do not prove compilation.

For the 18 GiB M3 Pro, retain the proposed arm64 component configuration,
`is_debug=false` and `symbol_level=1`, with an initial four-job local build limit.
This is unbenchmarked guidance: monitor memory pressure/swap and disk headroom.
Level 1 trades some debugging detail for lower resource use. Verify each argument
against the pinned revision and record effective GN args. Do not use official
release flags or reduce sandbox protection to achieve a successful launch.

## Phase 2A design-only integration contract

The [native UI plan](design/native-ui-integration-plan.md) maps Orbit to the
pinned Views/WebUI source. Patches and overlays remain empty. The new applicator
defaults to check-only using temporary Git index/object storage and supports
dependent patches. Explicit --apply is for a future reviewed native phase; it
never resets or overwrites existing overlay files. Overlay declarations require
source, destination under trinol/ and SHA-256. Directory overlays, symlink/binary
patches and rename/copy patches are unsupported. See the plan for exact limits.
The foundation validator intentionally retains the empty baseline restriction.
