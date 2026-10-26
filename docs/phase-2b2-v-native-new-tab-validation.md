# Phase 2B2-V — native Orbit New Tab validation

Status: **PARTIAL — offline tooling prepared; native acceptance NOT TESTED.**
Reviewed starting product: `46b40aff898e231ed518a101cc2495c94c75509c`.
On 2026-10-26 the operator replied **“Not available; prepare offline tooling
only.”** No native browser launched, disposable profile created or one-use claim
consumed. No Chromium source, compiled artifact, GN argument or old marker changed.
No browser compilation, GN generation or full native test link was performed.

## Host checkpoint and offline identities

The earlier fixed three-sample survey, at five-second intervals, returned pressure
**2/2/2**, failing the existing native-launch requirement **1**. Swap stayed at
6,195 MiB used of 7,168 MiB. Internal/external available capacity was
65,806,143,488 / 265,611,005,952 bytes (61.3 / 247.4 GiB). Host was Darwin arm64;
the process inventory found no compiled Chromium/build process. Sandbox-denied
sysctl/ps attempts were not treated as valid health evidence; the successful
read-only host calls supplied these readings. Memory was not subsequently
resampled to seek a passing value. This checkpoint does not establish the cause
of pressure or replace fresh full APFS/memory/process checks before any launch.

The complete three-patch/two-overlay applied source verification passes, with
no undeclared tracked/nonignored additions. Chromium remains 155.0.8059.85 at
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`; depot_tools remains
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`. DEPS remains
`23ef1ed90785da130901961e4f4179b4fc10adac957eee5622d7e67fe4b82ec5`.
The new gate was exercised read-only against all **25 historical records** and
**seven artifact paths**, plus the exact observer's invalid-PID self-check. It
created neither claim nor review guard. This is offline integrity evidence, not
a native-launch preflight PASS or a loaded-library observation.

| Identity | Verified SHA-256 |
| --- | --- |
| Source customization object | `041b497f44285a8e2708f8f20de0a9adede7555eb5c38bcd4363ace2d4ce147d` |
| Launcher | `62fa3b0be1ef7404d53911c5b28777da7ce441483b00b6271f4a4da494501fae` |
| libchrome_dll.dylib | `1ae9d063141a0dedd309cde33fb5312ac7ca2caa3697c759b25e90043581d527` |
| Framework and app resources.pak | `31e7050a1e730ab9720a9c03f309e9affa943c5eeba887d5490a79cbd984ed5e` |
| Framework and app English locale.pak | `8fb0e6cf49da6023c917062d142b0e37814a86f01a930e5564b280133a7ff72c` |
| args.gn | `cabeadd749736e664c312aca9303a57edd103c34fcc39d66d782128c4f44c1ab` |
| Read-only WindowServer observer | `3f328dc3cfb4ad60109ce8c2d68a62c66ba6470763da2b5e2a99c4511a819b29` |

Paths remain beneath `/Volumes/ssd(mac)2/TrinolBuild`. Framework packs use
`chromium/src/out/TrinolDev/Chromium Framework.framework/Versions/155.0.8059.85/Resources/`
and the application's corresponding Contents/Frameworks copy, not a presumed
out/resources.pak. Expected APFS UUID is
`47F505A1-126A-4EC6-8DB6-135813AA6111`; fresh physical-mount validation remains
required. The observer is `logs/phase2b1v-audit-2qxmjhtz/window-info`.

## Exact one-use gate and lifecycle

`scripts/phase2b2v_runtime.py` extends the existing supervisor without a force or
ignore-marker option. Only the new mode can review these exact source/artifact
identities alongside the immutable 2B1-V claim, old active PENDING_REVIEW guard,
R4/R5/R6 archives, prior 2B1 evidence and completed 2B1-V evidence/visual review.
Missing/changed files, unsafe paths and symlink escapes fail closed. The original
`scripts/phase2b1v_runtime.py` and all its digest constants remain unchanged.
The approved build root is exact; a copied tree at another path is refused.

The shared build/runtime lock remains exclusive. The supervisor repeats full
applied-source/executable verification under it, checks all compiled-app processes,
rejects active compiler/build processes, requires normal pressure and existing
storage thresholds, then creates a new private empty profile/Crashpad directory.
Profile owner/mode, direct-root prefix, empty contents and Crashpad path are
validated. Supported `BREAKPAD_DUMP_LOCATION` isolation and existing security/GPU
defaults remain intact. Immediately before claiming it rechecks processes,
artifacts, historical records and the observer.

Exclusive/fsynced creation of
`logs/TrinolLifecycle.phase2b2v-authorization.json` precedes the separate active
`logs/TrinolLifecycle.phase2b2v-review.json` and Popen. Neither old record is
renamed, replaced or deleted. A crash or failed launch after claiming still
consumes this one use; any new claim/guard blocks all older/default launch modes.
Lifecycle PASS retains the new review guard as PENDING_REVIEW. There is no retry.
An operator flag records a separately obtained human confirmation; it cannot
prove physical presence, so the assistant must obtain that confirmation first.

The fixed session is **360 seconds plus 30-second exit grace**, blank workload;
mixed legacy flags, alternate duration/workload and missing operator are denied.
Launch starts with about:blank so Command+T routing must be demonstrated. Direct
child ownership, PID/start/executable identity, monotonic supervision, real exit
code, helper inventories, observation gaps, U-state handling and evidence-writer
flush retain the tested supervisor behavior. No termination signal is added.
Normal Quit is targeted to NSRunningApplication for the owned identity; app/bundle
selection is forbidden. Final health is written privately, including memory,
UUID, internal/external headroom and compiled processes. Final artifact/history
changes or remaining processes invalidate PASS and retain the claim/guard.

## Capture and six-minute acceptance protocol

The screenshot tool chooses the claim by the recorded phase and checks matching
run authorization, PID/start/executable, profile, owned window, exact library
digest and its lsof mapping. It checks the complete compiled-app inventory for
another browser before/after capture. It never selects or activates an app.
PNG dimensions/hash and identity metadata are recorded privately with
`state_validation: PENDING_INSPECTION`; image content still needs human inspection.
An ambiguous owned window requires its explicit verified WindowServer ID.

Do not execute the prepared mode until fresh operator confirmation and full
preflight pass. The planned session prioritizes routing and genuine omnibox
focus; optional checks remain NOT TESTED if time is insufficient:

| Fixed time budget | Operator state and evidence |
| --- | --- |
| 0–60 s | Command+T; inspect actual committed route via native page information/DevTools if needed, logo/heading/title/favicon; confirm hands-off dark state, capture and inspect |
| 60–160 s | Tab to search button, capture focus; real click, confirm native omnibox focus, capture; type harmless query and verify configured provider; return; keyboard activation if feasible |
| 160–250 s | History and Appearance links; use Chromium's own theme mode for one confirmed light capture, without global macOS changes |
| 250–320 s | Narrow/zoom, focus order and incognito exclusion if safely feasible; record omitted accessibility/security cases independently |
| 320–360 s | Stop interaction, confirm readiness for scheduled normal Quit; no deadline extension |
| 360–390 s | Supervisor requests native Quit and records actual exit, helpers, watchdog/dumps, continuity and writer flush |

For every image: request one precise state, await operator confirmation, verify
owned PID/window, capture, inspect the resulting image, then acknowledge before
the operator changes state. Neither a filename nor source routing proves the
live state. Mojo Boolean acceptance, native focus change and search/navigation
outcome must be recorded separately. No injected focus or relaxed gesture/origin/
profile checks are permitted. One clean session does not resolve the R3 defect.

## Acceptance matrix — actual current results

| Check | Result / evidence |
| --- | --- |
| Offline applied source, tool pins, artifacts, historical records and observer | PASS offline |
| Fresh operator presence | BLOCKED: explicitly unavailable |
| Normal-memory native launch gate | FAIL at earlier checkpoint: 2/2/2 |
| Fresh APFS identity/full launch preflight | NOT TESTED for a native session |
| One-use claim/profile/browser PID and loaded library | NOT CREATED / NOT TESTED |
| Command+T actual route and bundled-resource live load | NOT TESTED |
| Native Orbit logo, heading, title/favicon, dark/light appearance | NOT TESTED |
| Real click/keyboard Mojo focus and native omnibox/provider outcome | NOT TESTED |
| History/Appearance links and honest unavailable-shortcuts state | NOT TESTED live; source inspected |
| Keyboard order/names/focus/Escape, zoom and narrow layout | NOT TESTED |
| Reduced motion, high contrast, screen reader | NOT TESTED |
| Live CSP/network, PageInfo, HTTPS, incognito/cross-profile | NOT TESTED; production source contract unchanged |
| Enterprise, extension and remote-provider overrides | NOT TESTED; separate fixtures remain necessary |
| Native screenshots and associated hashes | NONE; review directory contains instructions only |
| Native Quit acceptance, actual child exit, watchdog/dumps/helper cleanup | NOT TESTED in this phase |

Production CSP remains self/chrome://resources without a WebUI-test exception.
The existing argument-free Mojo handler retains its normal-profile, owning-browser,
origin, visibility and user-activation checks. This source inspection is not live
security certification. No core interaction or native appearance is accepted yet.

## Offline tests, delivery and next action

Synthetic tests cover exact history/artifact identity, pins/contracts, observer,
profile/Crashpad isolation, symlink refusal, process denial, fixed bounds, missing
operator, mixed flags, permanent claims, separate retained guards, final integrity
failure and screenshot PID reuse/extra-browser/finished-session denial. Existing
supervisor tests retain real-exit classification, bounded observations, writer
failures, U-state handling and no unrelated termination coverage.

Actual lightweight results: **282 Python tests PASS**, **four prototype model
tests PASS**, foundation validation (31 Markdown files), Python compileall, audit
shell syntax and Git whitespace checks PASS. Delivery commit/remote/Actions
evidence accompanies the phase delivery. Native tests remain distinct: four New Tab
browser cases compiled but NOT EXECUTED; four Mocha cases compiled/type-checked
but NOT EXECUTED; four earlier color cases NOT EXECUTED. No enormous native test
binary is linked for this task.

Next action is a separately requested memory/preflight check followed by fresh
operator confirmation and the single exact-build session if every gate passes.
Do not automatically resample memory, consume authorization or start another
phase. Recommend native acceptance before selecting any subsequent UI milestone;
sidebar, workspaces, command palette, AI and Phase 2B3 remain unauthorized.

**PHASE 2B2-V PARTIAL — AWAITING ARCHITECT REVIEW**
