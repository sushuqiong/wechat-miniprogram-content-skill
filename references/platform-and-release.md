# Platform Hard Limits and Release Paths

A second source of "the code is correct but the app will not ship" is platform limits and toolchain mechanics. This chapter pins the numbers that AI training data tends to get wrong, and the three real paths to upload a mini program — with the concrete CLI that was verified on a Windows machine.

## Contents

1. Hard limits (pin these as constants)
2. Account / subject capability boundaries
3. The three upload paths (DevTools CLI / Nightly wechatide / miniprogram-ci)
4. The verified stable-CLI workflow (Windows)
5. Version-number discipline
6. What CLI cannot do — the manual console steps

## 1. Hard limits (pin these as constants)

| Limit | Value | Consequence |
| --- | --- | --- |
| Main package | 2 MB | Keep a buffer (target 1950 KB); size ledger gate |
| Each subpackage | 2 MB | Split content roughly evenly |
| Page stack (`navigateTo`) | 10 levels | Beyond it fails **silently** — use redirectTo / switchTab |
| Cloud DB client query | 20 records/call | Paginate; do not assume a full-table read |
| Concurrent requests | 10 | Queue excess |
| Cloud function invocation timeout | 60 s (cloud-call) | Split long jobs |
| iOS `new Date('YYYY-MM-DD ...')` | `NaN` | Replace `-` with `/` before parsing |

These are deliberately boring facts; write them into a reference file rather than trusting the model's memory, which may reflect outdated base-library behavior.

## 2. Account / subject capability boundaries

For a **personal (individual) account** (the scope of this skill):

- Regulated categories (medical, finance, credentialed education, news, social) are unavailable. Content may *teach* a technical/medical-statistics topic, but the app must not select the medical category and must carry a learning-only disclaimer.
- No WeChat Pay, no UGC, no诱导分享 (share-to-unlock / collect-likes / follow-to-claim).
- Privacy guide must list exactly the APIs used. Clipboard (`setClipboardData`) must be declared if the privacy check is enabled.

Enterprise accounts lift some of these; only the gates and theming sections port directly. (Platform rules evolve — the 2026 iOS virtual-payment change is irrelevant to content apps; always re-check the latest official docs before release.)

## 3. The three upload paths

1. **Stable DevTools CLI** (`cli.bat` on Windows) — simplest, verified on a real machine. Requires an interactive login (QR scan once) but **no upload private key and no IP whitelist**. This is the recommended default for a solo developer with the stable DevTools installed.
2. **Nightly `wechatide` skills/MCP** (Tencent CloudBase official path) — preferred when doing AI-driven debugging/preview/upload with the Nightly build. Tools like `project_open_window`, `simulator_open_page`, `get_app_console_content`, `create_preview_qrcode`, `miniprogram_upload`. Requires the Nightly build; a missing `wechatide` is a one-time install gap, not an environment limit.
3. **`miniprogram-ci`** (Node) — programmatic fallback when DevTools is unavailable. Requires three things the CLI path does not: **appid**, a **code-upload private key**, and an **IP whitelist** configured in the console. Cannot replace simulator/console/network inspection.

Rule of thumb: stable CLI for shipping, Nightly wechatide for AI debugging, miniprogram-ci for headless CI only.

## 4. The verified stable-CLI workflow (Windows)

DevTools installed at `E:\微信web开发者工具\` (CLI = `cli.bat`), IDE service port `27006`.

```bash
# 1. Confirm login (reg.exe warnings are harmless on some locked-down machines)
"E:/微信web开发者工具/cli.bat" islogin --port 27006
# -> {"login":true}; if false: "E:/微信web开发者工具/cli.bat" login --port 27006  (scan QR)

# 2. Upload a new development version
"E:/微信web开发者工具/cli.bat" upload \
  --project "C:/.../小程序源码" \
  -v "1.0.2" \
  -d "v1.0.2 copy fallback, HD preview, swipe fixes" \
  --port 27006
# EXITCODE=0 and a printed AppID / package sizes means success
```

Notes learned the hard way:
- Use **English** for the `-d` remark on Windows — Chinese text passed through `cmd` can be mojibake in the console.
- Same version number overwrites the existing development version; that is the intended way to re-upload after a fix.
- Verify the `appid` in `project.config.json` before upload when maintaining two sibling apps — uploading the wrong app is an easy mistake.
- The `reg.exe` "blocked by security policy" warning is cosmetic; the CLI still works when `islogin` returns true.

**Do not** confuse a web deploy / preview-card tool with a mini-program upload. A publishing tool that returns `deployed:false` or only produces a preview card is NOT uploading to WeChat. The only real upload is the DevTools CLI (or Nightly / miniprogram-ci above).

## 5. Version-number discipline

- Bump the version in **three** places together: `config.js` `VERSION`, `config.js` CHANGELOG head entry, and the `app.js` header comment.
- Add a new CHANGELOG entry; if the project keeps "recent two versions only", drop the oldest.
- **Historical version strings in comments and older CHANGELOG entries are history — do not rewrite them.**
- Rerun all gates after bumping, before upload.

## 6. What CLI cannot do — the manual console steps

Upload creates a **development version** only. The following have no CLI interface and must be done by a human in the mp console:

1. Version management → select the development version → **提交审核** (submit for review).
2. After approval → **发布** (publish).
3. Console prerequisites before first submit: choose category (Tools / fitting information type), fill the privacy guide to match APIs used, register `wx.reportEvent` custom events (otherwise they are not reported), and show the ICP number once issued (hide the footer entry while empty).

Always tell the user these manual steps explicitly after an upload — "uploaded" does not mean "live".
