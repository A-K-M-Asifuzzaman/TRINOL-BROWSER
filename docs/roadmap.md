# Reviewed phase gates

| Phase | Deliverable | Exit evidence |
| --- | --- | --- |
| 0 — approved | Environment audit, architecture, small product repository, GitHub workflow | Foundation validation, owner verification and confirmed push; explicit review before proceeding |
| 1A — approved | Read-only storage inventory, preflight utility/tests, build preparation documentation | Verified candidate filesystem/backing capacity, tests and GitHub delivery; no downloads or storage changes |
| 1B — approved | Approved storage path, exact verified source/tool pins, Chromium checkout and toolchain | Successful dependency sync, matching SHAs, SDK compatibility and checkout evidence |
| 1C — partial; responsive browsing verified, bounded shutdown gate incomplete | Unmodified native macOS arm64 compilation and launch | Successful build, dedicated-profile launch and baseline checks with exact commands/results |
| 2A — UI foundation complete, awaiting design review | Independently authorized design system, runnable interactive prototype, screenshots and native integration contract | Prototype checks and captures; native checkout and R6 marker preserved |
| 2B — proposed; separate approval required | Selected native branding/UI implementation | Reviewed patches/overlays, resource/build tests and safe launch gate |
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
Native integration still requires new explicit instruction after architect review.
No native product UI, AI integration, signing setup or distribution is implemented.

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
next native integration phase awaits design selection and separate approval.
