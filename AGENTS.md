# Trinol Browser engineering instructions

## Scope and architecture

Trinol Browser is a native Chromium fork, not an Electron application or a web
browser mockup. Preserve Blink, V8, content, network, sandbox and existing browser
services. Integrate Trinol-specific C++/Views UI and trusted WebUI through small,
reviewable patches and overlays. macOS arm64 is the first target; keep Windows
and Linux portability in mind. Read docs/architecture.md before implementation.

Phases 0, 1A and 1B are approved. Phase 1C authorizes GN generation, native
compilation of the existing pinned Chromium checkout, artifact inspection and
browser smoke tests using only the dedicated external test profile. Preserve
source/tool pins and incremental outputs. Keep at least 50 GiB physical free
space; stop compilation at 60 GiB, on mount changes or unsafe memory pressure.
Initial Phase 1C started with four jobs and reduced to two. Phase 1C-R authorizes
recovery at one job after idle memory diagnostics, with sustained-deterioration
guards and an exclusive runner lock. Preserve existing GN files and outputs.
Keep Siso's
cache external and remote execution disabled. No disk images, reformatting,
repartitioning, global configuration changes, security bypasses or Trinol source
customizations. Do not begin Phase 2 without explicit instruction. Distinguish
compilation, executable launch and GUI/functional evidence.

Phase 1C-R6 consumed its one reviewed R5 recovery. Preserve both R4/R5 marker
archives and the active R6 failure marker. The owned browser exited 0 with valid
observation continuity, but GUI app selection apparently launched a second
compiled-app instance and invalidated isolation. Operator normal Quit removed
it; its exit status is unknown. No more native launch is authorized by R6.
Do not reuse either recovery option or clear future failure markers automatically.
Before a separately reviewed retry, establish GUI observation that cannot launch
an app; do not use macOS cua.getApp as a read-only binding during a trial. Keep
unexpected processes separate from owned helpers and request operator cleanup.

Phase 2A is explicitly authorized independently of the partial Phase 1C gate.
It covers the standalone design/prototype, original assets/tokens, visual and
interaction tests, source-grounded native planning and safe patch infrastructure.
It does not authorize applying patches to Chromium, native launch, clearing the
R6 marker, rebuilding, or proceeding to the next native integration phase.
Visual tests use a separate disposable testing browser, never the compiled app.

Phase 2B1 explicitly authorizes the first native Orbit baseline color patch,
exact manifest-bound source verification and a guarded one-job incremental build.
It also permits ONE operator-observed native UI session after successful build,
normal memory/storage, fresh present/unlocked confirmation and exact R6 evidence
review. Only `--reviewed-r6-ui-smoke --operator-present` can consume that recovery;
preserve the R6 marker bytes in `TrinolLifecycle.r6-ui-reviewed.json` atomically.
The archive blocks every later launch, including after a successful session.
Never use app selection/activation as observation. No Phase 2B2 is authorized.
The 2B1 session is now consumed: PID 20381 exited 0 with normal Quit, helper
cleanup and valid continuity. The exact original R6 bytes are archived. Its UI
trial exposed a frame eligibility error; the corrected palette compiled but has
not been launched. Preserve the archive; no further native session is authorized.

Phase 2B1-V separately authorizes ONE corrected-library visual trial through
`--phase-2b1v-visual --operator-present --window-observer /exact/reviewed/utility`.
Require the exact previous successful 2B1 evidence and unchanged historical
archives, corrected library/launcher/GN/source identities, tested nonlaunching
WindowServer observation, normal host health and fresh present/unlocked operator.
Under the shared lock, exclusively create the permanent
`TrinolLifecycle.phase2b1v-authorization.json` claim before the active guard.
Never delete the claim or reuse any older retry flag. Retain the final active
guard for visual review even after lifecycle PASS; a later run requires a new
reviewed authorization. No Phase 2B2 or additional UI feature is authorized.
Phase 2B1-V is now consumed: after six normal-memory samples and fresh operator
confirmation, PID 88337 ran for 540 seconds and exited 0 after accepted native
Quit, with helper cleanup, no extra browser, no watchdog/dump and valid continuity.
Corrected dark/light surface colors were observed; controlled focus/hover/security
and frame validation remain PARTIAL. Preserve its permanent claim and active
PENDING_REVIEW guard unchanged; the separate local visual review is PARTIAL.
No additional native launch is authorized by any existing flag. Four C++ tests
remain unexecuted. No Phase 2B2 is authorized.

Phase 2B2 is now explicitly authorized for a real Orbit New Tab WebUI, exact
suffix/overlay transitions, focused tests and resource-guarded one-job incremental
compilation. Preserve both color patches, source/tool pins, GN arguments, prior
artifacts, the consumed 2B1-V claim and all review/historical markers. Justified
incremental GN generation may retain the exact existing arguments. Inspect the
build graph and stop for architectural review on unexpectedly broad work. This
phase does NOT authorize any native browser launch: future runtime validation
requires a separately reviewed one-use authorization and fresh operator presence.
Do not reuse or clear old gates. Keep prior regression gaps explicit. No sidebar,
workspaces, command palette, AI, app rename or next phase is authorized.

Phase 2B2-V authorizes one exact-build New Tab acceptance session only through
`--phase-2b2v-new-tab --operator-present --seconds 360 --grace-seconds 30`, with
the reviewed WindowServer observer and fresh explicit operator confirmation.
The operator is currently unavailable and requested offline tooling only: do not
launch, create a profile or consume authorization until fresh confirmation and
all prelaunch gates pass. Keep the old 2B1-V claim/guard and archives immutable;
use separate permanent 2B2-V claim/review paths under the shared lock. Preserve
the new claim and final review guard after every outcome. Never reuse flags or
retry a failed/consumed session. No browser rebuild or Phase 2B3 is authorized.

## Quality and tests

Use Chromium style and ownership/lifetime conventions in C++, its WebUI patterns
for TypeScript, and standard-library Python for small repository tools where
practical. Avoid broad refactors, unexplained dependencies and duplicated browser
services. Keep customizations modular, accessible, localizable and reviewable.

Review `git diff` and staged diffs before every commit. Run relevant available
checks before pushing functional changes. Foundation checks are
`python3 scripts/validate_foundation.py`, `bash -n scripts/audit_macos.sh` and
`git diff --check`. Run `python3 -m unittest discover -s tests -v` for storage
preflight changes and syntax-check Python sources. Use the preflight with an
explicit checkout path before future downloads; it must check actual APFS and
physical backing capacity, including disk images. Later phases require affected
unit/browser/WebUI tests and real launch verification; document commands, failures and skipped checks.
Never claim foundation CI proves a Chromium build or production readiness.

## Security

Never commit API keys, credentials, private keys, certificates, passwords, browser
profiles or environment secrets. Keep local configuration and generated files
ignored. Inspect staged content; .gitignore is not a security scanner. Do not
weaken sandboxing, site isolation, TLS verification or permission prompts.
Use minimal validated IPC interfaces for privileged WebUI. Do not grant webpage
or future AI content unrestricted browser, filesystem or credential access.
Preserve incognito boundaries and use dedicated test profiles. See SECURITY.md.

## GitHub workflow (persistent requirement)

- Repository: https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER.git
- Primary branch: `main`; use the owner's locally authenticated GitHub account.
- Verify `gh api user` matches `A-K-M-Asifuzzaman`, and verify the configured Git
  author belongs to that account. Never fabricate identity or print tokens.
- Preserve existing files and history. Inspect status, log and remotes before
  work. Fetch and inspect remote changes before pushing; integrate safely.
- Use Conventional Commits: feat, fix, refactor, perf, docs, test, build, ci, chore.
- Commit each coherent verified unit; push completed commits to `origin/main`
  regularly and at phase completion. Use several focused commits for large work.
- Never force-push, rewrite shared main, remove unrelated work, or make empty
  commits solely to increase frequency. Stop on destructive history conflicts.
- If authentication, identity, network, tests or conflicts block delivery,
  preserve local work and report the exact blocker. Do not claim push success
  without Git confirmation; verify remote main matches the delivered commit.

## Upstream maintenance

Never vendor the Chromium source checkout or depot_tools into this repository.
Keep upstream and generated outputs outside it, on a suitable APFS volume with
a space-free checkout path on macOS. Pin exact Chromium and depot_tools commits
before Phase 1 build claims; keep upstream DEPS dependencies synchronized.
Maintain ordered patches in patches/series and declared overlay mappings.
Never overwrite an upstream checkout's local edits automatically. Reapply and
validate changes against each reviewed upstream revision. Track Chromium security
releases promptly; distribution requires an update and rollback process.
Keep third-party notices and license obligations intact. See
docs/upstream-workflow.md for the reproduction contract.

## Reporting

Report outcome, changed files, checks and limitations, author verification,
branch, commit hashes/messages, Git commands, remote push evidence and blockers.
Report pins, effective GN arguments, build exit status, resource observations,
artifact checks and individual browser test results for Phase 1C. Stop for
architect review before Phase 2; incomplete builds or launches are partial.
Never describe a proposed feature as shipped or an unrun test as passing.

## graphify

When the user types `/graphify`, read and use the installed graphify skill before
any other work. Original location: `~/.Codex/skills/graphify/SKILL.md`; if absent,
resolve the installed skill catalog (currently `~/.agents/skills/graphify/SKILL.md`).
