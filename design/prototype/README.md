# Trinol Orbit interactive preview

From the product repository:

```sh
python3 design/prototype/serve.py
```

Open [the preview](http://127.0.0.1:4173/prototype/). Stop the server with Ctrl-C.
Python 3.12 is the tested runtime. There is no install step, build step, CDN,
external font, account, telemetry or browser-profile access. The server binds
loopback and serves only design/. Do not expose it as a production service.

This is a design simulator, not a Chromium integration or browser engine. All
page content, tabs, history and shortcuts are fictional. URL entry changes a
local preview; it does not navigate to a website. Downloads/profile/site-info
panels describe their unconnected state. Workspace selection changes the demo
space label; it does not implement native workspace persistence. Session state
resets on reload. Traffic lights are decorative, inert preview geometry.

## Controls

- Tab buttons switch; × closes; + creates a tab. Menu offers pin/unpin. Drag
  tabs within the pinned/unpinned boundary. Arrow keys switch focused tabs;
  Alt+Shift+Arrow reorders. Audio indicator toggles a simulated mute state.
- Back/forward traverse per-tab simulated history. Reload starts a 1.2-second
  local loading state; Stop cancels it. Review states can hold loading for review.
- Address suggestions support Up/Down, Enter and Escape. URLs accept HTTP/HTTPS;
  other schemes render an error. No URL entered here is fetched or executed.
- ⌘K / Ctrl+K opens commands; type, use Up/Down and Enter. Escape closes dialogs
  and returns focus. ⌘L focuses the address, ⌘T creates, ⌘W closes, ⌘B toggles
  the sidebar; Ctrl equivalents are supported. The hosting browser may reserve
  some shortcuts; visible controls provide the same actions.
- The titlebar layout button switches horizontal/vertical alternatives. Sidebar
  collapse works in both. The footer theme button and Make it yours switch
  appearances. Review states exposes loading, empty, invalid and warning states.
- A shortcut form validates input and adds a session-only shortcut (maximum seven).

Default: horizontal tabs and expanded sidebar at wide sizes; compact navigation
below 760 px. The vertical alternative shares the same simulator state.

## Checks and capture reproduction

Dependency-free model tests (Node 22+):

```sh
node --test design/prototype/model.test.js
```

Optional browser checks use an already-installed Playwright module and a
separate testing browser. No tooling is downloaded by this repository:

```sh
export ORBIT_PLAYWRIGHT_MODULE=/absolute/path/to/node_modules/playwright/index.js
export ORBIT_TEST_BROWSER=/absolute/path/to/testing-browser-executable
node design/prototype/browser-check.cjs
# Replace the checked-in review captures, only after visual review:
node design/prototype/browser-check.cjs --capture
```

Run the loopback server first. The runner keeps Chromium sandboxing enabled,
rejects paths under TrinolBuild/out and never selects an installed application by
bundle ID. The captured browser was the separate Playwright cache build
141.0.7390.37, not the pinned product's 155.0.8059.85. Runtime and module paths are
local environment variables, never committed machine configuration.

[Design system](../../docs/design/trinol-orbit-design-system.md) ·
[Architecture](../../docs/design/browser-shell-architecture.md) ·
[Native integration](../../docs/design/native-ui-integration-plan.md) ·
[Review captures](../review/README.md)
