# Trinol Browser architecture — Phase 0 decision

Status: native implementation architecture; Phase 2A now has an independently
authorized standalone design prototype. Phase 2B1 adds a native ColorProvider
slice through reproducible patches; corrected surfaces have been observed, while
full controlled frame/state visual acceptance remains partial.
See [the UI contract](design/native-ui-integration-plan.md) and
[native report](phase-2b1-native-shell-report.md).

## Product boundary

Build a genuine Chromium-derived desktop browser with TrinolIT identity. Start
with an unmodified macOS arm64 Chromium baseline, then add small customizations.
Preserve the existing browser process, rendering engine, extension machinery and
browser services. Windows and Linux are later targets. A WebView/Electron shell
would require reimplementing too much browser functionality and is not the chosen
architecture.

## Layers and ownership

| Layer | Responsibility and intended integration |
| --- | --- |
| Chromium baseline | Blink, V8, content, network, GPU, sandbox, storage and multiprocess lifecycle; retain upstream behavior |
| Native shell | C++/Views integration for tab strip, toolbar, sidebar and window layout; use existing tab and navigation models |
| Browser services | Reuse profiles, bookmarks, history, downloads, permissions, password storage, printing, PDF and session restore |
| Trusted WebUI | Internal new-tab/settings surfaces where appropriate, with TypeScript/HTML/CSS, strict CSP and narrow Mojo interfaces |
| Trinol modules | Product-specific code under trinol/, incorporated through explicit overlay destinations and GN integration patches |
| Branding | Owned logos, themes, resources and app identity; reviewed license/provenance records under assets/ |
| Future services | AI and account sync require separate design, consent and threat review; outside Phase 0 |
| Release engineering | Platform packaging, signing, updates, rollback and vulnerability handling; must exist before public distribution |

Exact upstream symbols and paths must be inspected at the selected revision.
Likely integration areas include chrome/browser/ui/views, chrome/browser/ui/webui,
chrome/browser/resources, chrome/app and corresponding GN targets. These are
navigation hints, not evidence that specific patches already exist.

## Repository and source flow

The product Git repository holds reviewed patches, overlays, owned modules,
assets, config templates, scripts, tests and CI. A separate upstream checkout
holds Chromium and its DEPS dependencies. Reproduction flows from exact recorded
upstream/tool pins, through dependency sync, then ordered patches and explicit
overlay mappings, into generated output outside the product repository.

`upstream/manifest.json` records the verified source/tool pins, GN arguments and
build/runtime evidence. The versioned customization contract now records the
ordered patch SHA-256 digests and exact changed source paths, Git modes and final
content hashes. Verification distinguishes pristine, exact applied customization
and unauthorized changes; revision/dirty-tree protections remain enforced.
Phase 2B1 adds baseline macOS color recipes, leaving TabStripModel, commands and
window geometry upstream. ThemeService retains appearance/user-theme priority;
incognito, high contrast and app windows are excluded. The standalone simulator
does not replace native browser models or establish native acceptance.

## Trust and compatibility

Webpages stay in sandboxed renderer processes; privileged operations stay in
browser services behind validated IPC. Custom UI must preserve permission prompts,
security indicators, keyboard behavior, accessibility and incognito isolation.
Never bypass certificate checks or sandboxing to make a feature appear functional.
Use dedicated development profiles, not the user's Chrome profile.

Chrome-equivalent service parity is not assumed. Google sign-in/sync and some
extension identity flows depend on restricted APIs, as described in Chromium's
[API guidance](https://www.chromium.org/developers/how-tos/api-keys/). DRM, proprietary
codecs, extension-store distribution and service integrations need separate
technical and distribution review. Do not embed third-party keys or claim Chrome
branding/rights. No product license grant is invented at this stage; the owner
must select licensing for original work before distribution, while preserving
upstream and third-party notices.

## Implementation and verification strategy

Prove upstream builds and launches first. Add branding separately, then native UI
changes in small modules without replacing browser service implementations.
Introduce workspaces, split view and AI only in subsequent reviewed phases.

Each upstream revision change must pass patch application, compilation and
relevant tests. UI changes need browser/WebUI tests plus keyboard/accessibility
checks; profile features need isolation and migration coverage. Smoke coverage
must include navigation, tabs, private mode, downloads, bookmarks, history,
permissions, extensions, session restore, PDF and printing before usable-alpha
claims. Performance and crash behavior need measured baselines.

The principal risks are upstream patch drift, UI regressions, resource pressure,
service restrictions and timely security updates. Small patches, explicit pins,
a baseline build and release gates are the chosen controls.

## Phase 2B2 New Tab integration

The approved native New Tab slice reuses Chromium's existing trusted
`chrome://new-tab-page-third-party/` controller, resource map and normal New Tab
rewrite. Desktop local New Tabs use bundled Orbit resources. Enterprise policy
and extension overrides retain their earlier upstream routing precedence; valid
non-Google provider remote New Tabs remain supported. Incognito and guest rules
remain separate. This approval does not resolve historical lifecycle findings.

An argument-free typed Mojo operation focuses the owning visible browser's real
omnibox only after trusted-origin, profile and transient-user-activation checks.
Search preferences, suggestions, query encoding and navigation stay in Chromium.
No web search backend, query IPC or credential access is added. Top Sites binding
is deferred because its prepopulation behavior needs a separate product decision;
the page exposes an honest empty state and the native History link.

The existing profile theme bridge supplies browser appearance. Separate owned
GRIT strings and static HTML/CSS/TypeScript/SVG are incorporated through the ordered
patch/overlay contract. See the [implementation and verification report](phase-2b2-new-tab-report.md)
for actual compilation results and remaining native acceptance checks. Phase 2B2
authorizes implementation and guarded compilation, not another native launch.
