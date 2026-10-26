# Phase 2B2 — native Orbit New Tab

Status: **IMPLEMENTED AND COMPILED — NATIVE VISUAL ACCEPTANCE PENDING.**
No native launch is authorized.

## Scope and revision verification

The reviewed product baseline is `6fde699acd76eef667e8fad4e2da7f04c813b416`.
Authenticated owner: `A-K-M-Asifuzzaman`; preserved Git author:
`Asif Zman <138548302+asif4762@users.noreply.github.com>`. Work is on `main`.
Chromium remains `155.0.8059.85`, commit
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`; depot_tools remains
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`. DEPS SHA-256 remains
`23ef1ed90785da130901961e4f4179b4fc10adac957eee5622d7e67fe4b82ec5`.

The separate external checkout/output is preserved. The APFS volume UUID is
`47F505A1-126A-4EC6-8DB6-135813AA6111`. No source reset, clean, reclone,
full rebuild, GN argument change, security bypass or application rename occurred.
Native execution is outside this phase's authorization.

## Architecture and actual integration points

The implementation reuses the existing trusted generic local New Tab host,
`chrome://new-tab-page-third-party/`, rather than adding a new WebUI factory.
A separate Trinol host would duplicate registration and New Tab recognition.
Reusing the full Google-oriented NewTabPage/Realbox stack would retain substantially
more privileged service and contextual-search dependencies than this entry point
needs. The selected generic host already has resource, theme and normal desktop
New Tab integration in this exact source revision.

The ordered third patch changes:

- `chrome/browser/search/search.cc`: desktop local NTP fallback and Google-local
  choice use the generic local host. Configured non-Google providers with valid
  cryptographic remote New Tab URLs retain upstream behavior. Off-the-record
  routing still returns the upstream incognito path instead of the normal page.
- `chrome/browser/resources/new_tab_page_third_party/`: actual bundled
  HTML/TypeScript/CSS/SVG and its existing GN/GRIT resource map. The page title is
  localized; the document favicon references the approved Orbit SVG.
- `chrome/browser/ui/webui/new_tab_page_third_party/`: existing profile-scoped
  controller, strict data source, typed Mojo and theme observer.
- `chrome/browser/chrome_browser_interface_binders_webui_parts_desktop.cc`:
  remove the unused MostVisited factory from this host's binder registry.
- `chrome/chrome_repack_locales.gni` and `tools/gritsettings/resource_ids.spec`:
  wire the separate Trinol string catalogue into desktop locale repacking.
- `chrome/test/data/webui/BUILD.gn` and its new generic-NTP test directory:
  wire frontend tests and native browser test cases through upstream infrastructure.

`ChromeContentBrowserClient::BrowserURLHandlerCreated` retains enterprise
New Tab overrides first, extension overrides next and search rewrites afterward.
Those policy/extension handlers were inspected and left unchanged. The existing
incognito controller and guest-unavailable behavior remain separate; the generic
controller rejects off-the-record profiles. No general chrome:// factory is
replaced. Existing New Tab commands, tab-strip creation, omnibox/history services
and profile models remain upstream. Windows/Linux source paths are retained, but
only macOS arm64 compilation is attempted in this phase.

## Search and actual browser services

The prominent entry is a semantic button, not a simulated search box. The existing
`PageHandler` gains only `FocusOmnibox() => (bool focused)`. Browser-side checks
require a normal non-guest owning profile, matching browser context and browser
profile, this trusted committed origin, visible WebContents, live primary frame,
transient user activation and an existing browser window. It calls the existing
`BrowserWindow::SetFocusToLocationBar(true)`. No query, URL, command identifier,
filesystem path or other profile target crosses this interface. Chromium owns
search-provider preferences, suggestions/privacy controls, URL parsing, encoding
and actual navigation. A denied/disconnected operation announces localized help;
initialization does not steal focus. Full Realbox is deferred.

Top Sites was investigated: `TopSitesImpl::AddPrepopulatedPages` can supplement
empty real history with built-in entries. Correct product filtering, dismissal
and pinned-site semantics need separate reviewed work. No MostVisited/TopSites
or favicon-data endpoint is exposed here. The localized unavailable state and
working native History link are honest; no fictional or prepopulated sites ship.
The Appearance link opens Chromium's actual settings page.

## Orbit design, theme and accessibility

The approved original mark/favicon and orbit motif accompany the localized
“Where to next?” heading. System typography, asymmetric whitespace, graphite/slate,
blue focus accents and restrained cyan match the approved direction. The page does
not simulate tabs, toolbar, sidebar, sync, profile or workspace state.

Bundled CSS implements both approved palettes, viewport-based spacing, narrow
layout, wrapping, logical properties, keyboard focus outlines, a live status region,
high-contrast system colors and reduced motion. There are no perpetual animations
or downloaded fonts. Forced-colors declarations override inline custom-theme
variables. The existing ThemeService and WebContents ColorProvider observation
refresh mode and custom-theme text/background; custom theme images come only from
Chromium's profile theme source. Theme identifiers use URLSearchParams encoding. Google-oriented NTP wallpaper,
promo and account modules are not part of this page; browser ThemeService images
are supported at source level.
No cross-profile theme or history query is introduced.

These are implemented properties, not native visual, screen-reader, contrast or
zoom certification. The renderer/native-tab favicon and virtual New Tab title,
focus ordering, theme image geometry and custom theme contrast need the future
exact-build trial.

## Security and localization

Bundled resources use a trusted WebUI with ChromeSend disabled. CSP explicitly
sets default/connect/child/frame/object/base/form to none; script and style sources
are self plus chrome://resources, images self plus chrome://theme. No remote
script, wildcard, unsafe-eval, backend, cloud API, arbitrary command, query-bearing
IPC, credentials or unrestricted filesystem binding is added. The binder registry
exposes this host's page factory only; ordinary web pages receive no new interface.
Sandbox, TLS, site isolation and permission rules are unchanged.

Owned overlays `trinol/new_tab/BUILD.gn` and `strings.grd` create a separate actual
GRIT catalogue and generated header. Nine messages cover title, heading, search,
hint, sites, empty state, links and failure status. Text direction/language use
WebUI's standard localization values; the keyboard shortcut comes from the native
accelerator formatter. Supported locale packages are generated with English
fallback. Translations are not supplied; this is localized infrastructure, not a
claim of translated copy in every language.

## Reproducible customization and preservation

`0001-orbit-baseline-native-colors.patch` and
`0002-orbit-macos-native-frame.patch` retain their original bytes and ordering.
`0003-orbit-native-new-tab.patch` and two owned overlays extend the exact contract
to 23 source outputs (old two plus 19 patch outputs and two overlays). All file
hashes and regular Git modes are checked against prospective scratch-index output
and actual source. The new suffix transition verifies an immutable prior product
commit, unchanged pin/prefix, exact old source state, prospective full outputs and
exclusive new overlays before applying only the suffix. It never resets unrelated
changes. Synthetic tests cover refusal paths and partial-work preservation.

The first post-application check found a global user Git ignore rule `test` hiding
three new test files. Source bytes were present; no output was deleted. Verification
now explicitly inventories declared ignored additions and still checks their modes
and hashes. Tampered/missing additions remain rejected. The global ignore config
was not changed. Subsequent narrow source refinements retain the before manifest,
patch, changed source bytes and exact delta outside product Git.

Private evidence is under
`/Volumes/ssd(mac)2/TrinolBuild/logs/phase2b2-new-tab-ijr0v8d9`.
Before source application, the exact old source outputs, original manifest,
complete Chromium.app and 521 root libraries/paks/GN files were copied and
hash-verified. The root-file copy contains 935,652,074 bytes in addition to the app
bundle. The original corrected library hash is
`f4f64292a78c8758c2be665177dfc39103432105ecc4deacd9dfc4baec619afe`.
Five protected authorization/guard/archive hashes remain checked against baseline.
Raw logs, binaries, profiles and historical evidence are not committed.

## GN and build evidence

GN generation is necessary for the new strings and test targets. The build gate
permits it only for the exact Phase 2B2 customization with explicit manifest
permission and one job. Existing storage/mount, exclusive lock, memory/swap,
observation-gap and no-overlap guards remain unchanged. Stable historical pressure
2 is allowed by the existing one-job compilation guard; this does not relax the
separate normal-memory native-launch gate.

The first GN attempt failed test visibility before compilation. Setting the
production TypeScript target composite (the pinned upstream pattern) supplied
its declaration interface to the test target. The next GN generation exited 0:
35,963 targets from 5,001 GN files, 15.851 seconds. Existing arguments retain
mac/arm64, component=true, debug=false, symbol_level=1, official=false,
use_remoteexec=false, use_siso=true and use_lld=true. args.gn was preserved.

The guarded chrome dry run exited 0: 252 steps, 10 C++ translation units.
This is a bounded incremental graph, not a full browser build. Its private record
is `logs/phase2b2-dry-u5wl15ab`. The focused production/test TypeScript, Mojo-TS and
GRIT target build exited 0 with 14 steps (`phase2b2-frontend-gstese9m`). Swap
remained 3,587,304,325 bytes through GN/dry/frontend observations, with no growth;
external available space was about 247 GiB and internal about 65 GiB.

The affected C++ GN header/dependency check passed. The first guarded native
build was interrupted conservatively when shared GRIT ID regeneration exposed
34,971 scheduled downstream edges rather than the 252-step dry graph. It exited
1 after an owned-group SIGINT: 71 resource actions completed, zero failed build
actions and no native C++ compilation. The stop is recorded separately from a
compiler failure. A post-generation dry run reported 402 steps and the same ten
C++ files; scheduled edges are not completed compilation actions.

An offline reconstruction of the pinned and proposed ID tables found two shifted
tail ranges (shared toolbar and reserved placeholder). The new catalogue was moved
after the reserved tail. Repeating the exact upstream assignment tool in private
files established **zero changed existing ranges**, including the placeholder;
the nine new string IDs begin at 59030. This prevents unnecessary existing resource
ID changes. The generated header also follows the pinned empty-prepend convention
so no Windows-only atlres.h include is emitted.

To measure actual native work without speculative restat expansion, the 222 direct
shared-ID GRIT consumers already in chrome's dependency closure were isolated.
Their dry run reported 157 steps and zero native compile commands. Its first
execution stopped at the new page's CSS linter: eight actions completed, one
failed, no native compilation. The CSS was then formatted with Chromium's installed
stylelint configuration; strict linting was retained.

A proposed production script-CSP addition for the WebUI test loader was rejected
by automatic approval review as an avoidable security-boundary expansion; it was
not applied. The safer test-only fixture aliases the actual compiled production
modules beneath Chromium's existing WebUI test data source. Production CSP remains
self plus chrome://resources, without the test origin. Native tests do not require
a production CSP exception. Actual test execution remains unverified.

The corrected full page resource/test-TypeScript/GRIT build exited 0 with nine
steps, including CSS lint and the small generated resource-map object. The
resource-only shared-ID refresh then exited 0 with 216 steps and no native browser
compilation (`phase2b2-resources-apaah7mo`). All resource IDs used by previous
catalogues remain stable. The final GN generation exited 0 (11.811 seconds), and
both production and browser-test source_set header/dependency checks passed.

Before the next dry run, separate read-only final-status and process checks
confirmed resource-build completion and no remaining build/browser process. An
automatic review rejected a combined check/start call because of potential overlap;
no command ran from that rejected call. The subsequent separate checks established
safe completion without bypassing the exclusive-runner gate.

After resource regeneration, the fresh chrome dry run exited 0 with **250 steps
and ten C++ translation units**, `phase2b2-dry-2pyk_bkn`. With existing ID ranges
stable and the resource-only work completed separately, the remaining native graph
is within the reviewed one-job envelope. The guarded native chrome build then **completed 494 actions, exit 0, zero failed
actions**, with 14 completed C++ actions (the reviewed sources plus generated Mojo
and launcher translation units). The additional work was resource repacking and
bundle copies; this was an incremental build. Evidence:
`logs/phase1c-build-3by1eue0`. No native application or test binary was launched.

The 35 guard samples recorded pressure 2, maximum swap growth 315.44 MiB, maximum
sample interval 38.824 seconds, minimum external availability 247.356 GiB and
minimum internal availability 64.945 GiB. All remained inside the unchanged
one-job limits. The Siso post-build profiling summary warned about inconsistent
weighted time totals in siso_metrics.json. The warning is retained; weighted
performance statistics are not relied upon. The guarded process exit 0, explicit
494-step success/zero-failure log and verified packaged artifacts establish the
compilation result independently of that timing summary.

The final artifact audit verifies native arm64 launcher/library format, the bundle
version, all six packaged Orbit resource IDs, all nine English locale messages and
the application's copies of both packs against the framework outputs. It also
rehashes all 521 archived root files, inventories the prior bundle's 347 regular
files and verifies all five protected markers. The preserved old locale has no
new Trinol catalogue. Existing GN argument bytes and the original corrected
library remain preserved. The patch container's final blank context line was
avoided by ordering its independent file diffs; prospective output/source hashes
are unchanged and the complete applied contract was reverified.

| Exact artifact | SHA-256 |
| --- | --- |
| Launcher | `62fa3b0be1ef7404d53911c5b28777da7ce441483b00b6271f4a4da494501fae` |
| New libchrome_dll.dylib | `1ae9d063141a0dedd309cde33fb5312ac7ca2caa3697c759b25e90043581d527` |
| Application resources.pak | `31e7050a1e730ab9720a9c03f309e9affa943c5eeba887d5490a79cbd984ed5e` |
| Application English locale.pak | `8fb0e6cf49da6023c917062d142b0e37814a86f01a930e5564b280133a7ff72c` |
| Preserved args.gn | `cabeadd749736e664c312aca9303a57edd103c34fcc39d66d782128c4f44c1ab` |

The source customization object hash is
`041b497f44285a8e2708f8f20de0a9adede7555eb5c38bcd4363ace2d4ce147d`
(SHA-256 of Python json.dumps(customization, sort_keys=True), UTF-8).
The private final-artifact-audit.json records physical paths and the prior bundle
inventory digest. On the later continuation, current idle pressure was 2 with
about 5.7 GiB swap, 62 GiB internal and 247 GiB external available; no browser/build
process remained. This is not a normal-memory native-launch gate PASS.

The focused new native test-object dry run reports 638 generated-input steps and
two C++ commands. Its guarded object compilation is recorded below;
no full browser_tests binary or runtime result is implied. Its first compilation
processed the 638-step graph and failed in the new fixture on five obsolete
Browser::profile() calls: this pinned PlatformBrowserTest exposes a
BrowserWindowInterface. The fixture now uses the pinned chrome_test_utils profile
and active-WebContents helpers. An exact verified source refinement changed only
orbit_browsertest.cc; every production source record and compiled app artifact
remained unchanged. The guarded retry **passed: five steps, exit 0, zero failed actions and no swap
growth**, `logs/phase2b2-object-zd_t3feg`. The four native case bodies and existing
client wrapper now compile. The initial generated-input graph also compiled and
linted the WebUI test resources, including the new four Mocha cases. This proves
compilation/type/lint checks, not assertion results or native behavior. The
browser_tests binary was not linked or executed. A final read-only chrome dry run
then exited 0 with **zero steps** (`logs/phase2b2-dry-63203pbh`), confirming that
production outputs remain current after the test-only correction.

## Tests and limitations

| Check | Actual result |
| --- | --- |
| Product Python tests | PASS, 253 tests |
| Dependency-free prototype model | PASS, 4 tests; prototype only |
| Foundation, Python syntax, audit shell syntax, whitespace | PASS |
| Exact applied source/tool pins and full output contract | PASS |
| Production and new test TypeScript via actual Chromium targets | PASS, compiled/type-checked |
| New GRIT catalogue via actual Chromium target | PASS, including final packaged English messages |
| Incremental native chrome target | PASS, 494 actions, exit 0 |
| Native packaged artifacts and historical preservation | PASS |
| Four new WebUI Mocha cases | Added/type-checked; NOT EXECUTED |
| Four new native browser cases | Focused object compiled, five-step retry exit 0; NOT EXECUTED |
| Policy/extension override, guest, cross-profile runtime | NOT TESTED; source ordering inspected |
| Native New Tab appearance/focus/search/keyboard/favicon/zoom | NOT TESTED; launch unauthorized |
| Four prior Orbit color mixer tests | NOT EXECUTED; previous object compile retained |

Static product checks cover localization wiring, narrow privilege gates, CSP,
actual native links, no fake search/data, theme/encoding/accessibility rules and
approved asset bytes. They are source-contract checks, not proof of live Chromium
behavior. Native tests cover client delegation/theme behavior, local routing and
incognito exclusion, configured provider remote NTP, and denial without a user
gesture. Policy and extension override runtime regressions remain explicit gaps.

The original R3 GPU destruction wait/root-cause uncertainty, incomplete repeated
bounded lifecycle evidence and 2B1-V controlled visual gaps remain open. One prior
valid shutdown does not establish repeatability or a fix. The consumed 2B1-V
marker, active guard and R4/R5/R6 archives are retained. No historical result is
reclassified by this UI work.

## Future exact-build acceptance plan (not launch authorization)

After successful compilation, separately review a one-use authorization tied to
the exact new product/source contract and launcher/library/resource hashes. Require
fresh operator presence at an unlocked Mac; normal memory; verified APFS/host,
free space, no browser/build overlap; retained historical markers and safe explicit
review handling. Use a fresh disposable profile, isolated Crashpad and the existing
bounded supervisor with actual process identity/start/exit evidence. Bind only the
verified read-only WindowServer observer; never select/launch the app through GUI
binding. Do not reuse retired authorization flags.

Within one bounded session, capture the actual New Tab dark/light states without
racing operator changes; verify Cmd-T/tab-strip opening, title/favicon, initial
native omnibox focus, page-button focus, search with the configured engine,
History/Appearance links, keyboard focus return, narrow/zoom/reduced-motion/high
contrast and theme updates where feasible. Policy/extension overrides and separate
profile configurations need their own controlled regression coverage rather than
unchecked profile changes during the one-session visual trial. Record PASS/FAIL/
NOT TESTED and perform normal supervised Quit with real exit status and helpers
gone. Stop after any failed gate; no second launch, marker clearing or forced
success. Sidebar, workspaces and command palette remain outside this phase.

## Delivery

Tooling milestone: `409572ebf299c223106d2802634cedfe1a9aadde`,
`feat(build): support verified customization suffix transitions`, pushed to main;
exact-commit GitHub Actions run 40236281482 succeeded. The feature delivery uses `feat(ui): integrate native Orbit New Tab WebUI`.
Its immutable commit hash, confirmed origin/main and exact-commit Actions result
are supplied in the final delivery response after pushing; this report does not
claim foundation CI executes Chromium or the native tests.
