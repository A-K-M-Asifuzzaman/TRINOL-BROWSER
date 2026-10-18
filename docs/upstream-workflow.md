# Fresh-machine reproduction and upstream maintenance

This is the procedure for a later approved phase, not a claim that a browser can
already be built from Phase 0/1A. The manifest has no selected revisions yet, no
patches and no overlays. Do not substitute a moving branch for a recorded pin.

## Preparation

1. Clone this product repository and select a known product commit.
2. Provision macOS/Xcode and an APFS build volume with a space-free checkout path.
   Use the audit and storage budget in [environment-audit.md](environment-audit.md).
3. Review the current [upstream macOS instructions](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
   and the SDK requirements at the proposed source revision. macOS arm64 is the
   first target; do not treat this guide as Windows/Linux setup.
4. Select a Chromium baseline from upstream stable release information, resolve
   it to a full commit SHA, and record the selection rationale/version. Select
   and record an exact depot_tools SHA too. Populate upstream/manifest.json in
   a reviewed Phase 1 change before claiming reproducibility.

## Checkout and dependency sync (Phase 1B only)

The following example assumes a separately provisioned `/Volumes/TrinolBuild`
APFS volume. These paths are generic examples, not paths created by Phase 0/1A.
The actual recommended machine-specific layout is recorded in the
[Phase 1A report](phase-1a-storage-readiness.md); substitute that approved build
root consistently rather than assuming this example mount exists.
Set `CHROMIUM_REVISION` and `DEPOT_TOOLS_REVISION` to the full reviewed 40-character
SHAs from the manifest. Never use literal placeholders or guess versions.

```bash
# Check these prerequisites before cloning anything.
: "${CHROMIUM_REVISION:?Set the reviewed Chromium commit SHA}"
: "${DEPOT_TOOLS_REVISION:?Set the reviewed depot_tools commit SHA}"
test "${#CHROMIUM_REVISION}" -eq 40
test "${#DEPOT_TOOLS_REVISION}" -eq 40

# New, empty directories only. Stop if existing checkouts need reconciliation.
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git /Volumes/TrinolBuild/depot_tools
git -C /Volumes/TrinolBuild/depot_tools checkout --detach "$DEPOT_TOOLS_REVISION"
export DEPOT_TOOLS_UPDATE=0
export PATH="$PATH:/Volumes/TrinolBuild/depot_tools"
mkdir /Volumes/TrinolBuild/chromium
cd /Volumes/TrinolBuild/chromium
fetch --nohooks chromium
cd src
git fetch origin "$CHROMIUM_REVISION"
git checkout --detach "$CHROMIUM_REVISION"
gclient sync -D --revision "src@$CHROMIUM_REVISION"
git rev-parse HEAD
```

Run commands one at a time and stop on any failure. The `-D` sync removes obsolete
DEPS-managed dependency directories, so use it only in this fresh dedicated
checkout or after verifying an existing checkout has no work to preserve. Hooks
run during sync and download the pinned dependencies/toolchain. Record their
outcome and effective tool versions. depot_tools auto-update is disabled to keep
the selected tool revision stable; upgrades should be deliberate. Initial source
acquisition can be large even before the final selected revision is checked out.
Do not run an upstream sync over unknown local edits.

## Applying Trinol customizations

In Phase 0 there are none: patches/series contains only a comment and overlays is
empty. For future versions, implement an applicator with these rules:

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
  explicitly include Trinol modules/resources. Do not claim an applicator exists
  until it is implemented and tested with failure/reapplication cases.

For Phase 1's initial baseline, keep both customization lists empty and prove the
unmodified build before adding product changes.

## Build and launch (Phase 1C only)

Copy [the example GN arguments](../config/macos-arm64.args.gn.example) into
`src/out/TrinolDev/args.gn` after validating them against the chosen revision.
From the separate upstream `src` directory:

```bash
gn gen out/TrinolDev
autoninja -C out/TrinolDev -j 4 chrome
out/TrinolDev/Chromium.app/Contents/MacOS/Chromium --user-data-dir=/Volumes/TrinolBuild/test-profile
```

These are planned commands, not Phase 0 test results. Record resolved GN arguments,
source/tool SHAs, SDK/toolchain versions, build logs and launch behavior. Four jobs
is a starting resource limit for this host, not a measured optimal configuration.
Use only a disposable dedicated profile. Keep generated output outside product Git.
Choose relevant unit/browser tests from the pinned source and record exact commands
and results; a successful launch alone is insufficient for release readiness.

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

The manifest's phase is now `1a`; both revision fields remain null. In Phase 1B,
choose an official stable version using Chromium release records, resolve its tag
in the official repository to an exact commit, and verify that commit exists.
Resolve an intentional depot_tools revision the same way. Record full SHA values,
source version and selection rationale; do not copy moving `main` labels into the
revision fields. Reconcile depot_tools compatibility with the chosen baseline.

Before source sync, inspect the selected revision's `build/config/mac/mac_sdk.gni`
and its documented SDK/toolchain checks, including `mac_sdk_official_version`.
Compare these to `xcodebuild -version`, `xcrun --show-sdk-version` and the installed
SDKs. Newer Xcode is not proof of compatibility. Keep Chromium's DEPS/hook-managed
compiler and dependencies aligned with the selected source. Confirm compatibility
in the Phase 1B record, and actual compilation only in Phase 1C.

Large downloads start with Chromium `fetch` and continue through `gclient sync`
(dependencies, toolchain and hooks). depot_tools installation is smaller but is
also deferred to Phase 1B. Keep caches on the reviewed build storage too; do not
silently fill the internal SSD with a separate Git cache. A full-history fetch
may consume substantially more than a shallow fetch; decide and budget at Phase
1B. No checkout or dependency download was performed during Phase 1A.

For the 18 GiB M3 Pro, retain the proposed arm64 component configuration,
`is_debug=false` and `symbol_level=1`, with an initial four-job local build limit.
This is unbenchmarked guidance: monitor memory pressure/swap and disk headroom.
Level 1 trades some debugging detail for lower resource use. Verify each argument
against the pinned revision and record effective GN args. Do not use official
release flags or reduce sandbox protection to achieve a successful launch.
