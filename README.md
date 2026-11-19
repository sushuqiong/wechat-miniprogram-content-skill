# WeChat Mini Program Content Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-WeChat%20Mini%20Program-07C160.svg)](https://developers.weixin.qq.com/miniprogram/en/dev/)

**A field playbook and toolchain for shipping content-focused WeChat Mini Programs under a personal (individual) developer account.**

`wechat-miniprogram-content-skill` is a reusable AI-agent skill plus three standalone gate scripts, distilled from a real shipped project: a 365-card bioinformatics code-card mini program with 10 categories, a daily-card feature, two subpackages, 9 themes, and 16 automated quality gates. It covers the full journey — content pipeline, quality gates, adversarial compliance review, CSS-variable theming, interaction robustness, platform hard limits, and ICP filing + release.

![Six-stage workflow](assets/workflow.svg)

## Highlights

- **Offline-first by design**: zero `wx.request`, zero `web-view` — one architectural decision that removes most of the compliance surface, at the price of a strictly managed 2 MB package budget.
- **Gates as the specification**: every rule is a runnable script; all gates are re-executed before every delivery, never trusted from history.
- **Compliance treated as adversarial**: the things automated tests cannot catch — category red lines, induced sharing, ICP remark wording — are exactly what gets personal accounts rejected, so they get their own checklist and scanner.
- **Theming as variable overrides**: one `.theme-<id>` block per theme, zero page-code changes per skin, with a gate that prevents "half-applied themes".
- **Interaction robustness**: the copy-code three-layer fallback, swipe debounce, scroll-view and native-JS/iOS traps that static gates cannot see — plus a gate that screens for them.
- **Release paths made concrete**: stable DevTools CLI (verified on Windows), Nightly `wechatide`, and `miniprogram-ci`, with platform hard limits pinned as constants.
- **Original images only**: content figures are produced by the content code itself; atmosphere images are originally generated, watermark-cropped, and manually verified — no scraped web images, ever.

## What it helps you answer

- How do I fit hundreds of content items into a 2 MB main package without breaking over time?
- How do I guarantee hundreds of content entries stay complete, consistent, and correctly routed?
- Why did my mini program pass all tests but still get rejected in review?
- How do I write ICP filing remarks (备案备注) that do not trigger a phone call from the reviewer?
- How do I build multi-theme skinning that stays maintainable instead of "change one thing, break three"?
- What can a personal-account mini program legally do — and what must be designed around on day one?

## Why this is different

- It is **distilled from a shipped project**, not written in the abstract — every rule exists because something actually broke or got rejected.
- It treats **compliance as a first-class engineering stage**, with a scanner and a checklist, instead of a pre-release afterthought.
- It encodes **originality-safe asset pipelines**: no scraped images, no copied icon packs, watermark-cropped generated art.
- It ships **runnable gates**, not just prose: two Python scripts you can wire into CI today.

## Workflow

```mermaid
flowchart LR
    A["1. Content pipeline<br/>topic matrix · schedule<br/>two-layer data · size ledger"] --> B["2. Quality gates<br/>order · consistency · size<br/>runtime · theme · interaction"]
    B --> C["3. Compliance review<br/>category red lines · APIs<br/>induced sharing · copyright"]
    C --> D["4. Theming & UX<br/>CSS variable tokens<br/>one block per theme"]
    D --> E["5. Interaction robustness<br/>copy fallback · swipe<br/>scroll · native-JS pitfalls"]
    E --> F["6. Filing & release<br/>ICP remark · privacy<br/>CLI / wechatide · version"]
```

## Repository contents

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Main agent skill: six-stage workflow, core judgments, script usage, pitfall index |
| `references/methodology.md` | Content pipeline: topic matrix, two-layer data, subpackages, illustration pipeline, template distribution |
| `references/quality-gates.md` | The seven-gate system with per-gate criteria + a real-world pitfall list |
| `references/compliance.md` | Personal-account red lines, scan checklist, ICP remark template (from a real rejection case), release tasks |
| `references/theme-system.md` | Theme-token design, three hard rules, background-image handling, UX differentiation checklist |
| `references/interaction-robustness.md` | Copy three-layer fallback, rich-text limitation, swipe/scroll fixes, native-JS/iOS pitfalls |
| `references/platform-and-release.md` | Platform hard limits, account boundaries, DevTools CLI / wechatide / miniprogram-ci, version discipline |
| `scripts/check_theme.py` | Theme-token gate: 7 criteria, exit-code driven |
| `scripts/compliance_scan.py` | Compliance first pass: HIGH-RISK vs REVIEW tiers, exit-code driven |
| `scripts/check_interaction.py` | Interaction gate: 4 FAIL criteria + 3 REVIEW items, exit-code driven |
| `assets/` | Diagrams used in this README |

## Quick start

Requirements: Python 3.8+ (no third-party dependencies).

Run the theme-token gate against any mini program that uses `utils/theme.js` + `app.wxss`:

```bash
python scripts/check_theme.py /path/to/miniprogram-source
```

Run the compliance first pass (add content-data directories to scan bundled copy):

```bash
python scripts/compliance_scan.py /path/to/miniprogram-source /path/to/content-data
```

Run the interaction gate (copy fallback, list keys, iOS dates; scroll/debounce as REVIEW):

```bash
python scripts/check_interaction.py /path/to/miniprogram-source
```

All three scripts exit non-zero when a FAIL criterion is hit, so they drop straight into CI or a pre-commit hook.

## Example use cases

| Situation | Command / action | What you get |
| --- | --- | --- |
| You added a 10th theme and want to be sure nothing is half-wired | `python scripts/check_theme.py <src>` | Missing variables, stale selectors, oversized images — with file-level detail |
| You are about to submit for review | `python scripts/compliance_scan.py <src> <data>` | HIGH-RISK items (must be zero) + REVIEW items with context for human judgment |
| Your ICP filing was rejected over remark wording | read `references/compliance.md` §4 | The four rejection causes and a ready-to-adapt remark template |
| Copy-code fails or "long-press to copy" does nothing | read `references/interaction-robustness.md` §1-2 + run `check_interaction.py` | The three-layer fallback and selectable-text overlay; rich-text cannot be selected |
| Swipes get swallowed after scrolling code, or scroll-view will not scroll | read `references/interaction-robustness.md` §3-4 | Boolean `_noSwipe` + debounce; fixed height for vertical scroll-view |
| You need to upload / re-upload a build from the command line | read `references/platform-and-release.md` §3-6 | Verified `cli.bat upload` commands, version-bump discipline, manual console steps |
| You are designing a second app in the same family | read `references/theme-system.md` §5 | Six deliberate UX differentiation moves to avoid a "reskin" impression |

## Use as an AI-agent skill

Copy this repository into your agent's skills directory (e.g. `~/.workbuddy/skills/`, `~/.claude/skills/`, or a project-level equivalent). The agent will load it when you ask to build, review, re-theme, or publish a content mini program.

Example prompts:

```
Build a 100-card vocabulary mini program for personal release; follow the offline-first shape and set up all quality gates.
```

```
Review my mini program for compliance risks before I submit it — category, induced sharing, privacy, and image copyright.
```

Chinese examples:

```
用这套方法论帮我开发一个个人主体的每日一句小程序，内容 365 条，发布前把门禁都建好。
```

```
我的备案被驳回了，说备注里 Julia 没解释清楚，帮我按模板重写一版备注。
```

## The seven quality gates

1. **check_order** — schedule sanity: no duplicates/gaps, spacing, difficulty progression
2. **check_consistency** — index ↔ full-text ↔ routing ↔ images all agree
3. **check_milestone_sum** — package size ledger against the 1950 KB / 2048 KB lines
4. **check_release** — static release checks: syntax, WXML balance, event bindings, asset existence, no webp
5. **runtime_check** — behavioral assertions driving the *real* page code through a mocked `wx`
6. **check_theme** — theme-token integrity (this repo ships a generic version in `scripts/`)
7. **check_interaction** — interaction robustness (this repo ships a generic version in `scripts/`)

![Theme tokens](assets/theme-tokens.svg)

## Related work and acknowledgements

This skill's core is distilled from real shipped projects. The interaction, platform-limit and release chapters were sharpened against public community practice, in particular:

- [upgiorgio/wechat-miniprogram-ai-dev](https://github.com/upgiorgio/wechat-miniprogram-ai-dev) — the ten-step AI-dev method with per-step gates and a platform-hard-limits reference (methodology credited to the original thread by @shangdu2005).
- [Gourdbaby/wechat-miniprogram-skill](https://github.com/Gourdbaby/wechat-miniprogram-skill) — native-JS rules and bug-prevention list (iOS dates, page stack, `setData` data paths, `wx:key`).
- [TencentCloudBase/CloudBase-MCP](https://github.com/TencentCloudBase/CloudBase-MCP) — the official `miniprogram-development` skill and its debug/preview/upload guidance (Nightly `wechatide`, `miniprogram-ci` fallback).

These are credited as references only; the runnable gates and checklists here remain the original work of this repository.

## Scope and disclaimer

- Written for **personal (individual) accounts** shipping content/tool mini programs. Enterprise accounts, payments, and UGC carry different obligations; only the gates and theming sections apply directly.
- The compliance checklist reflects WeChat review and ICP filing practice as of 2026. Platform rules change — always confirm against the latest official documentation before release.
- This project offers engineering guidance; it is not legal advice.

## Contributing

Issues and PRs are welcome — especially new gate criteria, additional compliance patterns from real rejection cases, and translations of the checklists.

## Reading path

1. [SKILL.md](SKILL.md) — the workflow and core judgments
2. [references/methodology.md](references/methodology.md) — the content pipeline
3. [references/quality-gates.md](references/quality-gates.md) — gates and pitfalls
4. [references/compliance.md](references/compliance.md) — red lines and ICP craft
5. [references/theme-system.md](references/theme-system.md) — theming and UX
6. [references/interaction-robustness.md](references/interaction-robustness.md) — copy / swipe / scroll / native-JS
7. [references/platform-and-release.md](references/platform-and-release.md) — limits / CLI / version
8. Run the three scripts on a real project

## Keywords

`WeChat Mini Program` · `personal developer account` · `content app` · `quality gates` · `compliance review` · `ICP filing` · `CSS variable theming` · `offline-first` · `copy fallback` · `clipboard privacy` · `swipe gesture` · `DevTools CLI` · `agent skill`

## License

MIT © [sushuqiong](https://github.com/sushuqiong)
