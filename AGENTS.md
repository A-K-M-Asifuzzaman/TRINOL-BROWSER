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

Phase 1C-R5 consumed its one reviewed retry. Preserve the archived R4 marker
and the active R5 failure marker. Actual browser exit 0 was captured, but a startup
observation gap invalidated the trial. No further native launch is authorized by
R5. Review monitoring/evidence-write latency before a separately authorized retry;
do not reuse the R4 recovery option or clear future failure markers automatically.

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
