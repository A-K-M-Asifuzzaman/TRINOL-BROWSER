# Trinol Orbit design system

Status: Phase 2A design foundation, awaiting selection. Prototype only.

## Direction and critique

Orbit is a professional desktop shell with a clear frame/content boundary and
an original three-path orbital mark. The default combines horizontal tabs and
a 216 px expanded navigation sidebar (64 px rail when collapsed). A functioning
vertical alternative is included for review; it is not a second tab engine.

Initial direction: graphite, blue and cyan; system typography; quiet dense
controls; generous New Tab composition. Review against the brief removed
promotional cards, clock/weather widgets, glowing gradients and decorative
animations. The orbit drawing is the single expressive detail. Native window
geometry stays compact, content is left-aligned, and an asymmetric New Tab
composition leaves open space on the right. Both appearances use identical
geometry rather than a separately branded light theme. Green is used only for
the conventional inert macOS traffic-light illustration, never as product accent.

```text
[ native-safe inset ][ horizontal tabs + active underline ][ + ][ layout ]
[ back forward reload ][ site · address/search · star ][ download profile menu ]
[ navigation rail ] [ space                         quick commands ]
[ bookmarks       ] [ orbit mark · trinol                         ]
[ spaces (concept)] [ Where to next?                 orbit motif  ]
[                 ] [ search                                      ]
[                 ] [ shortcuts                                   ]
[ settings        ] [ demo reading threads                        ]
[ collapse        ] [ appearance                                  ]
```

## Tokens and typography

Canonical reusable CSS: [tokens.css](../../design/prototype/tokens.css).

| Semantic role | Dark | Light |
| --- | --- | --- |
| Frame | #101319 | #E7ECF3 |
| Surface | #191E27 | #F2F5FA |
| Content | #131820 | #FBFCFE |
| Text | #F4F6FA | #172234 |
| Muted text | #A5B0C0 | #526078 |
| Focus/accent | #86B1FF | #245DC2 |
| Accent surface | #233854 | #DCE8FF |
| Cyan detail | #69D8F5 | #006781 |
| Warning/coral | #FF9388 | #B33A30 |

The suggested #4C8DFF was lightened in dark mode for small-text contrast; muted
slate was adjusted similarly. Blue is functional focus/selection, cyan is a rare
brand detail, coral marks warnings and the secondary concept space. Security
classification must come from Chromium, never a URL string in the native product.

System UI typography avoids font payloads and licensing ambiguity. Roles:
11–12 px metadata/tab labels, 13 px controls, 15 px search, 30 px wordmark and
40–66 px responsive New Tab heading. Minimum line-height is 1.5 for body copy;
headings use 1.1. Titles truncate instead of wrapping into controls.

Spacing scale: 4/8/12/16/24/32/48/64 px. Radii: 8 px controls, 12 px content/search,
14 px dialogs. Toolbar 52 px; tab row 46 px; address field 34 px; primary search
60 px. Main icon targets are 32 px, profile 27 px and tab close 25 px. The preview
footer uses 24 px minimum button height. Native layout must derive physical
insets from AppKit/Views instead of treating CSS pixels as Cocoa measurements.

## Components and states

- Original stroke icons and orbit mark, reusable tab item and icon button.
- Tab variants: active, inactive, pinned, audio/muted, loading, long title,
  overflow and reorder. Active underline complements background and ARIA state.
- Address: empty, focused, suggestion selection, simulated URL/search, loading,
  non-HTTPS, unsupported address and certificate-warning example.
- Sidebar: expanded, compact, horizontal/vertical layout and narrow breakpoints.
- New Tab: brand, semantic search, editable fictional shortcuts, demo history.
- Native dialog-based palette and service panels; empty states explain missing
  integration. Command options use one focused combobox and active descendant.

Interactions are restrained 150 ms color/background changes. The only repeating
animation is a loading ring tied to loading state; reduced motion disables it.
No always-running background animation, cloud API or downloaded image exists.

## Accessibility and behavior

Semantic buttons/forms, roving tabs, keyboard commands, visible focus, labeled
combobox/listbox suggestions, dialog focus containment, Escape dismissal and
focus return are implemented. Warning text accompanies color. Both themes pass
4.5:1 checks for the selected semantic normal-text pairs. Disabled controls are
visually distinct and are not represented as active connections/services.

Responsive checks cover 720/960/1440/1920/2560 px widths with no horizontal page
clipping. Below 760 px navigation becomes compact; vertical overflow stays inside
the content or tab list. Full screen-reader certification, RTL, touch testing,
Windows/Linux rendering, forced-colors and native display scaling remain for
later integration review. This phase does not claim complete WCAG conformance.

[Asset provenance](../../design/assets/README.md) ·
[Captures](../../design/review/README.md)
