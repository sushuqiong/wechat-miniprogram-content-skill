# Quality Gates and the Real-World Pitfall List

## Contents

1. Gate design principles
2. The minimum gate set (seven gates)
3. Criteria per gate
4. Pitfall list (reverse-engineered from real incidents)
5. Best practices

## 1. Gate design principles

- **The check script is the specification**: every rule must be script-decidable; a rule that cannot be checked does not exist.
- **One standalone script per gate**, named after its purpose (check_order / check_consistency / ...), independently runnable, independently failable.
- **Rerun everything before every delivery**; never cite "it passed last time". In content projects the data changes daily — historical conclusions are worthless.
- Uniform output: `PASS/FAIL + criterion name + failure detail`; non-zero exit code on failure, so it plugs into any pipeline.

## 2. The minimum gate set

| # | Gate | What it prevents |
| --- | --- | --- |
| 1 | check_order — schedule | Duplicate/missing content, scheduling violations |
| 2 | check_consistency — cross-version | Index/full-text drift, broken routing, missing images |
| 3 | check_milestone_sum — size ledger | Package over the limit (a hard release failure) |
| 4 | check_release — static release checks | JS syntax errors, unclosed WXML tags, missing event bindings, references to nonexistent images, unsupported formats (webp) |
| 5 | runtime_check — behavioral assertions | Runtime logic errors that static checks cannot see |
| 6 | check_theme — theme tokens | "Half-applied themes" (mandatory once theming exists) |
| 7 | check_interaction — interaction robustness | Copy failure with no fallback, non-copyable rich-text, missing wx:key, iOS date NaN |

## 3. Criteria per gate

**check_order**: total count with no duplicates or gaps; same-category spacing ≥ N days; seven-day peak ≤ cap; monotonically progressive difficulty (plateaus allowed); final 7 days cover every category.

**check_consistency**: index count = full-text count; ID sets exactly equal; every image path in the index exists on disk; the subpackage routing rule (e.g. odd/even) matches the actual data distribution.

**check_milestone_sum**: walk all three packages, print file count / source size / compressed estimate; main package against the 1950 KB line, subpackages against the 2048 KB cap; any excess is FAIL.

**check_release** (static): every .js passes a syntax check (`node --check`); WXML tags balanced; every `bind*`/`catch*` handler referenced in WXML exists in the matching .js; image paths referenced in WXML/WXSS exist; no webp (unsupported on older base libraries); the code highlighter does not swallow characters (diff source text vs highlighted plain-text output).

**runtime_check** (behavioral assertions): hand-write a mock `wx` in Node (storage / navigate / toast / clipboard / reportEvent / setNavigationBarColor / setTabBarStyle, etc.), mock Page/App/getCurrentPages, then **require the real page code and drive it**: swipe boundaries (previous on first card / next on last), the debounce window, copy success and failure fallback, state reset after data clearing, the share object shape, analytics denominators. The assertion count grows over time — add one for every bug fixed.

**check_theme**: see references/theme-system.md; script is scripts/check_theme.py.

**check_interaction**: see references/interaction-robustness.md; script is scripts/check_interaction.py. FAIL on: clipboard used with no `onShowCopyFallback`, rich-text detail page with no copy handler, `wx:for` without `wx:key`, hyphenated `new Date('YYYY-MM-DD')` literal (comments excluded). REVIEW (non-failing) on: scroll container with only max-height, swipe handler with no debounce marker, 900 ms timestamp-blackout pattern.

## 4. Pitfall list (reverse-engineered from real incidents)

### Theming / styles
1. Hardcoded brand colors scattered across page WXSS/WXML → half-old-color after re-theming. Replace globally, then gate the old hex values.
2. "Pitfall" / "comparison" blocks with hardcoded light backgrounds and dark text → unreadable in dark themes. Always use theme variables (--warn-bg / --note-bg, etc.).
3. Switch component with `color="#xxx"` hardcoded → stays the old color after re-theming. Use `color="var(--primary)"` style values.
4. `backgroundTextStyle` fixed to dark → invisible pull-down spinner in dark themes. Follow the theme's dark flag.

### State / interaction
5. Clearing data deletes the theme key but does not reset the page or nav bar → theme jumps back to default on next entry. After clearing: reset all persisted state + re-apply nav bar / tabBar colors + refresh current page data.
6. List page recomputing unconditionally in `onShow` → after paginating to 120 items, returning from detail collapses back to 60; feels like a jump to top. Use a dirty check: recompute only when filters changed.
7. Favorites sorted by card ID → the just-favorited card sinks to the bottom; users think favoriting failed. Sort by favorite time, newest first.
8. No debounce on card swiping → animation stutters on rapid taps. Add a ~260 ms lock window, plus a behavioral assertion.
9. "Tap to view full image" that actually navigates to the detail page → copy does not match behavior. Either truly preview (previewImage) or fix the copy.

### Interaction / copy (new — see interaction-robustness.md)
13. Copy button calls `setClipboardData` but rich-text code cannot be selected; privacy-authorize failure ends in a toast → three-layer fallback (direct write → authorize retry → selectable-text overlay), one shared helper.
14. Code-area `catchtouch` handler stores a timestamp and `onTouchEnd` blocks swipes for 900 ms → a legitimate swipe right after scrolling is swallowed. Use a boolean `_noSwipe` cleared at gesture end.
15. Vertical `scroll-view` with only `max-height` → no scroll range on some base libraries. Do NOT patch it with a constant `height: 58vh; max-height: 820rpx`: short code then sits in a half-screen empty box. Compute a definite height from the code in JS and write it as an inline style (`style="height:{{codeH}}rpx"`, clamp ~160–600rpx, count CJK/full-width characters as two units) so short code fits and long code scrolls inside the block; see interaction-robustness.md section 4.
16. No debounce on flip → rapid taps stutter; ~260 ms lock shared by button and swipe.
17. `new Date('2025-01-01 10:00')` → NaN on iOS; `str.replace(/-/g,'/')` first. `navigateTo` past 10 levels fails silently.

### Engineering
10. Template and subpackage copies drift → single source + scripted distribution + post-distribution consistency check.
11. `data` defaults hardcoding an old theme id like `'brand'` → silently broken after a rename. Reference the DEFAULT_ID constant from theme.js.
12. AI-generated images committed with watermarks → see the illustration pipeline in references/methodology.md.

## 5. Best practices

- When you add a new asset class (themes, images, data files), **add its gate in the same commit** — do not defer it.
- Failure details should point at files and entries ("FAIL variables missing .theme-aurora --line"), not just counts.
- Behavioral assertions must run the real page code — do not re-implement the logic in the test; a copied test keeps passing while the code drifts.
- Refresh the size ledger on every build and record it in the README, creating a size history.
