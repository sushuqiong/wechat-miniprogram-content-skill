# Interaction Robustness: Copy, Swipe, Scroll and Native-JS Pitfalls

All-green static gates still ship a broken app when the *interaction* is wrong. This chapter collects the interaction failures that actually happened in two shipped content mini programs, plus native-JS pitfalls confirmed against WeChat docs. Every rule here has a runnable check in `scripts/check_interaction.py` where statically decidable.

## Contents

1. Why "copy code" fails and the three-layer fallback
2. The selectable-text fallback layer
3. Swipe gesture vs code-area touch conflict
4. scroll-view needs a definite height (and should adapt to content)
5. Copy text must match behavior
6. Native-JS pitfalls that pass tests but break on device
7. Interaction gate criteria
8. One authoritative copy entry beats two half-working ones
9. rich-text collapses newlines: render highlighted code line by line

## 1. Why "copy code" fails and the three-layer fallback

Two independent root causes, both common:

- `rich-text` (used to render syntax-highlighted code) **does not support long-press-to-select**. "Long-press the code to copy" instructions are inert on any page whose code is rendered with `rich-text`.
- Privacy authorization: since base library 2.32+, `wx.setClipboardData` may be gated by `wx.requirePrivacyAuthorize`. If the app declares `__usePrivacyCheck__` or the console privacy guide lists the clipboard, an unauthorized call can silently fail. **The fatal pattern** is a copy function that, on `requirePrivacyAuthorize` failure, just calls `toast('copy failed')` and gives up — that is a 100% failure path when the console guide is incomplete.

The fix is a **three-layer fallback** in `utils/ux.js`, ordered so the most-likely-to-succeed path runs first and nothing depends on console configuration being complete:

```
1. wx.setClipboardData directly  -> success: haptic + "copied" toast + stat callback
2. on fail: wx.requirePrivacyAuthorize -> on success: retry wx.setClipboardData
3. on fail again: call current page's onShowCopyFallback(text)
   -> a <text user-select> overlay with the plain text, so the user can long-press-select
```

Why this order matters: writing to the clipboard is usually allowed even when reading is restricted, so the direct path succeeds on most devices; the authorization retry covers strict base libraries; the overlay covers the residual case with **no dependency on backend config**. Never make layer 2 the only path — that is the original bug.

Keep copy logic in ONE shared helper so every page (daily, detail, library) inherits the fix. Do not hand-roll `setClipboardData` in individual pages.

## 2. The selectable-text fallback layer

Add to every detail page that copies its own code (see section 8 for the alternative):

- WXML: a full-screen mask + card containing `<text class="cf-code" user-select>{{copyFallbackText}}</text>` and a close button. The `user-select` attribute is what makes long-press-select work.
- JS data: `copyFallbackText`, `showCopyFallback`; methods `onShowCopyFallback(text)` and `onHideCopyFallback()`.
- WXSS: `white-space: pre; word-break: break-all; user-select: text` on the code text, so formatting is preserved and long lines wrap.

On pages whose code is already `<text user-select>` (e.g. a daily card), the third layer can simply toast "long-press to copy" instead of showing an overlay — the text is selectable. The shared helper detects the page method via `getCurrentPages()` and falls back to a toast if the page did not implement the overlay.

## 3. Swipe gesture vs code-area touch conflict

Two distinct bugs appear together:

- **Timestamp blackout**: a code-area `catchtouchstart/catchtouchend` handler that sets `_codeAt = Date.now()`, with `onTouchEnd` refusing to swipe within 900 ms of that timestamp. Any legitimate swipe shortly after scrolling code is silently swallowed. Fix: use a boolean `_noSwipe` set on code touch and cleared at the **end** of `onTouchEnd` — this blocks exactly the current gesture, not the next 900 ms.
- **No debounce**: rapid taps fire several flips and the animation stutters. Add a ~260 ms lock (`_stepAt` + `_stepLocked()`) shared by button steps and swipe steps.

Event model to remember: `catchtouchstart` on the code area stops the event from bubbling to the page-root `bindtouchend`, so the code-area gesture never reaches the root handler — the extra timestamp guard is unnecessary and harmful. When the code area only scrolls for *long* code, prefer `bindtouchstart` (bubbles, so the page still records swipe coordinates) plus a conditional `_noSwipe` that is set only when `codeScrollable` is true. Short-code cards then keep normal swipe-to-flip.

Gesture thresholds that feel right: horizontal displacement >= 70 rpx, vertical displacement <= 60 rpx, gesture duration <= 600 ms. Tune with on-device testing.

## 4. scroll-view needs a definite height (and should adapt to content)

A vertical `scroll-view` whose container uses only `max-height: 820rpx` **does not scroll** on some base libraries — the component cannot compute a scroll range without a definite height. `max-height` alone is not enough; `height` must be set. A plain `view` with `overflow: hidden` and a `max-height` is worse: it silently **truncates** long code with no way to reach the rest.

A fixed `height: 58vh` fixes scrolling but creates the next complaint: short code sits in a half-screen empty dark box. Better: compute the height in JS from the code and write it as an inline style (`style="height:{{codeH}}rpx"`) — still a definite `height`, so scrolling works:

- Detail pages that still use `rich-text` + `white-space: pre` can use the exact newline count (`rows = code.split('\n').length`). **But see section 9: `rich-text` collapses `\n` unless you emit real line nodes — a "one-line" code block has no real height and `scroll-y` cannot scroll.** The recommended layout renders highlighted code line by line with nested `<text>` and wraps long lines, so use the same wrapped-row estimate as the home page, not the raw newline count.
- Home/daily pages usually wrap lines (`white-space: pre-wrap; word-break: break-all`), so estimate wrapped rows. Count CJK/full-width characters as 2 half-width units (`charCodeAt(i) > 127`), ASCII as 1, and divide by the container's per-line capacity (~50 half-width units at 22 rpx).
- Clamp to a floor (~160 rpx) and a ceiling (~600 rpx). Above the ceiling the region scrolls; set a `codeScrollable` flag so the code-area touch handler only suppresses swipe-to-flip when scrolling is actually possible.

This removes both truncation and the fixed-height blank area, while keeping action buttons in a stable position. Community references (Tencent Cloud scroll-view guide, uni-app/CSDN threads) consistently require: definite height for `scroll-y`, `white-space: nowrap` + `inline-block` children for `scroll-x`, `word-break` for long text, and explicit touch handling to avoid nested-scroll gesture conflicts. Note also that only `<text>` supports long-press selection — `rich-text` never does.

## 5. Copy text must match behavior

"If you tap the figure you can view the full image" must actually call `wx.previewImage` on the HD asset, not navigate to the detail page. Same class of bug as misleading filing remarks: the words and the behavior must agree. When a link only navigates, either fix the copy or implement the preview — never leave the mismatch.

## 6. Native-JS pitfalls that pass tests but break on device

Confirmed against WeChat docs and the native-JS skill community:

| Area | Rule |
| --- | --- |
| iOS dates | `new Date('2025-01-01 10:00')` is `NaN` on iOS. Replace `-` with `/` first: `new Date(s.replace(/-/g, '/'))`. |
| Page stack | `wx.navigateTo` stack cap is 10 levels; beyond that it **fails silently**. Use `wx.redirectTo` / `wx.switchTab` for deep flows; never rely on unlimited pushes. |
| setData performance | Use data paths for partial updates: `this.setData({ 'list[0].text': 'new' })`. Avoid re-setting whole large arrays. |
| WXML lists | Always put `wx:key` on `wx:for`; without it, list diffing misbehaves on reuse. |
| Event binding | `bind:tap` bubbles; `catch:tap` does not. When an inner control must not trigger the outer card, use `catch`. |
| Layout units | Use `rpx` for responsive sizing; BEM naming keeps WXSS predictable. |
| Components | Prefer `Component()` over `Page()` for reusable logic — better isolation and `setData` performance. |
| Async APIs | Wrap callback-style wx APIs in Promise / async-await, and always provide both success and fail handlers. |
| Tab pages | Switching to a tabBar page requires `wx.switchTab`; `navigateTo` to a tab page fails. |

Platform hard limits worth pinning as constants in the team's head: main package 2 MB, each subpackage 2 MB, page stack 10, cloud DB query 20 records/call on the client, concurrent requests 10, cloud-function invocation timeout 60 s. See `references/platform-and-release.md`.

**Adding images near the 2 MB ceiling**: when the main package is already at ~1.99 MB, do NOT add new image files. Reuse the images already in the package as list thumbnails (`<image src="{{item.image}}" mode="aspectFill" lazy-load>`) — visible image density increases, package size does not change, and there is no risk of "image does not match the card" because each thumbnail is that card's own figure. Never wire orphan/unused figures to unrelated cards.

## 7. Interaction gate criteria (`scripts/check_interaction.py`)

- **FAIL** if `wx.setClipboardData` appears anywhere but no `onShowCopyFallback` exists in the project (no selectable-text escape hatch).
- **FAIL** if a detail page renders code via `rich-text` and **no page in the project** exposes `onCopyCode` (a read-only detail page is fine when the daily/home page owns the single copy entry; see section 8). If the detail code is rendered line by line with `<text>` instead (section 9), this check does not fire — the same "single authoritative copy entry" rule applies.
- **FAIL** if a `wx:for` lacks `wx:key`.
- **FAIL** if `new Date('...-...-...')` string-literal pattern appears (iOS NaN).
- **REVIEW** if a `scroll-y` scroll-view's class only has `max-height` with no fixed `height`.
- **REVIEW** if a swipe/touch handler exists but no debounce marker (`_stepAt` / `_stepLocked` / `debounce` / `260`) is present.
- **REVIEW** if a `catchtouchstart` handler sets a timestamp-like guard flag (possible 900 ms blackout pattern).

Run: `python scripts/check_interaction.py <miniprogram source dir>` — exit 0 when all FAIL checks pass; REVIEW items are printed for human confirmation and do not fail the gate.

## 8. One authoritative copy entry beats two half-working ones

`rich-text` cannot be long-press-selected, and a pushed detail page is the worst place to recover from a `requirePrivacyAuthorize` failure: the user has already navigated, the clipboard write is gated, and the fallback overlay is a long-press-select UX that few users complete. If the detail page's copy button is unreliable in the field, the clean fix is to **remove copy from the detail page entirely** and keep one authoritative copy entry on the daily/home page, where the code is already a `<text user-select>` (selectable as a secondary path) and the direct `wx.setClipboardData` succeeds on most devices.

Checklist for this layout:

- Remove `onCopyCode` / `onCopyExample`, the `copied` states, the `cf-mask` fallback overlay and its WXSS from the detail template, then re-run the subpackage generator so both `pkgA/detail` and `pkgB/detail` stay byte-identical.
- Keep `user-select` on the detail page's plain-text sections (example / pitfall / R equivalent) so long-press selection still works. A non-code action such as "copy the official account name" may stay on the detail page.
- Keep the daily/home copy button and the shared three-layer `ux.copy` helper untouched.
- Update the runtime gate: assert the detail page no longer exposes `onCopyCode` and the daily page still writes to the clipboard.

This is a deliberate product decision, not a regression: one working copy entry is better than two entries where one silently fails. The interaction gate (section 7, F2) accepts it as long as some page still offers `onCopyCode`.

## 9. rich-text collapses newlines: render highlighted code line by line

The failure that survived a whole "adaptive height" release: the detail page rendered syntax-highlighted code as a `rich-text` node array (`<span style="color:...">`), with the entire code (including `\n`) inside the span text. `rich-text` renders its nodes by HTML rules — a literal `\n` and runs of spaces are **collapsed into a single space**. WXSS on the `<rich-text>` component itself (`white-space: pre`) does not reach the isolated internal nodes. Combined with `.code-block { white-space: nowrap }`, the result was:

- the whole card's code squeezed into ONE line, unreadable and off-screen;
- the content had no real multi-line height, so `scroll-y` had nothing to scroll — "cannot swipe up/down";
- `codeH` computed from `code.split('\n').length` produced a tall box with one line of text at the top — "lots of empty space".

All static gates passed (definite height, `wx:key`, no truncation CSS), because the bug is in the **rendered content**, not the layout. A green gate does not prove the code is visible.

Fix (keeps highlighting, removes the failure mode):

- Add a `toRows(code)` helper beside `toNodes(code)`: feed the same tokenizer, split every token's text on `\n`, start a new row at each break, merge same-colour adjacent fragments within a row, and give empty rows a single space placeholder so their line box does not collapse. Export both — keep `toNodes` because the "tokenizer does not swallow characters" gate uses it.
- WXML: one `<text class="code-line" wx:for="{{codeRows}}" wx:key="index">` per line, with nested `<text wx:for="{{item}}" wx:for-item="seg" wx:key="index" style="color:{{seg.color}}">{{seg.text}}</text>` for colours. `<text>` may only nest `<text>` — never a `view` — so put the wrapping `view` outside.
- WXSS: `.code-line { display:block; white-space:pre-wrap; word-break:break-all; ... }`. Each line is a block (guaranteed newline), indentation survives via inherited `pre-wrap`, and long lines wrap so `scroll-x` is unnecessary — drop it to avoid two-direction scroll conflicts. Keep `scroll-y` with the JS-computed `height`.
- Change the code-area touch handler from `catchtouchstart` to `bindtouchstart` + `_noSwipe`: `bind` bubbles to the page-root swipe handler (which records coordinates), and the boolean flag suppresses exactly that flip. `catch` on a scroll-view ancestor is a known cause of dead native scrolling.
- Estimate `codeH` with the wrapped-row formula (CJK = 2 units) on BOTH home and detail pages, so the estimate matches what is actually rendered.

Verification that actually catches this class of bug: run `toRows()` over every card and assert (a) `rows.length === code.split('\n').length`, (b) the concatenated text equals the source after ignoring whitespace, (c) every row has at least one fragment and every fragment has a colour. Add a runtime gate asserting `codeRows.length > 3` on a loaded detail page. Layout-only gates cannot detect collapsed content.
