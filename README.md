# TRINOL-BROWSER

Trinol Browser is a planned native Chromium fork by TrinolIT: macOS arm64 first,
then Windows and Linux. It will retain Chromium's browser services while adding
TrinolIT branding and a distinct native interface. Phase 2B1 introduces the first
manifest-bound native toolbar/tab color slice; visual acceptance remains partial.

**Phase 1C is partial; compilation and responsive browsing succeeded:** the
preserved one-job build completed with exit 0. After a host restart, native
Chromium 155.0.8059.85 rendered HTML/CSS/JavaScript, HTTPS and internal pages.
R6 captured native Quit acceptance, browser exit 0, owned helper cleanup and
valid observation continuity, but an unexpected second instance invalidated the
single-instance lifecycle. Operator cleanup removed all compiled-app processes.
Repeatable clean shutdown remains unverified. Phase 2B1 separately authorized
one UI trial, preserving the exact R6 marker in a one-use archive. That browsing
trial exited 0 with helper cleanup and valid continuity. Further native launches
require separate review. See the [R6 report](docs/phase-1c-r6-observation-reliability.md).

**Phase 2B1 native slice is PARTIAL:** the first incremental build succeeded,
and its one bounded native session exposed an incorrect macOS frame eligibility
guard. The source correction compiled successfully; its regression case is tracked
in the [native report](docs/phase-2b1-native-shell-report.md); corrected Orbit appearance
was later observed in the single 2B1-V trial below. No Phase 2B2 is authorized.

**Phase 2B1-V is PARTIAL:** the corrected artifact, previous trial and archives
passed offline verification. The existing C++ test translation unit compiled
successfully (266 actions, exit 0), but the four tests have not executed. The
single corrected-library trial now ran after six normal-memory samples and fresh
operator confirmation. Dark/light surfaces were observed; controlled focus,
security and frame-state coverage remains incomplete. Normal Quit, real exit 0,
helper cleanup and valid continuity passed for this trial. Its authorization is
permanently consumed; preserve the review guard and do not launch again. See the
[validation report](docs/phase-2b1-v-native-visual-validation.md).

**Phase 2A design foundation was approved**, independently authorized
while Phase 1C remains partial. Run `python3 design/prototype/serve.py` and open
[Trinol Orbit](http://127.0.0.1:4173/prototype/). The interactive preview includes
horizontal/vertical tabs, a collapsible sidebar, omnibox suggestions, a command
palette and complete light/dark appearances. All navigation/data is simulated.
See the [UI report](docs/phase-2a-ui-report.md),
[preview instructions](design/prototype/README.md) and
[actual review captures](design/review/README.md).

This repository contains Trinol-owned changes, documentation, configuration
examples and validation. The Chromium checkout, depot_tools and build outputs
belong outside this repository.

- [Phase 1C build and launch report](docs/phase-1c-build-report.md)
- [Phase 1B checkout and toolchain report](docs/phase-1b-checkout-report.md)
- [Phase 1A storage readiness](docs/phase-1a-storage-readiness.md)
- [Phase 0 environment audit](docs/environment-audit.md)
- [Architecture and security boundaries](docs/architecture.md)
- [Fresh-machine setup and upstream maintenance](docs/upstream-workflow.md)
- [Phase gates](docs/roadmap.md)
- [Contributor instructions](AGENTS.md)
- [Security policy](SECURITY.md)
- [Phase 0 delivery record](docs/phase-0-delivery.md)

Validate the foundation with `python3 scripts/validate_foundation.py` and
`git diff --check`. Run tooling tests with
`python3 -m unittest discover -s tests -v`. On macOS,
`bash scripts/audit_macos.sh` gathers a read-only snapshot; `python3 scripts/check_chromium_build_storage.py /path/to/checkout`
checks a proposed fresh destination without creating it. These checks do not
build or test Chromium. Use `scripts/verify_upstream_checkout.py` with explicit
`--checkout-root` and `--depot-tools` paths to check the recorded source/tool pins.

Repository: https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER
