# Reviewed phase gates

| Phase | Deliverable | Exit evidence |
| --- | --- | --- |
| 0 — approved | Environment audit, architecture, small product repository, GitHub workflow | Foundation validation, owner verification and confirmed push; explicit review before proceeding |
| 1A — approved | Read-only storage inventory, preflight utility/tests, build preparation documentation | Verified candidate filesystem/backing capacity, tests and GitHub delivery; no downloads or storage changes |
| 1B — approved | Approved storage path, exact verified source/tool pins, Chromium checkout and toolchain | Successful dependency sync, matching SHAs, SDK compatibility and checkout evidence |
| 1C — partial; responsive browsing verified, shutdown failed | Unmodified native macOS arm64 compilation and launch | Successful build, dedicated-profile launch and baseline checks with exact commands/results |
| 2 — proposed | Trinol branding and packaging identity | Reproducible patches, resource/build tests and launch checks |
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
R4's initial blank-session supervisor failed on early native Quit refusal;
later menu cleanup left no processes or dump, but no browser exit status was
captured. The corrected lifecycle harness passes offline tests and remains
blocked from further native trials pending review. See the
[R4 investigation](phase-1c-r4-shutdown-investigation.md) for stacks, competing
shutdown-budget hypotheses, limitations and the next discriminating test.
No Chromium rebuild or source patch was performed.
Phase 2 still requires new explicit instruction after architect review.
No product UI, AI integration, signing setup or distribution is implemented.
