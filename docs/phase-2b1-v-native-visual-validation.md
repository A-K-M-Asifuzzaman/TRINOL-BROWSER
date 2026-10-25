# Phase 2B1-V — corrected native palette validation

Updated: 2026-10-26, Asia/Dhaka. Verdict: **PARTIAL**. The single corrected-library
trial ran after normal-memory diagnostics and fresh operator confirmation.
Corrected dark/light surfaces were observed; controlled interaction/state coverage
remains incomplete. Normal Quit, actual exit 0 and helper cleanup **PASS for this
single trial**. The authorization is permanently consumed and the review guard
is retained. No further native launch or Phase 2B2 is authorized.

## Completed single trial — current result

Reviewed product: `d8bda1d8b60de3f18722b842dc1f69e0b49955a0`, clean main and
zero remote divergence. Owner A-K-M-Asifuzzaman was verified; existing author
Asif Zman <138548302+asif4762@users.noreply.github.com> was preserved.
The earlier blocked checkpoints below remain historical evidence.

### Memory diagnosis and launch gates

Six read-only samples at 0/10/20/30/40/50 seconds all reported pressure **1**.
Swap stayed at **3,597.12 MiB** (3,771,853,701 bytes as parsed by the existing
runner); swap-outs did not increase and swap-ins increased by four pages.
The 18 GiB host had 65–294 MiB literally free, about 3.6–4.0 GiB inactive,
and 6.2–6.7 GiB occupied by the compressor during the survey. The separate
memory_pressure query reported 45–46% system-wide free; this is not the same
quantity as vm_stat's literal free-page count. Large individual resident users
included Codex/ChatGPT and Brave renderers (around 1 GiB each at peaks), plus
Python and Cursor. RSS is not a unique physical-footprint total. Compression and
multiple application workloads show resource demand, but the previous pressure-2
snapshot lacks enough VM/process detail to establish its specific cause or blame
one process. No application was killed, no threshold changed, and no restart was
performed. No automatic repeated diagnosis was used to force a passing result.

Internal/external physical free capacity was **65.48/248.72 GiB**; approved
writable APFS UUID `47F505A1-126A-4EC6-8DB6-135813AA6111` matched. No compiled
Chromium or build process was present. The source/tool pins, complete declared
two-patch state, arm64 executable/version, corrected library/launcher/GN hashes,
prior 2B1 evidence, R4/R5/R6 archives, absent claim/guard and exact read-only
observer passed. The existing supervisor repeated these checks before launch.
No GN generation, compile, source patch, library replacement or security bypass
occurred. The operator freshly confirmed all presence/interaction/cleanup
conditions after the survey; previous confirmations were not substituted.

### Exact owned run and screenshots

Private evidence: `logs/phase2b1v-visual-xg70p26t` under the approved build root.
PID **88337**, start **Mon Oct 26 01:31:37 2026 (Asia/Dhaka)**, exact compiled
executable, fresh profile and supported BREAKPAD_DUMP_LOCATION isolation were
recorded by the existing Popen supervisor. Command mode was
`--phase-2b1v-visual --operator-present --seconds 540 --grace-seconds 30 --workload browsing`,
with explicit approved build root, UUID and the observer resolved from the
previous authorization record. Its digest remains
`3f328dc3cfb4ad60109ce8c2d68a62c66ba6470763da2b5e2a99c4511a819b29`.
The permanent one-use claim was created before launch. No second compiled-app
instance was observed. Kernel PID/start/executable identity, disposable profile,
expected mapped library SHA and owned WindowServer ID **35203** were checked for
each successful capture. Bounds remained **1036 × 777**; no narrow resize PASS is
claimed. One capture safely refused ambiguous owned window IDs; specifying the
original verified window ID captured the same browser, without another launch.

Five genuine native images were captured. Only the inspected initial local
fixture image is public, unchanged byte-for-byte as
[dark-local-fixture.png](../design/review/native-2b1-validated/dark-local-fixture.png),
SHA-256 `13957d4d461bf26a2571f886f61e14d88e15a2cc1788ecfc9b6890c31a7a805a`.
[Sanitized metadata](../design/review/native-2b1-validated/capture-metadata.json)
binds it to the run and identity. The other captures contain unrelated browsing
or Settings states and stay private. Their filenames express intended captures,
not verified results: dark-omnibox-focused was a New Tab/apps panel;
dark-https-focus was Settings in Light mode; light-local-fixture showed an
unrelated page. None is relabeled as a passing fixture/focus/security screenshot.
No account credentials, raw logs, profiles, dumps or native binaries enter Git.

### Palette and functional observations

The corrected `f4f64292a78c8758c2be665177dfc39103432105ecc4deacd9dfc4baec619afe`
library was mapped in the owned process. Initial dark local HTML/CSS/JavaScript
rendered correctly; the active tab, inactive label, toolbar and traffic lights
were visible. Settings later showed Chromium's own **Mode: Light**; no global
macOS appearance change was requested. Raw captures carry the monitor ICC profile.
Read-only color conversion for analysis (original PNGs unchanged) gave dominant
sRGB toolbar/active-tab **#191E26**, close to dark target **#191E27**; light toolbar
**#F2F5FA** and omnibox **#E7ECF3** matched their recipes. Initial dark frame output
was **#12151B**. A light titlebar region was **#CDD0D5**, rather than the flat
frame token. These are pixel correlations, not internal ColorProvider values.

Pinned `browser_native_widget_mac.mm:110–120,1107–1140` contains a glass-frame
path that reads active/inactive frame colors and applies opacity (horizontal
light 0.55/dark 0.80); `browser_frame_view_mac.mm:501–509` skips solid painting
when glass-eligible. This establishes a possible compositing path, not proof
that this runtime took it. Glass eligibility/key contents were not inspected.
No new source defect or patch is established by the titlebar pixel difference.
The evidence supports corrected surface appearance, but full frame/state visual
acceptance remains PARTIAL pending architect review.

| Check | Current result | Evidence/limit |
| --- | --- | --- |
| Responsive native startup and core rendering | PASS | Initial fixture; later native tabs/pages and Settings changed |
| Version / exact mapped library | PASS | Bundle/arm64 verification and capture mapping/digest |
| Local HTML/CSS/JavaScript | PASS | Green heading, DOM PASS text and changed tab title |
| Dark baseline surfaces and active/inactive labels | PASS, observed | Safe native capture; ICC-aware correlation |
| Light toolbar/omnibox recipes | PASS, observed | Private native captures; ICC-aware correlation |
| Exact native frame/color-key eligibility | NOT TESTED directly | Frame output differs/compositing possible; no internal-key read |
| Tab creation/switching and Settings | PASS, observed | Multiple new tabs/active pages and Settings capture |
| Focus/hover/multiselection/pressed states | NOT TESTED | Requested stable states were not captured |
| Reload/back/forward and controlled HTTPS navigation | NOT independently verified | Operator reported success; subsequent captures did not retain requested state |
| Site-security/PageInfo | NOT TESTED | No controlled security UI capture |
| Traffic lights/basic geometry | PASS, observed | Native controls visible without overlap at one size; no click/drag certification |
| Narrow resize, incognito, custom theme/high contrast exclusions | NOT TESTED | No safe controlled state evidence |
| Normal Quit / actual exit / helper cleanup | PASS for this trial | Accepted native Quit, Popen exit 0, inventories empty |

The operator reported the requested tab/navigation actions worked, but capture
coordination did not reliably retain the requested states. A later free-text
request for the exact fixture lines received no reply before completion.
This limits those checks; it does not establish an implementation failure.
A narrowly filtered read-only History query was locked during runtime and could
not be opened after exit, so it supplies no additional navigation evidence.

### Shutdown, resource result and retained authorization

Native Quit requested at **540.091404 s**, accepted **540.242932 s**; real browser
exit **0** at **540.753202 s**; helpers exited **541.255497 s**. Supervisor exit
was **0**. No unexpected/remaining compiled processes, watchdog message or
isolated dump. Max poll gap **0.410046 s**, max observation gap **2.360681 s**.
All **520/520** writes acknowledged; zero drops/unacknowledged/error, final flush
true and writer exited. Transient U-state observations ended (longest observed
span **4.347 s**); none persisted. No termination signal or operator force-quit
was needed. The historical R3 watchdog cause remains unresolved; this is one
clean lifecycle, not an indefinite stability claim or automatic Phase 1C closure.

Runtime pressure values were 1/2, with no swap growth. Final pressure **2**, swap
unchanged; internal available **70,364,876,800** bytes, external **266,440,171,520**
bytes and expected UUID unchanged. Library and historical archive digests stayed
unchanged; compiled processes were absent. Claim and active review guard remain.
Raw supervisor `visual_validation: PENDING_REVIEW` and its retained marker are
unchanged; separate private `visual-review.json` records this PARTIAL review.
No retry or marker clearing is authorized. Four native C++ cases remain **NOT
RUN** despite the prior successful translation-unit compilation; the expensive
unit_tests executable was not built.

For this completed-trial delivery, **235 Python tests and four Node model tests
PASS**, with foundation validation, Python compileall, audit shell syntax and
Git whitespace checks. These do not replace native C++ execution. This delivery
includes the new native screenshot and actual lifecycle evidence. No scripts or
patches changed.

## Present-operator attempt — memory gate stopped prelaunch

On 2026-10-26 the operator explicitly confirmed physical presence at the unlocked
Mac, native-window observation/interaction and availability throughout the test.
Product main and origin/main matched `072f367ef8502602970f647a01c42f2c5401de2f`
after fetch, with zero divergence. Authenticated owner A-K-M-Asifuzzaman and the
existing author Asif Zman <138548302+asif4762@users.noreply.github.com> were verified.

Private evidence: `logs/phase2b1v-final-preflight-b4cs_7o8/preflight.json` under
`/Volumes/ssd(mac)2/TrinolBuild`. Native Darwin arm64, external writable APFS UUID
`47F505A1-126A-4EC6-8DB6-135813AA6111`, physical backing capacity, external free
267,054,903,296 bytes and internal free 70,300,844,032 bytes passed. The shared
build/runtime lock was acquired. Exact source/tool pins, DEPS, complete declared
two-patch source bytes/modes/inventory and arm64 bundle/executable identity passed.
The existing authorization review validated corrected-library, launcher and GN
hashes; all prior 2B1 evidence and R4/R5/R6 archives; absent claim/active guard;
and the exact recorded read-only observer digest and invalid-PID self-check.
No compiled-app or compiler/build process was found.

**BLOCKED — NORMAL IDLE MEMORY PRESSURE REQUIRED — AUTHORIZATION UNCONSUMED.**
Memory pressure was **2**, required **1**; swap was 3,780,242,309 bytes. The attempt
stopped at that failed gate. No retry, launch, profile, Crashpad directory, claim,
active guard, capture, rebuild or marker reset followed. This preflight record is
not a runtime result. Historical source/build evidence remains intact.

Native window identity/mapped library, dark/light palette, tabs/toolbar/focus,
geometry, browsing/security, new exit status, helper cleanup, watchdog and dumps
are all **NOT TESTED**. There is no new PID or exit code. C++ translation-unit
compilation remains historical PASS; four native C++ executions remain NOT RUN.
For this checkpoint, 235 Python tests and four Node model tests passed, as did
foundation, Python/shell syntax and whitespace checks. These are offline checks.
The next action is to reduce unrelated workload, then obtain fresh operator
availability and rerun all required checks before consuming the same single
trial. No automatic retry or Phase 2B2 is authorized by this blocked result.

## FINAL request — operator gate stopped the trial

**BLOCKED — OPERATOR UNAVAILABLE — AUTHORIZATION UNCONSUMED**

For the separately requested FINAL trial, the fresh operator response was:
“Not available; leave authorization unconsumed.” The current trial stopped at
that mandatory gate. No prelaunch health/source/artifact checks were rerun, no
browser or build was started, and no claim, guard, profile, Crashpad directory or
screenshot was created by this attempt. Prior offline hashes and host-health
measurements below are historical; they are not new verification of the current
external build environment. Existing evidence and markers were not modified.

Product main and origin/main matched the requested baseline
`54d777fe7287d7897690578dbeb97f820f1772c1` after fetch, with zero divergence.
Authenticated owner and the existing Git author were verified. This checkpoint
changes documentation and manifest reporting only. Native PID/library mapping,
dark/light appearance, tab/toolbar/focus, geometry, browsing/security, actual exit
status, helper cleanup, watchdog and dump observations are all **NOT TESTED** for
this attempt. No new exit code exists. The historical C++ translation-unit
compilation remains PASS; the four test executions remain NOT RUN. No expensive
unit_tests build or Phase 2B2 work is authorized here.

For this documentation checkpoint, 235 Python tests and four Node model tests
passed again, along with foundation validation, Python syntax, audit shell
syntax and Git whitespace checks. These offline checks do not establish a
native visual or lifecycle result.

The next action requires a fresh explicit present/unlocked operator confirmation,
then all prescribed prelaunch checks, before the same unconsumed one-use trial.
Phase 2B1 remains PARTIAL; this FINAL trial is BLOCKED, not visually accepted.

## Exact baseline and offline evidence

Reviewed product commit: `78406695aff1ad397aedf42a1e5fef28213ef095`, clean main,
no remote divergence after fetch. Authenticated owner A-K-M-Asifuzzaman, ID
138548302; existing author Asif Zman <138548302+asif4762@users.noreply.github.com>.
Chromium 155.0.8059.85 remains at
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`, depot_tools
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`. Both ordered product patches and
all authorized source bytes/modes/inventory passed exact verification.

Corrected library SHA-256:
`f4f64292a78c8758c2be665177dfc39103432105ecc4deacd9dfc4baec619afe`.
Launcher SHA-256:
`62fa3b0be1ef7404d53911c5b28777da7ce441483b00b6271f4a4da494501fae`.
GN args SHA-256:
`cabeadd749736e664c312aca9303a57edd103c34fcc39d66d782128c4f44c1ab`.
Effective GN values are unchanged: mac/arm64, component=true, debug=false,
symbol_level=1, official=false, siso=true, lld=true, remoteexec=false. The real
framework reexports @rpath/libchrome_dll.dylib; runtime mapping must be checked
separately. External APFS UUID remains
`47F505A1-126A-4EC6-8DB6-135813AA6111`. Initial pressure 1, swap 4,333,890,437
bytes, zero compiled-app processes/builds. Physical capacity checks passed.
Private audit: `logs/phase2b1v-audit-2qxmjhtz` under the build root.

The original 2B1 trial's exact launch/result/events/samples/health/browser log,
timing records, fixture and three captures are hash-bound by the new gate.
It recorded PID 20381, actual exit 0, accepted native Quit, empty helper and
unexpected-process inventories, no watchdog/dump, 266 acknowledged evidence
writes and valid continuity. It tested library `6c9a937b...`, not the corrected
library above. The corrected library's mtime is after that session ended.
The immutable R6 archive remains SHA-256
`ccc213f095ea07c8dc20fa086a00d87ce4297645a29a5b82bafbd6debdea5655`;
R4/R5 archives are independently checked and preserved.

## Narrow authorization and GUI inspection

`--phase-2b1v-visual` authorizes only this exact previous session, source/tool
pins, two-patch contract and corrected library. It requires fresh operator
presence/unlocked confirmation, approved UUID, normal memory/storage, no build
or compiled browser, and the exact previously tested nonlaunching WindowServer
utility. Arbitrary revisions, changed evidence, changed library/launcher/GN,
unknown observer binaries, symlinks and old retry-flag combinations are refused.

Under the shared exclusive build/runtime lock, a permanent exclusive claim at
`logs/TrinolLifecycle.phase2b1v-authorization.json` is fsynced before creating
the active guard and starting Popen. All launch modes reject an existing claim.
A crash between claim and active-guard creation still consumes authorization.
Original archives are never replaced/deleted. Final lifecycle results replace
the active guard atomically and retain it for visual review, even after exit 0.
A clean lifecycle is not automatically a visual PASS. No second launch is allowed.

The exact prior WindowServer binary is reused from private local evidence, with
SHA-256 `3f328dc3cfb4ad60109ce8c2d68a62c66ba6470763da2b5e2a99c4511a819b29`.
It calls CGWindowListCopyWindowInfo, filters the specified PID/layer and returns
only IDs/bounds. It does not select, activate or launch an application. Its invalid-
PID self-check returns 2 without output. The new capture script verifies
PID/start/kernel executable/disposable profile, expected mapped library with
lsof, exact digest and owned WindowServer ID. It rechecks process identity
immediately before and after window-targeted screencapture, validates PNG
headers/dimensions and records capture hashes. No app-selection API is used.
Operator-directed interaction remains the UI control method. No global macOS
appearance setting, sandbox/TLS/signing protection or personal profile is changed.

## Existing C++ tests: actual build versus execution

All four `TrinolOrbitColorMixerTest` cases were reviewed in the pinned source.
The guarded runner now permits a fixed `--orbit-test-object` target at one job;
it does not expose arbitrary targets or permit GN regeneration. Its affected
unit tests pass. Actual command:

```sh
python3 scripts/build_chromium_macos.py --build-root '/Volumes/ssd(mac)2/TrinolBuild' --jobs 1 --orbit-test-object
```

The exact object is
`obj/chrome/browser/ui/color/unit_tests/material_tab_strip_color_mixer_unittest.o`.
Build evidence `logs/phase1c-build-xlyu76od`: **exit 0**, **266 actions**, **0
failures**, **0 remaining**, Siso 1m57.60s. Initial/final pressure 1, unchanged
swap; available external 267,018,346,496 bytes, internal 69,797,556,224 bytes.
This proves translation-unit/API compilation, **not execution of four tests**.
The unit_tests executable is absent. Its dry run requires **7,100 actions**,
including **6,046 C++ compilations**; it was not built because that exceeds this
narrow verification scope. The eventual filter is `TrinolOrbitColorMixerTest.*`.
Native test execution remains **NOT RUN**. No full browser rebuild, GN change,
source patch, dependency refetch or pin change was needed for this object build.

## Runtime/acceptance result — not executed

The operator answered: “Not available now; keep runtime untested.” The presence
and unlocked-Mac gate therefore did not pass. No browser launch, native screenshot,
new profile/Crashpad directory, Quit request or new exit code was produced.
The one-use claim and new active guard were **not created**. Existing R4/R5/R6
archives and all prior session evidence remain unchanged. This is an explicit
runtime stop, not a passing visual result. The same authorization cannot be used
until a fresh operator confirmation and complete health/evidence preflight occur.

| Check | 2B1-V result | Direct evidence/limit |
| --- | --- | --- |
| Source/tool revisions and exact two-patch state | PASS | Full source contents/modes/inventory verifier |
| Corrected library/launcher/GN arguments | PASS offline | Exact hashes; no new loaded-process verification |
| Prior 2B1 session and R4/R5/R6 archives | PASS | Immutable hashes and semantic result/writer checks |
| New one-use authorization/capture regression | PASS offline | Synthetic tests; real invalid-PID observer self-check |
| Existing C++ test object/API compilation | PASS | Guarded 266-action build, real exit 0 |
| Four C++ test executions | NOT RUN | 7,100-action full binary deferred |
| Ordinary macOS FrameType | NOT TESTED at runtime | Source maps ordinary windows to kNative; correction remains as previously compiled |
| Orbit mixer eligibility/resulting colors | NOT TESTED | No new process, internal key inspection or pixel sampling |
| Dark native palette | NOT TESTED | Operator unavailable |
| Light native palette | NOT TESTED | Operator unavailable; OS appearance unchanged |
| Tab/toolbar hover, focus, selection, disabled states | NOT TESTED | No corrected-library session |
| Incognito, custom themes, high contrast, accessibility | NOT TESTED | No new runtime coverage |
| Traffic lights, narrow resize, fullscreen, clipping | NOT TESTED | Original geometry unchanged; no new inspection |
| HTML/CSS/JS, tabs, navigation, settings, HTTPS/PageInfo | NOT TESTED | Historical results preserved, not reused as new passes |
| Native window capture and loaded library mapping | NOT TESTED | New capture script tested synthetically; previous mechanism retained |
| New browser exit status | NOT TESTED / null | No Popen browser launch |
| New watchdog/dumps/helper cleanup | NOT TESTED | No new session; final absence of compiled-app processes checked separately |

The [review directory](../design/review/native-2b1-validated/README.md) contains a
status README only. No new PNG was captured; no old image is relabeled as a
corrected palette. Phase 2A prototype and original pre-fix native captures remain
unchanged. Pixel correlation with semantic recipes is deferred; internal
ColorProvider values are not inferred from old pixels.

Source inspection still establishes the historical defect and intended correction:
BrowserNativeWidgetMac::UseCustomFrame returns false for ordinary windows;
BrowserWidget sets kNative; AddTrinolOrbitColorMixer now requires kNative. It is
ordered after the platform mixer and before explicit custom-theme/app suppliers,
which can override later. Orbit excludes those suppliers, custom colors,
grayscale/incognito and accessibility keys. This is source evidence, not runtime
proof that all eligibility fields or resulting colors match the intended state.
No C++ instrumentation, new native patch, color change or browser rebuild was
performed. Both existing patches and their hashes remain unchanged. Final health
recheck: normal memory pressure 1, swap 4,333,890,437 bytes, external available
267,026,010,112 bytes, zero compiled-app processes, no new profile, no active
marker and no 2B1-V claim. The exact test object exists at 143,240 bytes, SHA-256
`d3c49b6bb4e03e14748fcd38aea5d523050d9deb41743d15aafeeae86041c15d`.

## Regression coverage and delivery

**235 Python tests PASS** and **4 Node model tests PASS**. Foundation validation,
Python compileall, audit shell syntax and Git whitespace checks pass. New tests
cover exact prior evidence/archives and corrected-library/launcher/GN identity,
wrong revisions/contracts, observer digest/self-check, symlink escapes, active
failure/duplicate processes, one-use claims, missing operator confirmation,
retained visual-review guard after exit 0, atomic replacement failure, PID reuse,
exit before capture, missing/ambiguous windows, unsafe output labels and invalid
PNG output. No regression test launches a real browser or reads the real screen.
The narrow build-runner test verifies its fixed object target and preserved
outputs; existing lifecycle tests retain genuine exit-status behavior. Captures
are also bound to the exact permanent authorization claim and launch record;
a different supervised session cannot be substituted.

Changes: scripts/phase2b1v_runtime.py, capture_chromium_window_macos.py,
test_chromium_lifecycle_macos.py and build_chromium_macos.py; new
tests/test_phase2b1v_runtime.py plus lifecycle/build tests; this report, prior
native report addendum, roadmap, integration plan, manifest, AGENTS, README and
review status README. No raw logs/dumps, profiles, native binaries or Chromium
checkout files are committed. GitHub CI remains lightweight and does not build
or download Chromium. Exact pushed commits and final Actions conclusion are
reported with the completion response.

## Next engineering action

Keep Phase 2B1 PARTIAL. The single visual authorization is consumed; do not reuse
it or any retired recovery flag. Architect review should assess the corrected
surface evidence, frame compositing uncertainty, incomplete controlled states
and unexecuted native C++ tests. Any additional native trial requires a separately
reviewed authorization and capture/interaction protocol that retains the requested
state. Preserve the claim, review guard, profiles and raw local evidence. Review
the native test-executable cost separately. Phase 2B2 remains unauthorized.

## GitHub milestone evidence

| Commit | Verified change | Exact-commit Actions |
| --- | --- | --- |
| `d5f407b97a3f4009462711adffb82438b50012cc` | Fixed guarded Orbit test-object mode | [40133833461 success](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/40133833461) |
| `3778f60236487fca9f13f188c8cb3ed61d4a8770` | Exact one-use gate, capture binding and regression coverage | [40134045539 success](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/40134045539) |

Both were pushed directly to origin/main after fetch/divergence inspection;
no force push or author change. The final documentation commit, verified remote
HEAD and exact-commit CI conclusion accompany the final report. CI validates
repository tooling; native compilation evidence is the separate local guarded
build above. These milestones established offline coverage only; the later single-trial
results and limitations are recorded in the current section above.
