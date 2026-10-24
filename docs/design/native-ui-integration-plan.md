# Chromium-native Orbit integration contract

Inspected locally against Chromium 155.0.8059.85 at
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`, not against moving main.
No native source change, GN generation, compile or app launch occurred in 2A.
All implementation below is proposed for a later reviewed phase.

## Verified ownership and extension points

Paths are relative to Chromium src. Line references identify the inspected pin.

| Concern | Actual source evidence | Proposed integration boundary |
| --- | --- | --- |
| Window ownership | chrome/browser/ui/views/frame/browser_view.h:132; browser_view.cc:935–979 | BrowserView observes the existing TabStripModel and owns child Views. Add owned Trinol Views through AddChildView; observe models with scoped lifetime, never duplicate WebContents ownership. |
| AppKit frame | chrome/browser/ui/views/frame/browser_native_widget_mac.h:34; .mm:266,347,353,744 | BrowserNativeWidgetMac owns titlebar height and native window creation/fullscreen callbacks. Preserve traffic lights, hit testing, native drag/titlebar and fullscreen transitions. CSS frame geometry is reference only. |
| Layout | chrome/browser/ui/views/frame/layout/browser_view_layout.h:97 and browser_view_tabbed_layout_impl.h | Work through the current layout/delegate structure. The old flat browser_view_layout.cc hint does not exist at this pin. Respect content/side-panel minimum widths and top-container/infobar order. |
| Toolbar | chrome/browser/ui/views/toolbar/toolbar_view.h:91; .cc:325,343 | ToolbarView derives AccessiblePaneView and creates LocationBarView in Init. Style existing commands, buttons and spacing. Do not replace the omnibox with a text field or draw URL-derived security badges. |
| Site information | chrome/browser/ui/views/location_bar/location_icon_view.cc:122,160,165,273 | LocationIconView delegates PageInfo and derives SecurityLevel/accessibility from LocationBarModel. Keep this trust path and dangerous/insecure/certificate behavior intact. |
| Horizontal tabs | chrome/browser/ui/views/tabs/tab_strip.h; tab.h:67; browser_tab_strip_controller.h:40–65 | BrowserTabStripController bridges TabStripModel to selection/pinning/closing. Add reviewed TabStyle/color/spacing changes around the existing controller, drag, grouping and audio behavior. |
| Existing vertical tabs | chrome/browser/ui/views/frame/browser_view.cc:984–1017; frame/vertical_tab_strip_region_view.h; chrome/browser/ui/tabs/vertical_tab_strip_state_controller.h:41,88–105 | BrowserView already creates a VerticalTabStripRegionView when the controller is present. Reuse this controller and its enable/collapse/width state after feature compatibility review. No parallel vertical-tab store or engine. |
| Sidebar | chrome/browser/ui/views/side_panel/side_panel.h:28; side_panel_coordinator.h:39; browser_view.cc:974 | Existing SidePanel is an AccessiblePaneView coordinated by SidePanelCoordinator. First reuse its service entries/actions. A persistent compact rail needs a narrow owned View/layout patch rather than treating the service panel as arbitrary WebUI chrome. |
| New Tab | chrome/browser/ui/webui/new_tab_page/new_tab_page_ui.cc:205–210,839 | CreateAndAddNewTabPageUiHtmlSource uses WebUIDataSource for the existing host; SetupWebUIDataSource registers GRIT resources. Reuse audited routing/profile mechanisms; do not blindly retain Google-specific modules or all existing privileged Mojo handlers. |
| WebUI build | chrome/browser/resources/new_tab_page/BUILD.gn:15; chrome/browser/ui/webui/new_tab_page/BUILD.gn | build_webui("build") declares static/TS/CSS files and generated Mojo dependencies. Place owned assets beneath trinol/, add explicit resource/GN wiring and review generated resource IDs. |
| Theme | chrome/browser/ui/color/chrome_color_id.h; chrome_color_mixers.cc; toolbar/tab-strip/omnibox mixers; color/BUILD.gn | Map semantic CSS roles to reviewed ColorIds/mixers and existing ThemeService/ColorProvider behavior. Preserve theme changes, high contrast, extension themes and incognito differentiation; no global hardcoded RGB replacement. |
| Keyboard | chrome/browser/ui/accelerator_table.cc:75,227,257 | Existing IDC_FOCUS_LOCATION, IDC_NEW_TAB and IDC_SHOW_DOWNLOADS accelerators remain authoritative. Check ⌘K availability before proposing a native palette accelerator. Use FocusManager/AccessiblePaneView and existing command enablement. |

The pinned sources have several feature-dependent branches (including vertical
and WebUI toolbar paths). Presence is verified; feature availability in the
compiled baseline and the intended Trinol default are not assumed.

## Data and security contract

The prototype list is discarded at the native boundary. Native tabs must derive
from TabStripModel/BrowserTabStripController and current tab interfaces. No
second history/bookmark/download/profile implementation is permitted. Sidebar
entries dispatch existing BrowserCommands/SidePanel actions with correct profile
ownership. Workspaces are a later design, not a new profile service in 2A.

A Trinol New Tab WebUI must use localized strings, bundled resources, strict
script/style CSP and typed narrow Mojo handlers. Validate URL schemes, lengths,
profile/incognito availability and user intent in browser-process code. Query
most-visited/bookmark data only through reviewed services; production empty
states contain no fictional history. Renderer content cannot execute shell
commands, read arbitrary files or access credentials. Dangerous URLs and TLS
interstitials remain Chromium-owned. No webpage gains privileged access through
the prototype command palette design.

## Reproduction and patch workflow

Product Git stays authoritative. patches/series and manifest overlays remain
empty in 2A; no selected design has been applied. The reusable token/icon assets
remain in design/ until approved for conversion into Views/vector-icon/GRIT
resources. Do not create unused native stubs or copy the prototype DOM into
browser chrome.

The new scripts/apply_product_patches.py defaults to check-only and requires an
explicit checkout. It verifies exact HEAD and complete clean Git status, rejects
unsafe paths/symlinks/duplicates/generated targets, and supports ordered regular
text patches. Dependent patches are checked in order using a temporary index and
object store; neither working files nor checkout .git objects/index are written.
Temporary check storage cost scales with the tracked index and changed blobs;
it has only been exercised on small synthetic repositories in this phase.

Future overlay schema: {"source":"product-relative-file",
"destination":"trinol/path/file","sha256":"64-lowercase-hex"}. Only new regular
files under trinol/ are copied, with matching content digest and exclusive
creation. Existing content, symlink parents, duplicate destinations and files
created by patches must be refused. There is no overwrite or force flag.

An explicit --apply performs git apply --check followed by git apply for each
patch in order, then copies overlays. Errors preserve work and list completed
operations; there is no reset, cleanup or automatic rollback. No live checkout
was passed to this script in 2A. The foundation validator intentionally still
requires an empty customization contract. A future native phase must review its
schema/validator change alongside its first concrete patch and overlay mapping.

## Incremental implementation order and acceptance

1. Review horizontal default versus existing vertical-mode compatibility and
   settle the token/brand direction. Keep frame/toolbar/content ownership intact.
2. Add owned theme/vector resources and a narrow color/spacing patch. Do not
   change branding/signing flags or output directories without explicit review.
3. Add a small left navigation View through the actual layout delegate, preserving
   existing SidePanel, infobars, find bar, dialogs, fullscreen and web-app layouts.
4. Introduce the trusted Trinol New Tab WebUI with localized TypeScript/CSS and a
   minimal audited browser-process interface; then review search/focus semantics.
5. Integrate the selected tab appearance through existing horizontal/vertical
   controllers. A command palette needs a separate accelerator/action/focus review.
6. Before compilation, inspect GN deps and estimate affected action count using
   the existing build tooling. //chrome/browser/ui/views:views is a component;
   //chrome/browser/resources/new_tab_page:build is the inspected WebUI target.
   Native links can fan out: a small patch does not guarantee a small build.
   Use the existing guarded one-job incremental runner and preserved GN/output
   only after separate approval, normal memory and capacity checks. No clean/full
   rebuild or security/linker workaround is proposed.
7. Add affected unit/browser/WebUI tests before runtime validation. Existing
   examples include tabs/tab_strip_unittest.cc, browser_tab_strip_controller_
   browsertest.cc, tab_strip_interactive_uitest.cc and vertical tab tests;
   browser_native_widget_mac_interactive_uitest.mm covers native widget behavior.
   chrome/test/BUILD.gn declares browser_tests (1627) and unit_tests (4691).
   chrome/test/data/webui/new_tab_page contains TypeScript tests; run the new
   tests through its current suite harness, not an invented target name.
8. Regression gates: tab lifecycle/groups/pinning/drag/audio, omnibox/security,
   PageInfo/certificates, permissions, bookmarks/downloads, profiles/incognito,
   native keyboard/accessibility, minimum sizes/2× scaling, theme/high contrast,
   fullscreen/window controls, WebUI CSP and UI performance. Native lifecycle
   launch remains blocked by R6 until a separately reviewed safety gate.

Ready: design tokens, original vectors, shared visual components, prototype
interaction evidence and a tested application contract. Not ready: native C++
implementation, production WebUI bindings, branding packages or native runtime
acceptance. Phase 1C remains PARTIAL throughout this independent design phase.
