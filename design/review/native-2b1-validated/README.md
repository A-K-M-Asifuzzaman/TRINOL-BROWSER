# Corrected native Orbit review — not captured

Phase 2B1-V native runtime was not executed: the operator was unavailable and
explicitly directed that runtime remain untested. **No corrected-palette native
screenshots exist in this directory.** No prior image was overwritten or renamed.

Expected version 155.0.8059.85, source
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`, corrected library SHA-256
`f4f64292a78c8758c2be665177dfc39103432105ecc4deacd9dfc4baec619afe`.
These are offline verified identities; this phase has no running browser PID.
Dark/light, tabs/toolbar, focus, native geometry, HTTPS/security and incognito/
theme/accessibility states are all NOT TESTED against that running library.

Prepared capture method: supervised exact executable and fresh profile; kernel
PID/start/executable checks; read-only CGWindowListCopyWindowInfo filtered to that
PID; exact window ID passed to screencapture -x -l; fresh identity checks before
and after capture. No app selection or activation. New capture tooling has only
synthetic coverage; the underlying WindowServer mechanism was tested in 2B1.

The [older native captures](../native-2b1/README.md) show the pre-correction palette.
[Phase 2A images](../README.md) show a standalone prototype. Neither is corrected
native acceptance evidence. See the [validation report](../../../docs/phase-2b1-v-native-visual-validation.md).

The separately requested FINAL trial was also blocked by the fresh response
“Not available; leave authorization unconsumed.” No prelaunch checks, native
launch or capture followed. **BLOCKED — OPERATOR UNAVAILABLE — AUTHORIZATION
UNCONSUMED.** This directory still contains no corrected native screenshot.

On 2026-10-26 the operator was present, but preflight memory pressure 2 failed
the required normal level 1. No native launch or capture followed; the one-use
authorization remains unconsumed. Corrected dark/light and interaction captures
still do not exist. See the current validation report for exact preflight evidence.
