# -*- coding: utf-8 -*-
"""check_theme.py -- Theme-token gate for WeChat Mini Programs (prevents half-applied themes).

Usage:
    python check_theme.py <miniprogram source dir>

Criteria:
  1. Every theme id declared in utils/theme.js has a matching .theme-<id> block in app.wxss
  2. Every theme block defines all REQUIRED variables (a missing one falls back to the
     default color -> "half-applied theme")
  3. DEFAULT_ID exists in the theme table
  4. Themes with bgImg define --veil (otherwise text sits on the image unreadably)
  5. Files referenced by bgImg exist and are < MAX_BG_KB
  6. No stale .theme-<id> selectors project-wide (leftovers after a rename)
  7. No hardcoded legacy brand colors project-wide (configure LEGACY_PATTERNS)
"""
import io, os, re, sys

APP = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()

# Project-specific: variables every theme block must define
REQUIRED = [
    '--primary', '--primary-2', '--primary-soft', '--text', '--sub', '--muted',
    '--panel', '--panel-2', '--line', '--shadow', '--code-bg', '--deco',
    '--tag-beginner', '--tag-beginner-bg', '--tag-advanced', '--tag-advanced-bg',
    '--warn-bg', '--warn-line', '--warn-text', '--note-bg', '--note-line', '--note-text',
]

# Project-specific: regex of retired hardcoded colors that must not reappear (case-insensitive)
LEGACY_PATTERNS = r'#186090|#4F8A80|24, 96, 144'

# Per-image size budget (KB)
MAX_BG_KB = 100

theme_js_path = os.path.join(APP, 'utils', 'theme.js')
wxss_path = os.path.join(APP, 'app.wxss')
for p in (theme_js_path, wxss_path):
    if not os.path.exists(p):
        print('FAIL  file not found: ' + p)
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


check('theme table is not empty', len(ids) > 0, '%d themes' % len(ids))
check('DEFAULT_ID exists in theme table', default_id in ids, str(default_id))

for tid in ids:
    body = theme_block(tid)
    if body is None:
        check('WXSS block exists .theme-' + tid, False)
        continue
    missing = [v for v in REQUIRED if (v + ':') not in body]
    check('variables complete .theme-' + tid, not missing, ','.join(missing))

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
check('image themes all define --veil', not no_veil, ','.join(no_veil))
check('background images all exist', not missing_img, ','.join(missing_img))
check('each background image < %dKB' % MAX_BG_KB, not heavy, ','.join(heavy))

legacy = []
for dirpath, _, files in os.walk(APP):
    for fn in files:
        if not fn.endswith(('.wxml', '.wxss', '.json')):
            continue
        p = os.path.join(dirpath, fn)
        src = io.open(p, encoding='utf-8').read()
        if re.search(LEGACY_PATTERNS, src, re.I):
            legacy.append(os.path.relpath(p, APP))
check('no legacy brand colors', not legacy, ','.join(legacy[:5]))

# .theme-card / .theme-card-active are component classes, not theme ids:
# exclude compound names starting with card- / item- (theme ids are single words)
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
check('no stale theme selectors', not stale, ','.join(stale))

print('\nall checks passed' if not fails else '\n%d check(s) failed' % len(fails))
sys.exit(0 if not fails else 1)
