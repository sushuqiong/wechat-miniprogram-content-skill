# -*- coding: utf-8 -*-
"""check_theme.py —— 微信小程序主题令牌自检（防止换肤半途而废）

用法:
    python check_theme.py <小程序源码目录>

判据:
  1. utils/theme.js 里声明的每个 id，在 app.wxss 里都有 .theme-<id> 块
  2. 每个主题块都定义了全部必需变量（缺一个就会出现「半套主题」）
  3. DEFAULT_ID 存在于主题表里
  4. 有 bgImg 的主题都定义了 --veil（否则文字压在背景图上读不清）
  5. bgImg 指向的文件真实存在且 < 100KB（主包余量有限）
  6. 全项目 wxss 里没有指向「已不存在主题 id」的失效选择器
  7. 全项目没有旧品牌色硬编码残留（在 LEGACY_PATTERNS 里配置你的旧色值）
"""
import io, os, re, sys

APP = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()

# 按你的项目配置：必需的主题变量
REQUIRED = [
    '--primary', '--primary-2', '--primary-soft', '--text', '--sub', '--muted',
    '--panel', '--panel-2', '--line', '--shadow', '--code-bg', '--deco',
    '--tag-beginner', '--tag-beginner-bg', '--tag-advanced', '--tag-advanced-bg',
    '--warn-bg', '--warn-line', '--warn-text', '--note-bg', '--note-line', '--note-text',
]

# 按你的项目配置：已废弃、不应再出现的硬编码色（正则，不区分大小写）
LEGACY_PATTERNS = r'#186090|#4F8A80|24, 96, 144'

# 单张背景图体积上限（KB）
MAX_BG_KB = 100

theme_js_path = os.path.join(APP, 'utils', 'theme.js')
wxss_path = os.path.join(APP, 'app.wxss')
for p in (theme_js_path, wxss_path):
    if not os.path.exists(p):
        print('FAIL  找不到文件: ' + p)
        sys.exit(1)

theme_js = io.open(theme_js_path, encoding='utf-8').read()
wxss = io.open(wxss_path, encoding='utf-8').read()

ids = re.findall(r"\n\s*id: '([a-z0-9-]+)',", theme_js)
m = re.search(r"DEFAULT_ID = '([a-z0-9-]+)'", theme_js)
default_id = m.group(1) if m else None

fails = []


def check(name, ok, detail=''):
    print(('PASS  ' if ok else 'FAIL  ') + name + ('  ' + detail if detail else ''))
    if not ok:
        fails.append(name)


def theme_block(tid):
    m2 = re.search(r'\.theme-' + re.escape(tid) + r'\s*\{(.*?)\n\}', wxss, re.S)
    return m2.group(1) if m2 else None


check('主题表非空', len(ids) > 0, '%d 套' % len(ids))
check('默认主题在主题表内', default_id in ids, str(default_id))

for tid in ids:
    body = theme_block(tid)
    if body is None:
        check('WXSS 存在 .theme-' + tid, False)
        continue
    missing = [v for v in REQUIRED if (v + ':') not in body]
    check('变量齐备 .theme-' + tid, not missing, ','.join(missing))

no_veil, missing_img, heavy = [], [], []
for tid, bg in re.findall(r"id: '([a-z0-9-]+)'[\s\S]{0,900}?bgImg: '([^']*)'", theme_js):
    if not bg:
        continue
    body = theme_block(tid) or ''
    if '--veil:' not in body:
        no_veil.append(tid)
    p = os.path.join(APP, bg.lstrip('/'))
    if not os.path.exists(p):
        missing_img.append(tid)
    elif os.path.getsize(p) > MAX_BG_KB * 1024:
        heavy.append('%s %.0fKB' % (tid, os.path.getsize(p) / 1024.0))
check('有背景图的主题都定义了 --veil', not no_veil, ','.join(no_veil))
check('背景图文件齐备', not missing_img, ','.join(missing_img))
check('单张背景图 < %dKB' % MAX_BG_KB, not heavy, ','.join(heavy))

legacy = []
for dirpath, _, files in os.walk(APP):
    for fn in files:
        if not fn.endswith(('.wxml', '.wxss', '.json')):
            continue
        p = os.path.join(dirpath, fn)
        src = io.open(p, encoding='utf-8').read()
        if re.search(LEGACY_PATTERNS, src, re.I):
            legacy.append(os.path.relpath(p, APP))
check('无旧品牌色残留', not legacy, ','.join(legacy[:5]))

# .theme-card / .theme-card-active 这类是组件类名，不是主题 id：
# 以 card / item 开头的复合名一律排除（主题 id 是单个词，如 violet / aurora）
IGNORE = {'card', 'item', 'scroll', 'list', 'preview', 'check', 'name', 'desc', 'badge'}


def is_component_class(name):
    return name in IGNORE or name.startswith('card-') or name.startswith('item-')


used = set(re.findall(r'\.theme-([a-z0-9-]+)', wxss))
used = {t for t in used if not is_component_class(t)}
for dirpath, _, files in os.walk(APP):
    for fn in files:
        if fn.endswith('.wxss'):
            src = io.open(os.path.join(dirpath, fn), encoding='utf-8').read()
            used |= {t for t in re.findall(r'\.theme-([a-z0-9-]+)', src) if not is_component_class(t)}
stale = sorted(t for t in used if t not in ids)
check('无失效主题选择器', not stale, ','.join(stale))

print('\n全部通过' if not fails else '\n有 %d 项未通过' % len(fails))
sys.exit(0 if not fails else 1)
