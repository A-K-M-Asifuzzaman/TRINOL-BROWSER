# TRINOL-BROWSER

Trinol Browser is a planned native Chromium fork by TrinolIT: macOS arm64 first,
then Windows and Linux. It will retain Chromium's browser services while adding
TrinolIT branding and a distinct native interface. No browser is implemented yet.

**Phase 1A:** storage readiness tooling and audit are complete. An existing
external APFS volume passes the read-only preflight. Phase 1B (checkout/toolchain)
and Phase 1C (build/launch) require explicit instruction. No build exists yet.

This repository contains Trinol-owned changes, documentation, configuration
examples and validation. The Chromium checkout, depot_tools and build outputs
belong outside this repository.

- [Phase 1A storage readiness](docs/phase-1a-storage-readiness.md)
- [Phase 0 environment audit](docs/environment-audit.md)
- [Architecture and security boundaries](docs/architecture.md)
- [Fresh-machine setup and upstream maintenance](docs/upstream-workflow.md)
- [Phase gates](docs/roadmap.md)
- [Contributor instructions](AGENTS.md)
- [Security policy](SECURITY.md)
- [Phase 0 delivery record](docs/phase-0-delivery.md)

Validate the foundation with `python3 scripts/validate_foundation.py` and
`git diff --check`. Run storage tests with
`python3 -m unittest discover -s tests -v`. On macOS,
`bash scripts/audit_macos.sh` gathers a read-only snapshot; `python3 scripts/check_chromium_build_storage.py /path/to/checkout`
checks a proposed fresh destination without creating it. These checks do not
build or test Chromium.

Repository: https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER
