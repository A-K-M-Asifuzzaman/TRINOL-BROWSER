# Phase 1A — storage and build readiness

Date: 2026-10-18 (Asia/Dhaka). Phase 0 was approved at
`5c3ec7b8921e43911708bfdaba328e7710bbfe15`; local and fetched `origin/main`
matched with a clean working tree before changes. Architecture is unchanged.

**Verdict: Phase 1A readiness work complete. A suitable existing external APFS
volume passes the read-only storage preflight. No storage was provisioned, and
Phase 1B/1C have not started.**

## Fresh inventory

The broader inventory corrects Phase 0's limited storage conclusion: the same
physical external SSD has an APFS partition in addition to the HFS+ workspace.
The physical disk is `X900 Plus 1TB`, 1,024,209,543,168 bytes, USB, SSD, observed as
`disk6`. SMART status is unavailable through this connection. Device identifiers
are observations, not stable configuration; re-identify disks before any operation.

| Candidate | Actual filesystem and device chain | Capacity at inspection | Assessment |
| --- | --- | --- | --- |
| Existing external APFS | `/Volumes/ssd(mac)2`, APFS volume `disk7s2`, container `disk7`, physical store `disk6s2`, physical SSD `disk6` | 512,000,000,000 bytes total; 334,075,715,584 bytes available (311.1 GiB) | Recommended; writable, no quota/reserve reported, no image layer |
| Product workspace partition | `/Volumes/Asif ssd (mac)`, Journaled HFS+, `disk6s3` on the same SSD | 511,731,351,552 bytes total; approximately 370,635,018,240 available (345.2 GiB) | Keep product Git here; not a direct Chromium checkout filesystem |
| Internal data volume | `/System/Volumes/Data`, APFS `disk3s1`, container `disk3`, physical store `disk0s2` | About 69.9 billion bytes available (65.1 GiB), shared container | Insufficient for the proposed budget |
| Mounted simulator image | Read-only APFS iOS 26.5 Simulator, `disk5s1`, backed by an Apple-managed `.dmg` | About 0.43 GiB container free | Not a build candidate; leave unchanged |
| Illustrative `/Volumes/TrinolBuild` | Not mounted or present | No independent capacity | Blocked; do not mistake its internal `/Volumes` parent for build storage |

The two external partitions share one physical SSD but have separate free-space
budgets. Their free space cannot simply be added for a checkout on one partition.
The internal recovery/boot APFS containers were inventoried and are not candidates.
`hdiutil info -plist` showed only the mounted simulator image. Root-level inspection
of the two external volumes found no `.dmg`, `.sparsebundle`, `.sparseimage` or
`.asif` entries. This was scoped inspection, not a search of every user directory.

Hardware revalidated: native Apple M3 Pro arm64, 11 CPU cores, 18 GiB RAM;
macOS 26.6.2; Xcode 26.5 and macOS SDK 26.5. Chromium tools remain absent from PATH.
No throughput, sustained build performance, image mount/write, or hardware-health
benchmark was performed.

## Options compared

### A — use the existing native external APFS volume (recommended)

Use a new directory on `/Volumes/ssd(mac)2`. No migration, new volume, partition
change, erasure, filesystem conversion or disk image is needed. The proposed
parent passes read/search/write access checks and contains no conflicting checkout
at the proposed destination. Its full checkout path has no whitespace.

This avoids the extra image layer and offers the clearest physical-capacity
accounting. The APFS volume contains other projects, so its free space is shared
and can shrink. Do not remove or relocate those projects. The same USB SSD is
also hosting product Git; it is not an independent backup. Use a reliable cable,
keep the SSD connected, stop builds before ejecting, and retain pushed product
changes plus reproducible source/tool pins. A public push does not back up local
build profiles or uncommitted upstream changes.

If this APFS volume becomes unavailable, establishing a new native APFS partition
on the HFS+ allocation could involve migration/repartitioning and risk existing
data. That is outside this phase; do not erase or convert the drive incidentally.

### B — APFS sparse image on HFS+ (feasible fallback, not recommended now)

Apple's [disk-image guide](https://support.apple.com/guide/disk-utility/create-a-disk-image-dskutl11888/mac)
supports APFS images and growable image formats. On this host, `hdiutil create
-help` and `man hdiutil` explicitly list APFS, SPARSEBUNDLE/UDSB and single-file
SPARSE/UDSP. Sparsebundle stores data in bands; the older sparseimage format uses
one growing file. Apple's current guide also mentions ASIF, but the inspected
local hdiutil help does not list it; do not assume a usable CLI workflow for ASIF
without separate validation. Fixed read/write or compressed/read-only images are
poor choices for this growable build-storage use case.

A conservative fallback proposal is an APFS sparsebundle with a **275 GiB virtual
ceiling**, stored outside product Git at the explicitly illustrative path
`/Volumes/Asif ssd (mac)/TrinolBuild.sparsebundle`, mounted as
`/Volumes/TrinolBuild`. The backing path may contain spaces; the mounted checkout
path must not. The current HFS+ backing has about **345.2 GiB physically available**.
If the bundle grew to roughly 275 GiB, about 70 GiB would remain before additional
host consumption and image overhead. Retain at least 50 GiB safety headroom and
recheck both layers. Virtual capacity is a ceiling, not allocated or reserved
physical space. No image has been created or its mounted usable capacity measured.

An image adds filesystem and image-layer work; metadata-heavy Chromium operations
may be slower, but no overhead percentage is claimed. Use one predictable mount
point, check it is actually mounted, and verify APFS plus image-to-backing-device
mapping on each use. Do not create directories beneath an absent mount, accept an
unexpected numbered mount suffix, or build through an unresolved image mapping.

Backing exhaustion or accidental USB disconnection can interrupt writes and damage
the image. Backups must capture a coherent, cleanly detached image; APFS snapshots
inside it do not protect against loss/corruption of the host file or SSD. Recovery
may require repair or rebuilding from pins. Image compaction/recovery are separate
operations, not guaranteed ways to reclaim space. No such operations were run.

Creating even a growable image requires explicit approval. With Option A available,
there is no current reason to take this extra operational burden.

### C — internal APFS (blocked)

About 65.1 GiB is available. The 200 GiB minimum environment budget plus 50 GiB
headroom requires at least 250 GiB currently available. Do not delete caches,
applications or user files to meet that target. Internal storage is not proposed
for the checkout, generated output or a large separate Git cache.

## Recommended exact layout and budget

These are proposed paths, not active configuration or directories created here:

```text
/Volumes/ssd(mac)2/TrinolBuild/
  depot_tools/
  chromium/                 # fetch root
    src/                    # actual Chromium source checkout
      out/TrinolDev/        # generated build output
  test-profile/             # disposable browser profile
  logs/
```

Explicit preflight/fetch destination: **`/Volumes/ssd(mac)2/TrinolBuild/chromium`**.
Actual source directory after a future fetch:
**`/Volumes/ssd(mac)2/TrinolBuild/chromium/src`**.
Always quote these paths in shell commands because parentheses are shell syntax.

- Observed physical and accessible capacity: **311.1 GiB**.
- Safety headroom policy: **50 GiB**, not an actual filesystem reservation.
- Remaining maximum planning budget after that margin: **261.1 GiB**.
- Initial environment allocation target: **200 GiB**, leaving about 61.1 GiB
  additional flexibility above that target while preserving the safety margin.
- Expected real consumption: **not measured**; source history, dependencies,
  symbols, output configurations and caches can exceed the initial budget.
  Monitor during checkout/build and stop before consuming the safety margin.

There is no virtual image capacity in the recommended approach. No disk quota was
set, and other projects can consume this free space. A second full build or
large history/cache growth needs another capacity review.

## Preflight utility

Run from the product repository:

```bash
python3 scripts/check_chromium_build_storage.py '/Volumes/ssd(mac)2/TrinolBuild/chromium'
```

The utility checks native macOS arm64, supplied and resolved paths, existing parent,
mount presence, ordinary permissions, fresh-destination conflicts, actual APFS,
accessible free blocks, APFS container free space and quotas. It maps physical
stores via native metadata, distinguishes mounted images using hdiutil, and caps
image capacity by backing free space. Nested, shadow-backed, ambiguous or unknown
image mappings fail closed. It neither mounts nor writes to proposed storage.

A native physical-device inventory is necessary: this Apple SSD reports
`VirtualOrPhysical=Unknown` through `diskutil info`, but is explicitly physical in
`diskutil list physical`. Tests cover that observed metadata case.

Exit codes: 0 = storage pass with warnings, 1 = blocked, 2 = CLI usage error.
The policy floor is 200 GiB plus 50 GiB headroom; flags can increase these limits.
A pass does not prove a write or allocation will succeed, reserve capacity,
validate the toolchain, or authorize a download. Capacity and mount state can
change immediately after inspection. Re-run before a future provisioning step.

## Future source and build preparation

The [upstream workflow](upstream-workflow.md) now separates Phase 1B downloads
from Phase 1C compilation. Current official Chromium
[macOS instructions](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
and [Apple Silicon guidance](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_arm64.md)
were reviewed. Native arm64, APFS and a space-free checkout remain the baseline.

`upstream/manifest.json` records phase `1a`; exact Chromium and depot_tools
revisions remain null. No SHA was invented and no reproducible checkout is claimed.
Phase 1B must select/verify exact revisions, check the pinned mac_sdk.gni against
installed Xcode/SDK, install depot_tools and sync source/dependencies only after
explicit instruction. Retain the proposed component-build GN template and start
with four jobs in Phase 1C; these settings are not benchmarked on this host.

## Validation and delivery evidence

Executed locally:

- `python3 -m unittest discover -s tests -v` (initial 40), then
  `python3 -m unittest discover -s tests -q`: **43 tests passed** after adding
  physical-inventory and empty-df regression cases. Covers paths,
  symlinks, future parents, permission failures, mount absence, conflicting work,
  capacity/headroom thresholds, APFS quotas, native physical mapping, image
  backing limits, unsupported images, malformed metadata and command timeouts.
- `python3 scripts/validate_foundation.py`: **passed**, including links in 12
  Markdown files, phase `1a`, null revision pins and empty customization lists.
- `python3 -m compileall -q scripts tests`: **passed**; bytecode is ignored.
- `bash -n scripts/audit_macos.sh`: **passed** (the script itself is unchanged).
- `bash scripts/audit_macos.sh`: **executed successfully** for fresh host evidence.
- `git diff --check`: **passed**.
- Live preflight on the recommended external APFS path: **exit 0**, 311.1 GiB
  effective available, 261.1 GiB after headroom; no directories created.
- Live internal APFS candidate: **exit 1**, insufficient capacity (65.1 GiB).
- Live `/Volumes/TrinolBuild/chromium`: **exit 1**, expected mount absent.
- Live HFS+ workspace candidate: **exit 1**, whitespace in path; native filesystem
  inspection independently confirms HFS+ and unit tests cover filesystem rejection.

Staged file-type and known credential-pattern scan passed (no generated build
files, private-key files or known token patterns found); diffs were manually
reviewed. This limited static scan is not proof against every possible secret.
Hosted tests use mocked disk metadata and temporary paths, not this user's disks.

Tooling commit `20b859f45b1ca5f3db10fe13515d8d2de1b1ae09` —
`feat: add read-only Chromium storage preflight` — was pushed successfully to
`origin/main`. Remote main returned the identical SHA after the push. Its
[GitHub Actions run](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39106414599)
passed, including all 43 tests on Linux. The owner
identity remains `Asif Zman <138548302+asif4762@users.noreply.github.com>`;
`gh api user` confirmed `A-K-M-Asifuzzaman`, ID `138548302`.

The findings/documentation are a separate commit,
`docs: record Phase 1A storage readiness and phase gates`. Its hash and final
GitHub Actions result are reported in the final chat after execution. Commands
used for delivery include targeted `git add`, `git diff`/`git diff --cached`,
`git diff --cached --check`, `git commit`, `git fetch origin`,
`git merge-base --is-ancestor origin/main HEAD`, `git push origin main`,
`git rev-parse HEAD` and `git ls-remote origin refs/heads/main`. No force push or
history rewriting was used.
No Chromium compilation, launch, runtime, UI, signing or notarization validation
was performed. No real image was created/mounted for tests; image tests use fixtures.

## Exact next action

Approve the proposed native APFS layout and explicitly authorize Phase 1B. Then
re-run the preflight, confirm the same mounted volume and free-space budget, create
only the dedicated `TrinolBuild` directories on that APFS volume, and perform a
small write/remove permission probe within the newly created directory before any
large download. Directory creation and that probe are future actions, not work
performed under Phase 1A's read-only storage authorization.

No disk image, erasure, reformat, repartition, migration or global setting change
is needed for the recommended route. Stop for architect review here.
