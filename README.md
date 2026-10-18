# TRINOL-BROWSER

Trinol Browser is a planned native Chromium fork by TrinolIT: macOS arm64 first,
then Windows and Linux. It will retain Chromium's browser services while adding
TrinolIT branding and a distinct native interface. No browser is implemented yet.

**Phase 1B:** Chromium 155.0.8059.85, pinned depot_tools, dependency sync and
hooks are verified on external APFS storage. The environment is ready for review
before Phase 1C (GN generation, build and launch), which requires explicit
instruction. No compiled browser exists yet.

This repository contains Trinol-owned changes, documentation, configuration
examples and validation. The Chromium checkout, depot_tools and build outputs
belong outside this repository.

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
