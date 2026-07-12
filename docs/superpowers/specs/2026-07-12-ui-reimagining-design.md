# Owlet Dashboard — UI Reimagining ("One app, four rooms")

- **Date:** 2026-07-12
- **Status:** Approved design, pre-implementation
- **Branch:** `multi-user`

## Context

The app grew a landing page, a power dashboard, and two well-received experimental
views (Tonight, Rhythms) with unrelated styling. This spec unifies them into one
cohesive product: simplified, Owlet-like data viewing by default, with the raw
workbench one tap away, themed light/dark from a single token system extracted
from the two prototypes.

## Decisions (settled with owner)

| Question | Decision |
|---|---|
| Default view after login | **Now** — a new live-glance home |
| Power dashboard | Moves to **/data**; nothing removed |
| Theme behavior | Follows `prefers-color-scheme`; manual override in profile menu, persisted per user |
| Dark theme source | Tonight's palette (deep navy, indigo glass) |
| Light theme source | Rhythms' palette (warm paper, ink, violet accent) |
| Brand mark | "Owlet Dashboard·" wordmark with the living freshness dot, in the shell on every view |

## 1. Design tokens (`app/static/theme.css`, served once, used by every page)

CSS custom properties on `:root[data-theme="light"]` and `[data-theme="dark"]`:

- **Color:** `--bg`, `--bg-accent` (gradients), `--surface` (cards), `--surface-line`,
  `--ink`, `--dim`, `--faint`, `--accent` (violet #6d28d9 light / #818cf8 dark),
  `--sleep-deep/-light`, `--awake`, `--good`, `--warn`, `--nodata`.
- **Shape/space:** `--radius-card: 18px`, `--radius-control: 10px`, spacing scale.
- **Type:** system-ui stack; display sizes with negative tracking; tabular numerals
  for all vitals; serif display (`Iowan Old Style` stack) reserved for Rhythms'
  editorial headline only.
- Dark values come from the current Tonight page; light values from Rhythms.
  Cards in dark are translucent glass (`backdrop-filter`), in light are white with
  soft shadow — same component, two skins.
- `prefers-reduced-transparency` / `prefers-contrast` fallbacks included once, centrally.

Theme resolution: inline script in the shared shell head sets `data-theme` from
(1) per-user preference if set, (2) else `prefers-color-scheme`. Toggle in the
profile menu: Auto / Light / Dark, persisted in `dashboard_preferences.theme`
(whitelisted server-side).

## 2. App shell (`app/shell.py`)

One Python helper `render_shell(view, body, ...)` producing the common chrome all
authenticated views share:

- **Top bar (desktop):** brand ("Owlet Dashboard" + living dot), centered nav
  tabs — **Now · Tonight · Rhythms · Data** — active tab highlighted, profile
  avatar/menu at right. Translucent (`backdrop-filter`), content scrolls under.
- **Bottom tab bar (mobile ≤640px):** the four rooms as icon+label tabs; profile
  moves into the top-left brand row. Parents use phones; this is the primary nav.
- **The living dot** renders in the shell brand on every view, fed by the same
  freshness logic (extracted to a small shared JS snippet `theme-shell.js`:
  fetches `/api/health` + latest reading age, colors the dot, click = refresh
  current view's data).
- Footer disclaimer, shared once.
- Auth pages (landing/onboarding) don't get the app shell but do consume the
  same tokens so the brand carries through.

## 3. The four rooms

### Now (`/` — new home, new file `app/now_page.py`)
The ten-second check. Hero: current O₂ and HR as the two biggest numbers in the
app, sleep/wake state with duration, all live (5s polling like the dashboard).
Below: a "today so far" strip (sleep total, dips, battery), a one-line generated
status sentence (reusing Tonight's narrative tone), and a compact link-card to
last night's report. Empty/onboarding states reuse the existing flows.

### Tonight (`/night` — restyle to tokens)
Content unchanged. Gets the shell; its bespoke colors are replaced by tokens
(in light theme it becomes a "morning report" — same layout on paper white;
the starfield only renders in dark).

### Rhythms (`/rhythms` — restyle to tokens)
Content unchanged; gets the shell; already matches the light tokens, gains a
proper dark rendering (paper→navy, ink→mist, actogram cell colors from tokens
with dark-tuned sleep scale).

### Data (`/data` — the current dashboard, reframed)
- Route moves from `/` to `/data`; `/` serves Now; old bookmarks fine because
  `/` still works (just shows Now).
- Reskin via tokens: toolbar/cards/tables pick up `--surface`/`--ink` etc.
- **Dark mode for charts:** Chart.js colors read from tokens at render time
  (grid lines, tick color, dataset palette variants tuned per theme); offline/
  no-data/challenge band alphas adjusted for dark.
- All existing features stay: combined/split toggle, smoothing, O₂ challenges,
  notifications, CSV, crypto toggle, readings table.

## 4. The glue — insight → raw deep links

Contract: `/data?focus=<ISO start>&span=<minutes>` zooms the charts to that
window on load (sets `zoomWindow` after first render, loads enough history).

- Tonight: each O₂ dip event row links to `/data?focus=<dip start - 15m>&span=45`.
- Tonight: the sleep timeline links to the whole night window.
- Rhythms: each actogram cell links to `/data?focus=<bucket start>&span=120`.
- Now: the hero numbers link to `/data` (today window).

Every simplified claim is verifiable in the raw view in one tap.

## 5. Build order (each phase ships working, own commit)

1. **Theme layer + shell:** `theme.css`, `shell.py`, shared dot JS; apply shell +
   tokens to Tonight and Rhythms; theme toggle in profile menu persisted via
   `dashboard_preferences.theme`; auth pages consume tokens.
2. **Now page:** build `/`; move dashboard to `/data`; update nav, tests, README.
3. **Data reskin:** tokens + dark chart palettes in `dashboard.py`.
4. **Deep links:** `?focus`/`span` in Data; add links from Tonight/Rhythms/Now.

## Non-goals

New data features, mobile apps, changes to auth/onboarding flows (styling only),
Owlet trademark rebrand (name stays as decided earlier).

## Risks

- `dashboard.py` (3.4k lines) reskin is the riskiest phase — tokens must not
  break chart alignment logic; done last-but-one deliberately, verified against
  live data in both themes.
- Theme flash on load: mitigated by the inline `data-theme` resolver in `<head>`.
