# -*- coding: utf-8 -*-
"""compliance_scan.py -- Compliance first-pass scanner for personal-account WeChat Mini Programs.

Usage:
    python compliance_scan.py <miniprogram source dir> [content data dirs...]

Positioning: this is a SCREEN, not a VERDICT. Word-list hits must be judged by a human
in context -- "第一" inside "第一行代码" (first line of code) is not an ad-law violation.
Hits are grouped into [HIGH-RISK] (should be zero) and [REVIEW] (context-dependent);
exit code is 1 whenever any HIGH-RISK hit exists.

The source dir is scanned for .js/.wxml/.wxss/.json; optional data dirs are scanned for
.js/.json only, to cover bundled content such as card copy.
"""
import io, os, re, sys

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

APP = os.path.abspath(sys.argv[1])
DATA_DIRS = [os.path.abspath(d) for d in sys.argv[2:]]

# ---- rules: (level, category, regex, guidance) ----
RULES = [
    ('HIGH-RISK', 'network request', r'wx\.request|wx\.downloadFile|wx\.uploadFile|<web-view',
     'an offline app should have zero; networking pulls in domain whitelists + content-security duties'),
    ('HIGH-RISK', 'external link', r'https?://(?!developers\.weixin|mp\.weixin|res\.wx)',
     'no external links in business code (documentation domains in comments excepted)'),
    ('HIGH-RISK', 'induced sharing', '分享得|必须分享|分享后.*解锁|转发.*解锁|集赞|助力|关注.*领取|邀请.*好友.*奖',
     'zero tolerance -- any hit is a violation'),
    ('HIGH-RISK', 'contact funnel', r'微信号|微信[:：]|QQ群|QQ号|扣扣|[Vv]信(?![a-zA-Z])|二维码|加群|私信我|星球|公众号[:：]',
     'funneling users off-platform is a high-risk rejection cause'),
    ('HIGH-RISK', 'monetization wording', '付费|购买|打赏|赞赏|商务合作|价格[:：￥¥]',
     'personal accounts have no payment capability; expect zero hits'),
    ('HIGH-RISK', 'sensitive API', r'getUserProfile|getUserInfo|getLocation|getPhoneNumber|chooseAddress|chooseContact|getWeRunData',
     'anything used must be declared in the privacy guide; confirm it is truly needed'),
    ('REVIEW', 'clipboard', r'setClipboardData',
     'must go through wx.requirePrivacyAuthorize with a denial fallback'),
    ('REVIEW', 'ad-law superlative', '最好|最强|第一|唯一|顶级|国家级|世界级|100%|百分百|永久|全网最|史上',
     'context matters: "第一行代码" / "唯一去重" are technical usage, not violations'),
    ('REVIEW', 'medical-sensitive', '诊断建议|治疗方案|用药建议|临床治疗|治愈|疗效|问诊|体检报告',
     'teaching examples + disclaimer are acceptable; no feature may give health advice'),
    ('REVIEW', 'politically sensitive', '赌博|博彩|彩票|色情|枪支|毒品|翻墙|VPN|科学上网',
     'expect zero for a content app; watch context for technical terms like VPN'),
    ('REVIEW', 'mini-program jump', r'navigateToMiniProgram',
     'cross-app jumps must be declared in app.json and accepted by the target; plain text mention without a jump is safe'),
    ('REVIEW', 'share implementation', r'onShareAppMessage|onShareTimeline',
     'confirm it is plain sharing (returns title/path) with no unlock condition'),
]

CODE_EXT = ('.js', '.wxml', '.wxss', '.json')
DATA_EXT = ('.js', '.json')

# content-word rules do not apply to style files (width:100% is CSS, not copy)
WORD_CATS = ('ad-law superlative', 'medical-sensitive', 'politically sensitive',
             'contact funnel', 'monetization wording', 'induced sharing')

CTX = 30  # context radius around a hit


def iter_files(root, exts):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
        for fn in files:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def scan(roots, exts):
    """Returns {level: [(category, file, line_no, hit, context, guidance)]}"""
    hits = {'HIGH-RISK': [], 'REVIEW': []}
    for root in roots:
        for p in iter_files(root, exts):
            try:
                lines = io.open(p, encoding='utf-8', errors='replace').read().splitlines()
            except OSError:
                continue
            rel = os.path.relpath(p, APP)
            for ln, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('*'):
                    continue
                for level, cat, pat, tip in RULES:
                    if p.endswith('.wxss') and cat in WORD_CATS:
                        continue
                    m = re.search(pat, line, re.I)
                    if m:
                        ctx = line[max(0, m.start() - CTX):m.end() + CTX].strip()
                        hits[level].append((cat, rel, ln, m.group(0), ctx, tip))
    return hits


all_hits = scan([APP], CODE_EXT)
if DATA_DIRS:
    data_hits = scan(DATA_DIRS, DATA_EXT)
    for lv in all_hits:
        all_hits[lv].extend(data_hits[lv])

print('=' * 70)
print('Compliance first-pass report  target: ' + APP)
print('=' * 70)

for level in ('HIGH-RISK', 'REVIEW'):
    items = all_hits[level]
    by_cat = {}
    for it in items:
        by_cat.setdefault(it[0], []).append(it)
    print('\n[%s] %d hit(s)' % (level, len(items)))
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        print('  %-22s %3d  -- %s' % (cat, len(rows), rows[0][5]))
        for _, rel, ln, word, ctx, _ in rows[:5]:
            print('    %s:%s  hit "%s"  ...%s...' % (rel, ln, word, ctx))
        if len(rows) > 5:
            print('    ... %d more' % (len(rows) - 5))

n_high = len(all_hits['HIGH-RISK'])
print('\n' + ('HIGH-RISK hits found -- resolve every one before release.'
             if n_high else
             'No HIGH-RISK hits; please manually confirm the context of every REVIEW item.'))
sys.exit(1 if n_high else 0)
