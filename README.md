# TRINOL-BROWSER

Trinol Browser is a planned native Chromium fork by TrinolIT: macOS arm64 first,
then Windows and Linux. It will retain Chromium's browser services while adding
TrinolIT branding and a distinct native interface. No browser is implemented yet.

**Phase 0:** repository foundation and environment audit. **Build readiness:
blocked** by the available checkout storage. Phase 1 requires explicit review.

This repository contains Trinol-owned changes, documentation, configuration
examples and validation. The Chromium checkout, depot_tools and build outputs
belong outside this repository.

- [Environment audit](docs/environment-audit.md)
- [Architecture and security boundaries](docs/architecture.md)
- [Fresh-machine setup and upstream maintenance](docs/upstream-workflow.md)
- [Phase gates](docs/roadmap.md)
- [Contributor instructions](AGENTS.md)
- [Security policy](SECURITY.md)
- [Phase 0 delivery record](docs/phase-0-delivery.md)

Validate the foundation with `python3 scripts/validate_foundation.py` and
`git diff --check`. On macOS, `bash scripts/audit_macos.sh` gathers a read-only
snapshot. These checks do not build or test Chromium.

Repository: https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER
