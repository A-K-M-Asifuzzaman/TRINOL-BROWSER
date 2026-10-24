# Browser shell prototype architecture

The Phase 2A preview is a dependency-free ES-module application under
design/prototype/. Python's standard-library loopback server serves design/
only. No Electron/CEF/Tauri wrapper, embedded webpage, profile access, credential
API, network navigation or native Chromium process is part of it.

## File boundaries

| File | Responsibility |
| --- | --- |
| index.html | Semantic frame, toolbar, sidebar, page panel and dialog mount |
| tokens.css | Reusable dark/light semantic tokens, spacing and motion |
| shell.css | Component styling and desktop responsive layouts |
| icons.js | Original consistent stroke icon and orbit-mark components |
| model.js | Pure address classification, tab reorder/close selection and escaping |
| app.js | Session-only simulator, shared renderers, events and focus behavior |
| serve.py | Loopback server, scoped GET/HEAD paths, no listings, no external connections |
| model.test.js | Dependency-free Node tests |
| browser-check.cjs | Optional Playwright interaction/visual regression runner |

Plain JavaScript is deliberate: a small review simulator needs no bundler,
framework, transpiler or runtime dependency. This is the simpler self-contained
option permitted by the brief. Production trusted WebUI will use Chromium's
TypeScript/Mojo/build conventions; prototype JS is not to be copied wholesale
into privileged browser code. Tests exercise the parser and interaction boundary.

The state is a list of fictional tabs, selected tab ID, per-tab demo history,
loading timer, session bookmarks, theme, sidebar mode and shortcuts. Both tab
layouts consume that same list. Loading timers are canceled on navigation/close;
all state resets on a page reload. Personal/Studio selection changes a concept
label only, not profiles or service storage. Download and profile panels are
explicitly unconnected. All rendering of entered text is escaped; HTTP(S)
addresses and searches produce local mock content, never external requests.

## Native boundary

The native shell must be C++/Views attached to BrowserView, Chromium tab models,
commands and existing browser services. Security indicators, permission prompts,
certificate errors and real omnibox behavior remain native Chromium components.
The New Tab content is the candidate trusted WebUI boundary. Its production
search/shortcut APIs require a small typed, validated service surface, correct
profile ownership, incognito rules and CSP without unsafe-inline.

The preview server permits inline style declarations used for state color; this
is local demo CSP, not a proposed production WebUI policy. It forbids connections,
frames, objects, arbitrary forms and external scripts. The screenshots and QA
contain only labeled synthetic content. The preview traffic lights are inert;
AppKit window management will never be replaced by these illustrations.

See the [source-grounded integration contract](native-ui-integration-plan.md).
