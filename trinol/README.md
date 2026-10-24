# Trinol-owned modules

Reserved for native shell customizations and trusted WebUI. No browser modules
are implemented in Phase 0. Reuse Chromium services and expose only narrow,
validated interfaces to internal pages. GN wiring belongs in reviewed patches.

Phase 2A adds no native stubs here. The independent design prototype and reusable
assets live under design/. Selected components will enter this module tree only
through the reviewed Views/WebUI contract in
[the integration plan](../docs/design/native-ui-integration-plan.md).
