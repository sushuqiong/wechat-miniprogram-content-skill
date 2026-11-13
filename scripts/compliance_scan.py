# -*- coding: utf-8 -*-
"""compliance_scan.py —— 个人主体微信小程序合规静态初筛

用法:
    python compliance_scan.py <小程序源码目录> [内容数据目录...]

定位：这是「初筛」不是「裁判」。词表命中必须人工核对上下文——
技术语境里的「唯一/第一/最好」不违规，宣传语里才违规。
脚本把命中按【高危】（原则上应为零）与【核对】（看语境）分级输出，
有任何【高危】命中时退出码为 1。

源码目录扫描 .js/.wxml/.wxss/.json；内容数据目录（可选）只扫 .js/.json，
用于覆盖打包进小程序的卡片文案等数据文件。
"""
import io, os, re, sys

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

APP = os.path.abspath(sys.argv[1])
DATA_DIRS = [os.path.abspath(d) for d in sys.argv[2:]]

# ---- 规则表：(级别, 类别, 正则, 判定提示) ----
RULES = [
    ('高危', '网络请求', r'wx\.request|wx\.downloadFile|wx\.uploadFile|<web-view',
     '离线应用应为零；有网络即引入域名白名单与内容安全义务'),
    ('高危', '外部链接', r'https?://(?!developers\.weixin|mp\.weixin|res\.wx)',
     '业务代码里不应出现外链（文档注释域名除外）'),
    ('高危', '诱导分享', '分享得|必须分享|分享后.*解锁|转发.*解锁|集赞|助力|关注.*领取|邀请.*好友.*奖',
     '零容忍，命中即违规'),
    ('高危', '联系方式引流', r'微信号|微信[:：]|QQ群|QQ号|扣扣|[Vv]信(?![a-zA-Z])|二维码|加群|私信我|星球|公众号[:：]',
     '小程序内引流站外是高危驳回项'),
    ('高危', '商业化词', '付费|购买|打赏|赞赏|商务合作|价格[:：￥¥]',
     '个人主体无支付能力，应为零命中'),
    ('高危', '敏感API', r'getUserProfile|getUserInfo|getLocation|getPhoneNumber|chooseAddress|chooseContact|getWeRunData',
     '用到即需在隐私指引声明；确认真实需要'),
    ('核对', '剪贴板', r'setClipboardData',
     '必须走 wx.requirePrivacyAuthorize 且拒绝后有降级提示'),
    ('核对', '广告法极限词', '最好|最强|第一|唯一|顶级|国家级|世界级|100%|百分百|永久|全网最|史上',
     '看语境：「第一行代码」「唯一去重」等技术语境不违规'),
    ('核对', '医疗敏感词', '诊断建议|治疗方案|用药建议|临床治疗|治愈|疗效|问诊|体检报告',
     '教学示例+免责声明可接受；不得有对用户健康给建议的功能表述'),
    ('核对', '政治敏感词', '赌博|博彩|彩票|色情|枪支|毒品|翻墙|VPN|科学上网',
     '内容型应用应为零；技术词 VPN 等注意语境'),
    ('核对', '小程序跳转', r'navigateToMiniProgram',
     '互跳需在 app.json 声明且对方同意；静态文字提及无跳转则无风险'),
    ('核对', '分享实现', r'onShareAppMessage|onShareTimeline',
     '确认是纯分享（返回 title/path），不带解锁条件'),
]

CODE_EXT = ('.js', '.wxml', '.wxss', '.json')
DATA_EXT = ('.js', '.json')

CTX = 30  # 命中上下文截取半径


def iter_files(root, exts):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
        for fn in files:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def scan(roots, exts, label):
    """返回 {级别: [(类别, 文件, 行号, 命中, 上下文, 提示)]}"""
    hits = {'高危': [], '核对': []}
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
                    # 内容词类规则不扫样式文件（width:100% 之类是样式不是文案）
                    if p.endswith('.wxss') and cat in ('广告法极限词', '医疗敏感词', '政治敏感词', '联系方式引流', '商业化词', '诱导分享'):
                        continue
                    m = re.search(pat, line, re.I)
                    if m:
                        ctx = line[max(0, m.start() - CTX):m.end() + CTX].strip()
                        hits[level].append((cat, rel, ln, m.group(0), ctx, tip))
    return hits


all_hits = scan([APP], CODE_EXT, '源码')
if DATA_DIRS:
    data_hits = scan(DATA_DIRS, DATA_EXT, '内容数据')
    for lv in all_hits:
        all_hits[lv].extend(data_hits[lv])

print('=' * 70)
print('合规静态初筛报告  目标: ' + APP)
print('=' * 70)

for level in ('高危', '核对'):
    items = all_hits[level]
    by_cat = {}
    for it in items:
        by_cat.setdefault(it[0], []).append(it)
    print('\n【%s】共 %d 条' % (level, len(items)))
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        print('  %-10s %d 条  —— %s' % (cat, len(rows), rows[0][5]))
        for _, rel, ln, word, ctx, _ in rows[:5]:
            print('    %s:%s  命中「%s」  ...%s...' % (rel, ln, word, ctx))
        if len(rows) > 5:
            print('    ... 其余 %d 条略' % (len(rows) - 5))

n_high = len(all_hits['高危'])
print('\n' + ('存在高危命中，请逐项处理后再谈上架。' if n_high else '无高危命中；「核对」项请人工确认上下文。'))
sys.exit(1 if n_high else 0)
