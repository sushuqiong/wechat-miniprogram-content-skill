# Theme-Token System and UX Differentiation

## Contents

1. Token design: a theme block only overrides variables
2. Theme table structure (theme.js)
3. Three hard rules
4. Special handling for background-image themes
5. UX differentiation checklist (distancing sibling products)
6. Gate criteria

## 1. Token design

Define a set of semantic variables on `page` (--primary / --text / --panel / --code-bg / --tag-*, etc.). Each theme is a single `.theme-<id>` block that **only overrides variables — never touches layout**. All page styles consume `var(--xxx)`. Switching themes = swapping the root class + re-applying nav bar / tabBar colors, with zero page-code changes.

Semantic variable layers:

- Brand: --primary / --primary-2 / --primary-soft
- Text: --text / --sub / --muted
- Containers: --panel / --panel-2 / --line / --shadow
- Functional: --code-bg / --deco / --tag-beginner(-bg) / --tag-advanced(-bg) / --warn-* / --note-*
- Background image: --bg-img / --bg-size / --veil

## 2. Theme table structure (theme.js)

One record per theme: `{ id, name, desc, nav, front, tabBg, tabColor, tabSel, dark, bgImg, primary, swatch[] }`.

- The `dark` flag drives: nav bar frontColor, tabBar borderStyle, page `backgroundTextStyle`, and the frosted-light brand-area adaptation under dark themes.
- `swatch` feeds the theme-picker UI (color dots for image-less themes).
- `DEFAULT_ID` is defined once as a constant; every page's `data` default references it — **never a string literal** (literals silently break on renames).

## 3. Three hard rules

1. **Every theme block must define all required variables** — miss one and that spot falls back to the default color: a "half-applied theme". Enforced by the gate.
2. **Any theme with a background image must define --veil** (a dimming overlay) — otherwise body text sits on the image unreadably. Enforced by the gate.
3. **No hardcoded theme colors anywhere in pages** — the old brand hex values are written into the gate; any residue fails the build.

## 4. Special handling for background-image themes

- Images live in `images/theme/`; each <100 KB (gate-enforced), 640 px wide is enough (full-bleed plus veil).
- Under dark themes, if the logo/title uses dark glyphs, give the brand area a light frosted background (rgba(252,251,255,.93)) or it becomes unreadable.
- Image-less themes (e.g. the default) are pure CSS variables — do not force an image; saves package size.
- Background-image copyright: original generation, watermark cropped, manually verified per image. See references/methodology.md.

## 5. UX differentiation checklist

If your product family has sibling apps (e.g. an R-language edition and a Julia edition), differentiate deliberately to avoid a "reskin" impression:

1. **Theme picker form**: a horizontally scrolling theme gallery (large cards with real background previews), not a small color-swatch grid.
2. **Card-flip gesture**: the daily card supports horizontal swiping (horizontal displacement threshold + vertical tolerance + 260 ms debounce), not just buttons.
3. **Search feedback**: highlight the matched keyword inside result titles.
4. **Favorites ordering**: newest favorite first — the just-favorited card sits at the top.
5. **Data clearing**: also resets the theme and re-applies nav bar / tabBar colors; no state jumps.
6. **List return**: coming back from detail does not reset pagination (no recompute when filters are unchanged).

## 6. Gate criteria (scripts/check_theme.py)

1. Every id in the theme table has a matching `.theme-<id>` block in app.wxss
2. Every block defines all required variables
3. DEFAULT_ID exists in the theme table
4. Themes with bgImg define --veil
5. Files referenced by bgImg exist and are <100 KB
6. No stale theme selectors project-wide (leftover `.theme-<old-name>` after renames)
7. No hardcoded legacy brand colors project-wide

Run: `python scripts/check_theme.py <miniprogram source dir>` — exit code 0 when all pass.
