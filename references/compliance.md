# Adversarial Compliance Review: Personal-Account Red Lines, Scan Checklist, and ICP Filing Craft

All-green automated tests ≠ approvable. Quality gates cannot see regulatory compliance and review-rejection risk — which is exactly where personal accounts get stuck. This chapter is organized as: account red lines → scan checklist → filing → release configuration.

## Contents

1. Hard boundaries of a personal account (design around them on day one)
2. Adversarial scan checklist (with grep patterns)
3. Image copyright: why scraped web images are banned
4. ICP filing remarks (with a real rejection case)
5. Four manual release tasks on the WeChat side

## 1. Hard boundaries of a personal account

- **Categories**: medical, finance, credentialed education, news, social and similar categories are unavailable to personal accounts. Pick "Tools" (工具) or a fitting information category for a content app; the content may include medical-statistics teaching examples, but **do not touch the medical category**, and include a "for learning only, not medical advice" disclaimer in the app.
- **No payments**: personal accounts cannot use WeChat Pay — no selling, tipping, or paid unlocking of any kind.
- **No UGC**: no user-posted content (comments, uploads, posts), or you inherit content-security review obligations.
- **No inducement**: "share to unlock", "collect likes", "follow the official account to receive materials" and similar inducement patterns are banned. Sharing must use the standard `open-type="share"`; sharing is a right, never a task.

## 2. Adversarial scan checklist

Run scripts/compliance_scan.py for the first pass, then manually judge every hit's context. Judgment principles per item:

| Item | What to scan | Judgment principle |
| --- | --- | --- |
| Network & external links | `wx.request` / `web-view` / `downloadFile` / `http(s)://` | An offline app should have zero hits; any hit pulls in domain whitelisting and content-security obligations |
| Sensitive APIs | `getUserProfile` / `getLocation` / `getPhoneNumber` / `chooseAddress` / `getWeRunData`, etc. | Anything used must be declared in the privacy guide; clipboard must go through `wx.requirePrivacyAuthorize` with a denial fallback |
| Inducement wording | 分享得 / 必须分享 / 分享后解锁 / 集赞 / 助力 / 关注领取 ("share to get", "must share", "collect likes", "boost", "follow to claim") | Zero tolerance |
| Ad-law superlatives | 最好 / 最强 / 第一 / 唯一 / 顶级 / 100% / 永久 ("best", "strongest", "first", "only", "top-tier", "100%", "permanent") | **Context matters**: "第一行代码" (first line of code) and "唯一去重" (unique dedup) are technical usage, not violations; marketing copy is where they violate |
| Medical-sensitive wording | 诊断建议 / 治疗方案 / 用药建议 / 治愈 / 疗效 / 问诊 ("diagnosis advice", "treatment plan", "medication advice", "cure", "efficacy", "consultation") | Teaching-example context + disclaimer is acceptable; no feature may be phrased as giving health advice to the user |
| Contact funnels | 微信号 / QQ / 公众号 / 二维码 / 加群 / 私信 and variants (V信/vx) | Funneling users off-platform is a high-risk rejection cause |
| Monetization wording | 付费 / 购买 / 价格 / 打赏 / 广告 / 商务合作 ("paid", "purchase", "price", "tip", "ads", "business cooperation") | Should be zero hits for a personal account |

**Principle: a word-list hit is not a violation — everything depends on context; but every hit must have a human confirmation record. Scanning without reviewing does not count.**

## 3. Image copyright: why scraped web images are banned

Personal accounts have no legal buffer. Unlicensed web images are the two most frequent causes of copyright complaints and review rejections. Rules:

- Content images: actually produced by the content code (figure-code consistency, clean copyright).
- Atmosphere/background images: original generation or self-drawn. After AI generation you must crop the watermark, compress, and manually verify every image (no text / no recognizable faces / no third-party brands). See references/methodology.md.
- Icons: use built-in unicode symbols or self-drawn SVG; do not lift image assets from third-party icon libraries (iconfont fonts require license checks).

## 4. ICP filing remarks (with a real rejection case)

Filing remarks (备案备注) are not product copy — they are a "service description" written for the reviewer. Real case: the remark read "提供生物信息学Julia语言代码卡片查询服务：365张卡片覆盖……" and the reviewer called to say "the wording is unsafe — you must explain what Julia is".

Four rejection causes and their fixes:

1. **Unexplained foreign terms/abbreviations** → explain every foreign word on first use, in parentheses: "Julia 指 Julia 编程语言（一种用于科学计算的开源计算机编程语言）".
2. **A "service provider" tone** (提供××服务) → for a personal non-commercial filing, write "个人开发的学习参考工具，仅提供静态内容展示" (a personal learning-reference tool, static content display only).
3. **Un-defused trigger words** (机器学习/AI, etc.) → keep the term but add the cover: "内容为预先编写的静态图文，不含人工智能生成内容，不涉及算法推荐" (pre-written static content, no AI-generated content, no algorithmic recommendation).
4. **Obscure domain terms** (e.g. 生物信息学/bioinformatics) → also explain in one parenthesized sentence, to avoid a second verification call.

Ready-to-adapt template (fill the braces, keep the disclaimers truthful):

> 本小程序为个人开发的编程学习参考工具，仅提供静态内容展示。{外文术语}指{解释}。小程序内展示{N}张{领域}（指{领域一句话解释}）{内容形态}，内容涵盖{场景列举}，用户可按分类、关键词查阅，并可收藏。所有内容均为预先编写的静态图文，不含人工智能生成内容，不涉及算法推荐、用户注册、用户发布信息、课程售卖、在线支付及任何交易行为。

Warning: **the remarks must match the app's actual functionality**. Verify every "does not involve" claim in the code before writing it down.

## 5. Four manual release tasks on the WeChat side

1. **Category**: pick "Tools" (工具) or a fitting information category; never touch credentialed categories.
2. **Privacy guide**: check exactly the APIs actually used (e.g. clipboard); the purpose text must match code behavior.
3. **Custom analytics**: events sent via `wx.reportEvent` must be registered in the console, or they are not reported (this affects data, not approval).
4. **Filing number display**: after the ICP number is issued, put it into the config and show it in the footer (hide the entry while empty — no blank rows before issuance).
