---
name: wechat-miniprogram-content-app
description: End-to-end playbook for building content-focused WeChat Mini Programs under an individual (personal) developer account — code cards, knowledge cards, question banks, daily-card apps, and other read-only, offline-first mini programs. Covers content data pipelines and subpackage size budgets, automated quality gates (including mocked-wx behavioral assertions), adversarial compliance review for personal accounts (category red lines, induced sharing, privacy, image copyright), a CSS-variable theming system, and the ICP filing + WeChat release workflow. Use when building, reviewing, re-theming, or publishing this kind of mini program, or when asked about personal-account restrictions, ICP filing rejections (备案驳回), mini program theming, or how to build quality gates for a mini program.
---

# Content-Focused WeChat Mini Programs (Personal Account) — Field Playbook

Distilled from a real shipped project: a 365-card bioinformatics code-card mini program with 10 categories, a daily-card feature, two subpackages, 9 themes, 16 automated gates, published under a personal account. This Skill is the reusable abstraction of that process.

## Core judgment: confirm the shape first

The first decision for a content mini program is **offline-first**: ship all content inside the package, zero `wx.request`, zero `web-view`. This single choice eliminates most of the compliance surface (domain whitelists, content-security APIs, network-related privacy declarations). The price is a hard 2 MB main-package budget that must be managed deliberately. Introduce networking only when content truly must update dynamically — and accept the full compliance obligations that come with it.

The second decision is **account boundaries**: personal accounts cannot select regulated categories (medical, finance, credentialed education), cannot use WeChat Pay, and cannot host user-generated content. Design around these on day one instead of deleting features later.

## Workflow (five stages, in order)

### Stage 1 — Content pipeline
Topic matrix (total × categories × difficulty) → production schedule (date mapping for daily cards) → two-layer data (index always in main package / full text in subpackages, loaded on demand) → illustrations produced by the content code itself (never scraped web images) → size ledger refreshed on every build. See [references/methodology.md](references/methodology.md).

### Stage 2 — Quality gates
One standalone script per gate; **rerun all gates before every delivery — never trust historical results**. Minimum gate set: data integrity → index/full-text consistency → size ledger → release static checks → mocked-wx behavioral assertions. Add the theme-token gate when a theming system exists. Criteria and rationale: [references/quality-gates.md](references/quality-gates.md).

### Stage 3 — Adversarial compliance review
What quality gates cannot catch is exactly what gets personal accounts rejected. Work through the checklist in [references/compliance.md](references/compliance.md): category red lines, induced sharing, sensitive APIs, content-sensitive wording, contact-info funnels, image copyright. Use `scripts/compliance_scan.py` for the first pass, then manually judge the context of every hit.

### Stage 4 — Theming and UX
Theming via CSS custom properties: global tokens on `page`, one `.theme-<id>` block per theme that only overrides variables, zero page-code changes when switching. Any theme with a background image must define a veil (dimming) variable. Use `scripts/check_theme.py` to prevent "half-applied themes". Design details: [references/theme-system.md](references/theme-system.md).

### Stage 5 — ICP filing and release
ICP filing remarks have a fixed craft (foreign terms must be explained, avoid a "service provider" tone, defuse trigger words). Rejection causes and a ready-to-adapt template: [references/compliance.md](references/compliance.md). On the WeChat side: pick the "Tools" category, declare privacy items exactly matching the APIs used, and register custom analytics events or they will not be reported.

## Scripts

| Script | Purpose | Usage |
| --- | --- | --- |
| `scripts/check_theme.py` | Theme-token gate: theme table ↔ WXSS blocks one-to-one, all required variables present, image themes have veils, images exist and are <100 KB, no stale selectors, no legacy brand colors | `python scripts/check_theme.py <miniprogram source dir>` |
| `scripts/compliance_scan.py` | Compliance first pass: network/external links, sensitive APIs, induced sharing, ad-law superlatives, medical-sensitive wording, contact funnels, monetization wording | `python scripts/compliance_scan.py <miniprogram source dir> [content data dirs...]` |

Both scripts are **screening gates, not verdicts**: they list hits for human context judgment ("唯一" inside a "unique/dedup" code example is not an ad-law violation). Do not treat them as auto-approve/auto-reject.

## Quick pitfall index (full list in references/quality-gates.md)

1. Hardcoded brand colors scattered across page styles → half-blue/half-purple after re-theming; replace globally and gate the old values
2. Detail-page template drifting from subpackage copies → single source of truth + scripted distribution
3. AI-generated images keep the vendor watermark → crop before compressing; manually verify every image (no text/faces/brands)
4. Clearing data without resetting persisted state (theme, nav bar, tabBar) → state jumps on next entry
5. List page recomputing unconditionally in `onShow` → returning from detail collapses pagination, feels like a jump to top
6. Writing filing remarks like product copy → unexplained foreign terms and un-defused trigger words; rejection guaranteed
