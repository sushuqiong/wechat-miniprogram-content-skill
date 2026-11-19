# Interaction Robustness: Copy, Swipe, Scroll and Native-JS Pitfalls

All-green static gates still ship a broken app when the *interaction* is wrong. This chapter collects the interaction failures that actually happened in two shipped content mini programs, plus native-JS pitfalls confirmed against WeChat docs. Every rule here has a runnable check in `scripts/check_interaction.py` where statically decidable.

## Contents

1. Why "copy code" fails and the three-layer fallback
2. The selectable-text fallback layer
3. Swipe gesture vs code-area touch conflict
4. scroll-view needs a fixed height
5. Copy text must match behavior
6. Native-JS pitfalls that pass tests but break on device
7. Interaction gate criteria

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

Add to every detail page (the pages whose code is `rich-text`):

- WXML: a full-screen mask + card containing `<text class="cf-code" user-select>{{copyFallbackText}}</text>` and a close button. The `user-select` attribute is what makes long-press-select work.
- JS data: `copyFallbackText`, `showCopyFallback`; methods `onShowCopyFallback(text)` and `onHideCopyFallback()`.
- WXSS: `white-space: pre; word-break: break-all; user-select: text` on the code text, so formatting is preserved and long lines wrap.

On pages whose code is already `<text user-select>` (e.g. a daily card), the third layer can simply toast "long-press to copy" instead of showing an overlay — the text is selectable. The shared helper detects the page method via `getCurrentPages()` and falls back to a toast if the page did not implement the overlay.

## 3. Swipe gesture vs code-area touch conflict

Two distinct bugs appear together:

- **Timestamp blackout**: a code-area `catchtouchstart/catchtouchend` handler that sets `_codeAt = Date.now()`, with `onTouchEnd` refusing to swipe within 900 ms of that timestamp. Any legitimate swipe shortly after scrolling code is silently swallowed. Fix: use a boolean `_noSwipe` set on code touch and cleared at the **end** of `onTouchEnd` — this blocks exactly the current gesture, not the next 900 ms.
- **No debounce**: rapid taps fire several flips and the animation stutters. Add a ~260 ms lock (`_stepAt` + `_stepLocked()`) shared by button steps and swipe steps.

Event model to remember: `catchtouchstart` on the code area stops the event from bubbling to the page-root `bindtouchend`, so the code-area gesture never reaches the root handler — the extra timestamp guard is unnecessary and harmful.

Gesture thresholds that feel right: horizontal displacement >= 70 rpx, vertical displacement <= 60 rpx, gesture duration <= 600 ms. Tune with on-device testing.

## 4. scroll-view needs a fixed height

A vertical `scroll-view` whose container uses only `max-height: 820rpx` **does not scroll** on some base libraries — the component cannot compute a scroll range without a definite height. Fix: give the code block a fixed height (`height: 58vh; max-height: 820rpx;`). Short code occupies the full box; for code cards that is acceptable, and it is the precondition for correct scrolling.

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

## 7. Interaction gate criteria (`scripts/check_interaction.py`)

- **FAIL** if `wx.setClipboardData` appears anywhere but no `onShowCopyFallback` exists in the project (no selectable-text escape hatch).
- **FAIL** if any detail page renders code via `rich-text` yet has neither a copy button nor a fallback overlay.
- **FAIL** if a `wx:for` lacks `wx:key`.
- **FAIL** if `new Date('...-...-...')` string-literal pattern appears (iOS NaN).
- **REVIEW** if a `scroll-y` scroll-view's class only has `max-height` with no fixed `height`.
- **REVIEW** if a swipe/touch handler exists but no debounce marker (`_stepAt` / `_stepLocked` / `debounce` / `260`) is present.
- **REVIEW** if a `catchtouchstart` handler sets a timestamp-like guard flag (possible 900 ms blackout pattern).

Run: `python scripts/check_interaction.py <miniprogram source dir>` — exit 0 when all FAIL checks pass; REVIEW items are printed for human confirmation and do not fail the gate.
