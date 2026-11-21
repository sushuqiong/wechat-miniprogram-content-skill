---
name: wechat-miniprogram-content-app
description: End-to-end playbook for content-focused WeChat Mini Programs under an individual (personal) account — code cards, knowledge cards, question banks, daily-card apps, other offline-first read-only programs. Covers content data pipelines and subpackage size budgets, automated quality gates (mocked-wx behavioral assertions), adversarial compliance review for personal accounts (category red lines, induced sharing, privacy, image copyright), CSS-variable theming, interaction robustness (copy-code fallback, swipe, scroll-view, native-JS/iOS pitfalls), platform hard limits, and the ICP filing + release workflow (DevTools CLI / Nightly wechatide / miniprogram-ci) with version-bump discipline. Use when building, reviewing, debugging, re-theming or publishing such a mini program, or when asked about personal-account limits, ICP rejection (备案驳回), theming, copy/clipboard or swipe bugs, quality gates, or CLI upload.
---

# Content-Focused WeChat Mini Programs (Personal Account) — Field Playbook

Distilled from a real shipped project: a 365-card bioinformatics code-card mini program with 10 categories, a daily-card feature, two subpackages, 9 themes, 16 automated gates, published under a personal account. This Skill is the reusable abstraction of that process.

## Core judgment: confirm the shape first

The first decision for a content mini program is **offline-first**: ship all content inside the package, zero `wx.request`, zero `web-view`. This single choice eliminates most of the compliance surface (domain whitelists, content-security APIs, network-related privacy declarations). The price is a hard 2 MB main-package budget that must be managed deliberately. Introduce networking only when content truly must update dynamically — and accept the full compliance obligations that come with it.

The second decision is **account boundaries**: personal accounts cannot select regulated categories (medical, finance, credentialed education), cannot use WeChat Pay, and cannot host user-generated content. Design around these on day one instead of deleting features later.

## Workflow (six stages, in order)

### Stage 1 — Content pipeline
Topic matrix (total × categories × difficulty) → production schedule (date mapping for daily cards) → two-layer data (index always in main package / full text in subpackages, loaded on demand) → illustrations produced by the content code itself (never scraped web images) → size ledger refreshed on every build. See [references/methodology.md](references/methodology.md).

### Stage 2 — Quality gates
One standalone script per gate; **rerun all gates before every delivery — never trust historical results**. Minimum gate set: data integrity → index/full-text consistency → size ledger → release static checks → mocked-wx behavioral assertions. Add the theme-token gate when a theming system exists. Criteria and rationale: [references/quality-gates.md](references/quality-gates.md).

### Stage 3 — Adversarial compliance review
What quality gates cannot catch is exactly what gets personal accounts rejected. Work through the checklist in [references/compliance.md](references/compliance.md): category red lines, induced sharing, sensitive APIs, content-sensitive wording, contact-info funnels, image copyright. Use `scripts/compliance_scan.py` for the first pass, then manually judge the context of every hit.

### Stage 4 — Theming and UX
Theming via CSS custom properties: global tokens on `page`, one `.theme-<id>` block per theme that only overrides variables, zero page-code changes when switching. Any theme with a background image must define a veil (dimming) variable. Use `scripts/check_theme.py` to prevent "half-applied themes". Design details: [references/theme-system.md](references/theme-system.md).

### Stage 5 — Interaction robustness and platform limits
Static gates pass while the app feels broken if interaction is wrong. Put `wx.setClipboardData` in one shared helper with a three-layer fallback (direct write → privacy-authorize retry → selectable-text overlay), because `rich-text` code blocks cannot be long-press-selected; never let authorization failure be a dead end. Debounce swipes (~260 ms) and block only the current gesture on code-area touch (boolean flag, not a 900 ms timestamp). Give vertical `scroll-view` a definite, content-adaptive height (never a constant half-screen box). Handle native-JS traps: iOS date parsing, 10-level page stack, `wx:key`, `setData` data paths. Run `scripts/check_interaction.py`. Details: [references/interaction-robustness.md](references/interaction-robustness.md), [references/platform-and-release.md](references/platform-and-release.md).

### Stage 6 — ICP filing and release
ICP filing remarks have a fixed craft (foreign terms must be explained, avoid a "service provider" tone, defuse trigger words). Rejection causes and a ready-to-adapt template: [references/compliance.md](references/compliance.md). On the WeChat side: pick the "Tools" category, declare privacy items exactly matching the APIs used, register custom analytics events, and show the ICP number once issued. Upload via the stable DevTools CLI (`cli.bat upload`), Nightly `wechatide`, or `miniprogram-ci`; bump the version in all three places. Remember: upload only creates a development version — submission and publish are manual console steps. Release paths and the verified CLI commands: [references/platform-and-release.md](references/platform-and-release.md).

## Scripts

| Script | Purpose | Usage |
| --- | --- | --- |
| `scripts/check_theme.py` | Theme-token gate: theme table ↔ WXSS blocks one-to-one, all required variables present, image themes have veils, images exist and are <100 KB, no stale selectors, no legacy brand colors | `python scripts/check_theme.py <miniprogram source dir>` |
| `scripts/compliance_scan.py` | Compliance first pass: network/external links, sensitive APIs, induced sharing, ad-law superlatives, medical-sensitive wording, contact funnels, monetization wording | `python scripts/compliance_scan.py <miniprogram source dir> [content data dirs...]` |
| `scripts/check_interaction.py` | Interaction gate: clipboard fallback present, a copy entry exists somewhere in the project (read-only detail pages are legitimate), `wx:key` on lists, no iOS-unsafe date literal; REVIEW for scroll height / swipe debounce / timestamp blackout | `python scripts/check_interaction.py <miniprogram source dir>` |

All three scripts are **screening gates, not verdicts**: they list hits for human context judgment ("唯一" inside a "unique/dedup" code example is not an ad-law violation; a REVIEW scroll-height item may be an intentional non-scrolling block). Do not treat them as auto-approve/auto-reject.

## Quick pitfall index (full list in references/quality-gates.md and interaction-robustness.md)

1. Copy code fails: `rich-text` cannot be long-press-selected, and privacy-authorize failure with no fallback = 100% failure → three-layer fallback with selectable-text overlay
2. Swipe swallowed after scrolling code → 900 ms timestamp blackout; use a boolean flag cleared at gesture end + ~260 ms debounce
3. Vertical `scroll-view` with only `max-height` does not scroll → write a definite JS-computed height (short code fits, long code scrolls inside); never a constant half-screen box
4. Hardcoded brand colors scattered across page styles → half-blue/half-purple after re-theming; replace globally and gate the old values
5. Detail-page template drifting from subpackage copies → single source of truth + scripted distribution
6. AI-generated images keep the vendor watermark → crop before compressing; manually verify every image (no text/faces/brands)
7. Clearing data without resetting persisted state (theme, nav bar, tabBar) → state jumps on next entry
8. List page recomputing unconditionally in `onShow` → returning from detail collapses pagination, feels like a jump to top
9. iOS `new Date('YYYY-MM-DD')` = NaN, page stack > 10 fails silently → parse with `new Date(y,m-1,d)`, use redirectTo/switchTab
10. "Tap to view full image" that only navigates to detail → copy does not match behavior; use `previewImage` or fix the copy
11. Writing filing remarks like product copy → unexplained foreign terms and un-defused trigger words; rejection guaranteed
12. Highlighted code rendered with `rich-text` collapses `\n` into one space → code becomes a single line, has no real height and `scroll-y` cannot scroll; render line by line with one `<text>` per line (see interaction-robustness.md §9). Static gates stay green — only the rendered content is broken.
