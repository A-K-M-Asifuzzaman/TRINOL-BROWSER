# Reviewed phase gates

| Phase | Deliverable | Exit evidence |
| --- | --- | --- |
| 0 — approved | Environment audit, architecture, small product repository, GitHub workflow | Foundation validation, owner verification and confirmed push; explicit review before proceeding |
| 1A — approved | Read-only storage inventory, preflight utility/tests, build preparation documentation | Verified candidate filesystem/backing capacity, tests and GitHub delivery; no downloads or storage changes |
| 1B — approved | Approved storage path, exact verified source/tool pins, Chromium checkout and toolchain | Successful dependency sync, matching SHAs, SDK compatibility and checkout evidence |
| 1C — partial; responsive browsing verified, bounded shutdown gate incomplete | Unmodified native macOS arm64 compilation and launch | Successful build, dedicated-profile launch and baseline checks with exact commands/results |
| 2A — approved UI foundation | Independently authorized design system, runnable interactive prototype, screenshots and native integration contract | Prototype checks and captures; native checkout and R6 marker preserved |
| 2B1 — PARTIAL; corrected visual validation blocked by operator availability | Native Orbit colors and exact patched-tree verification | Corrected artifact verified; C++ test object compiled; test execution and corrected runtime visual checks outstanding |
| 2B2 — proposed; separate approval required | Next selected native slice | First validate corrected baseline colors with separate runtime authorization; review resources/layout before expanding |
| 3 — proposed | Native UI redesign and trusted internal surfaces | Browser/WebUI, accessibility, keyboard and functional regression checks |
| Later — proposed | Workspaces, split view, command palette, optional AI/sync | Separate designs, privacy/security tests and measured performance |
| Distribution — gated | Supported releases across approved platforms | Signed packages/updates, rollback, license review, security response and release testing |

The overall Phase 1 exit criterion remains a verified native Chromium build and
launch. Phase 1B has verified source/tool pins, dependency sync and hooks; see the
[checkout report](phase-1b-checkout-report.md). It does not satisfy the build/launch
criterion. Phase 1C-R completed the full native target at one job with exit 0;
the arm64 executable and version metadata are verified. Following a confirmed
host restart, R3 verified responsive native GUI, local HTML/CSS/JavaScript,
navigation, HTTPS and core internal pages with a new isolated test profile.
R3 native Quit triggered a teardown watchdog and dump. R4 symbolicated the
browser-main GPU destruction wait, but did not establish its underlying cause.
R5 archived the reviewed R4 marker and captured accepted native Quit, browser
exit 0 and complete helper cleanup in one blank session. A 36.95-second startup
observation gap invalidated that trial; no second session was eligible. The
R5 failure marker was subsequently archived by R6. See the
[R5 lifecycle report](phase-1c-r5-lifecycle-validation.md) for the event timeline,
monitoring limits and next engineering action. No Chromium rebuild or source
patch was performed. Repeatable valid bounded shutdown remains unverified.
These are historical Phase 1C findings; no shutdown-root-cause fix is claimed.
Phase 2B1 now separately authorizes the first native color slice. AI integration,
signing and distribution remain unimplemented.

R6 improved the maximum observation gap to 2.423 seconds with acknowledged final
evidence flush. Its owned browser exited 0, but GUI app selection apparently
started an unexpected second instance. This failed the isolation gate; the
operator used normal Quit and all compiled-app processes were then absent. The
conditional browsing trial was not eligible. The R6 failure marker blocks more
launches pending review of an observation route that cannot launch an app. See
the [R6 report](phase-1c-r6-observation-reliability.md). Phase 1C remains PARTIAL.

Phase 2A explicitly authorizes an independent prototype while Phase 1C remains
PARTIAL. [Trinol Orbit](phase-2a-ui-report.md) supplies original tokens/assets,
working simulated shell interactions, both appearances, 16 captures and a
[source-grounded integration plan](design/native-ui-integration-plan.md). This
does not retire the R6 marker or establish native shutdown/UI acceptance. The
design was approved for the limited Phase 2B1 color slice. See the
[native report](phase-2b1-native-shell-report.md). Its one operator-observed
browsing session captured exit 0, normal Quit, complete helper cleanup and valid
continuity, while exposing a macOS frame-guard error. The correction is kept in
the ordered patch series. No second native launch is permitted. Phase 1C stays
PARTIAL: repeated independent lifecycle evidence and the original GPU teardown
uncertainty remain unresolved. Phase 2B2 is not authorized.

Phase 2B1-V completed offline gate/capture regression coverage and the existing
C++ test-object compilation with 266 actions, exit 0. Its full unit_tests binary
requires 7,100 actions and remains deferred. The operator requested no runtime
while unavailable, so the exact one-use visual authorization remains unconsumed
and no corrected native screenshot/exit event exists. See the
[visual-validation report](phase-2b1-v-native-visual-validation.md). Resume only
with fresh operator availability and revalidated safety/evidence; no Phase 2B2.
