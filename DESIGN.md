# linkrescue design system

Read this before changing the site's UI. Do not introduce a new direction; extend this one. English only. Values below come from `docs/index.html` as of this commit.

## Concept

A pulse line per saved link: steady when alive, a jump when moved, flat when dead.

Theme: light.

## Color tokens

| Token | Value | Role |
|---|---|---|
| `--bg` | `#f1faf8` | page background |
| `--fg` | `#0b2a30` | body text |
| `--mut` | `#3d646d` | secondary text (AA on bg) |
| `--card` | `#ffffff` | card and panel surface |
| `--line` | `#bfe0dc` | borders and dividers |
| `--acc` | `#0e7490` | primary action, links, focus ring |
| `--accfg` | `#ffffff` | text on accent |
| `--code` | `#0b2a30` | code block background |
| `--codefg` | `#a5f3fc` | code block text |
| `--warn` | `#b45309` | warning border and limits |

Contrast: every text node on the page is checked against WCAG AA (4.5:1, 3:1 for large text) with a script in the repo owner's QA harness. Keep it passing when you change a color.

## Type

| Token | Stack | Role |
|---|---|---|
| `--arabic` | `'Alexandria',sans-serif` | Arabic font stack |
| `--body` | `'Outfit','Alexandria',system-ui,sans-serif` | body font stack |
| `--head` | `'Syne','Alexandria',system-ui,sans-serif` | heading font stack |

Font sizes in use: `.86rem`, `1.5rem`, `1rem`, `.9rem`, `.72rem`, `clamp(2rem,8vw,3rem)`, `1.4rem`, `1.15rem`, `clamp(1.9rem,8.2vw,3.9rem)`, `1.3rem`, `.74rem`.

## Spacing, radius, elevation

- Spacing values in use: `2px`, `4px`, `6px`, `8px`, `10px`, `11px`, `12px`, `14px`, `16px`, `26px`, `30px`, `44px`. Prefer these; do not add new ones.
- Radius: `--r` (8px). Use the token, not literals.
- Elevation: `0 14px 34px -18px rgba(14,116,144,.45)`

## Motion

- Durations in use: `.05s`, `.15s`, `.25s`, `.2s`, `.34s`, `.3s`, `.42s`, `.6s`, `2.6s`.
- Curves: `cubic-bezier(.16,1,.3,1)`, `cubic-bezier(.2,.8,.2,1)`, `cubic-bezier(.22,1.36,.32,1)`.
- Every animation sits behind `prefers-reduced-motion: reduce`, which turns animation and transition off.
- Motion shows state or order. It is never decoration.

## Components and states

- Button `.btn` (filled) and `.btn.alt` (outline): min height 44px, visible `:focus-visible` outline (2px accent), hover and active states.
- Card `.card`, warning card `.card.warn` (left border in `--warn`).
- Language toggle `.langtoggle` with `aria-pressed`.
- Code block `pre`: always LTR, monospace.
- Status words use `.ok b` and `.no b` colors (AA checked).

## RTL rules

- The language toggle sets `dir` and `lang` on `<html>`. Arabic text uses the `--arabic` font and line-height 1.75.
- Use logical CSS (`margin-inline`, `inset-inline-start`, `text-align:start`). No `left` or `right` for layout.
- Letter-spacing is 0 and text-transform none in Arabic.
- Code, terminal output and demo panels stay LTR (`direction:ltr`). Install and demo output stay English.
- Arabic is Egyptian-leaning plain language. Brand names and commands stay Latin.

## Microcopy voice

Plain, specific, honest about limits. Say what it does and what it does not. No hype, no invented numbers.

Examples from the site:

1. Don't let the links you saved die.
2. CONTENT MOVED
3. HTTP 404; no archived copy found
4. A site that refuses bots is BLOCKED, not BROKEN.
5. The archive lookup needs internet access.

## Do / Don't

| Do | Don't |
|---|---|
| Five fixed statuses | Invent new statuses |
| BLOCKED is not BROKEN | Call every failure broken |
| Pulse only to show state | Animate for decoration |
| Teal accent, status colors for state | Status colors as decoration |
| Say text only is saved | Imply a full page copy |

## Known hard-coded values (should become tokens)

These literal colors appear in the CSS outside `:root`: `#06141a`, `#0a2a33`, `#17703f`, `#2e9e5b`, `#a8281b`, `#c0392b`, `#d3f1ec`, `#e3f2f0`, `#fff`.
Also: status colors in `.ok b` and `.no b`, and several literal pixel sizes in component CSS. Move them into tokens next time that block is touched.
