# -*- coding: utf-8 -*-
"""check_interaction.py -- Interaction-robustness gate for WeChat Mini Programs.

Usage:
    python check_interaction.py <miniprogram source dir>

Scans for the interaction failures documented in references/interaction-robustness.md.
FAIL items are deterministic bad patterns (exit 1). REVIEW items need human context
and never fail the gate. This is a SCREEN, not a verdict.

FAIL criteria:
  1. setClipboardData is used but the project has no onShowCopyFallback (no selectable
     text escape hatch for rich-text code blocks).
  2. A rich-text code block exists in a detail page but NO page in the project
     offers an onCopyCode entry. A read-only detail page is legitimate when the
     daily/home page is the single authoritative copy entry. (A detail code
     block rendered line-by-line with <text> is also a legitimate read-only
     layout; see references/interaction-robustness.md section 9.)
  3. wx:for appears without wx:key somewhere in WXML.
  4. iOS-unsafe date literal new Date('YYYY-MM-DD ...') (hyphenated string) is present.

REVIEW criteria (printed, not failing):
  R1. scroll-y scroll-view whose class has only max-height and no fixed height.
  R2. touch/swipe handler present but no debounce marker.
  R3. catchtouch handler sets a timestamp guard flag (possible 900ms blackout).
"""
import io, os, re, sys

APP = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()

fails = []
reviews = []


def fail(name, detail=''):
    print('FAIL  ' + name + ('  ' + detail if detail else ''))
    fails.append(name)


def review(name, detail=''):
    print('REVIEW ' + name + ('  ' + detail if detail else ''))
    reviews.append(name)


def walk(exts):
    for dp, dirs, fs in os.walk(APP):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
        for fn in fs:
            if fn.endswith(exts):
                yield os.path.join(dp, fn)


def read(p):
    try:
        return io.open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        return ''


js_files = list(walk(('.js',)))
wxml_files = list(walk(('.wxml',)))
wxss_files = list(walk(('.wxss',)))
all_js = '\n'.join(read(p) for p in js_files)
all_wxml = '\n'.join(read(p) for p in wxml_files)

print('=' * 70)
print('Interaction robustness gate  target: ' + APP)
print('  js=%d  wxml=%d  wxss=%d' % (len(js_files), len(wxml_files), len(wxss_files)))
print('=' * 70)

# F1: clipboard without a selectable-text fallback
uses_clipboard = 'setClipboardData' in all_js
has_fallback = 'onShowCopyFallback' in all_js
if uses_clipboard and not has_fallback:
    fail('F1 clipboard has no selectable-text fallback',
         'setClipboardData used but no onShowCopyFallback found')
else:
    print('PASS  F1 clipboard fallback' + ('  (no clipboard usage)' if not uses_clipboard else ''))

# F2: rich-text code block in a detail page with no copy handler at all.
# Two layouts are legitimate: (a) the detail page copies its own code; (b) the
# detail page is read-only and the ONE authoritative copy entry lives on the
# daily/home page (rich-text cannot be long-press-selected, and privacy-authorize
# failures are harder to recover from on a pushed page). Only fail when the whole
# project has no onCopyCode entry at all.
project_has_copy = any('onCopyCode' in read(p) for p in js_files)
rich_detail_bad = []
for p in js_files:
    base = os.path.splitext(p)[0]
    wxml = base + '.wxml'
    js_src = read(p)
    if not os.path.exists(wxml):
        continue
    w = read(wxml)
    is_detail = 'detail' in os.path.basename(base).lower()
    if is_detail and 'rich-text' in w:
        has_copy = ('onCopy' in js_src or 'copyCode' in js_src or
                    'setClipboardData' in js_src or 'onShowCopyFallback' in js_src or
                    'onCopyCode' in js_src)
        if not has_copy and not project_has_copy:
            rich_detail_bad.append(os.path.relpath(p, APP))
if rich_detail_bad:
    fail('F2 rich-text detail has no copy handler', ','.join(rich_detail_bad))
else:
    print('PASS  F2 rich-text detail pages provide copy')

# F3: wx:for without wx:key on the same tag
bad_key = []
for p in wxml_files:
    for m in re.finditer(r'<[\w-]+\b[^>]*\bwx:for\b[^>]*>', read(p)):
        tag = m.group(0)
        if 'wx:key' not in tag:
            # allow wx:for on <block> only if a key is present; strict check
            bad_key.append('%s:%d' % (os.path.relpath(p, APP),
                                      read(p)[:m.start()].count('\n') + 1))
if bad_key:
    fail('F3 wx:for without wx:key', ','.join(bad_key[:6]))
else:
    print('PASS  F3 every wx:for has wx:key')

# F4: iOS-unsafe hyphenated date literal (skip comment lines -- code comments often
# show the bad pattern as a "don't do this" example, e.g. new Date('2026-12-01'))
bad_date = []
for p in js_files:
    src = read(p)
    for ln, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('*'):
            continue
        code = line.split('//')[0]
        if re.search(r"new\s+Date\(\s*['\"]\d{4}-\d{2}-\d{2}", code):
            bad_date.append('%s:%d' % (os.path.relpath(p, APP), ln))
if bad_date:
    fail('F4 iOS-unsafe hyphenated date literal', ','.join(bad_date[:6]))
else:
    print('PASS  F4 no iOS-unsafe date literal')

# R1: scroll-y container with max-height but no fixed height
for p in wxss_files:
    src = read(p)
    for m in re.finditer(r'([\w-]+)\s*\{([^}]*)\}', src, re.S):
        sel, body = m.group(1), m.group(2)
        if 'max-height' in body and not re.search(r'(?<!max-)\bheight\s*:', body):
            if any(k in sel for k in ('code', 'scroll', 'rich', 'block')):
                review('R1 scroll container lacks fixed height',
                       '%s %s' % (os.path.relpath(p, APP), sel))

# R2: touch handler without debounce
touch_js = [p for p in js_files if re.search(r'onTouchEnd|onSwipeEnd|stepBy|onStep', read(p))]
for p in touch_js:
    src = read(p)
    if not re.search(r'_stepAt|_stepLocked|debounce|260|Date\.now\(\)', src):
        review('R2 swipe handler without debounce marker', os.path.relpath(p, APP))

# R3: the specific old anti-pattern -- a code-area timestamp guard with a 900ms-style
# blackout window. Modern fixes use a boolean _noSwipe cleared in onTouchEnd; a plain
# Date.now() debounce (_stepAt) is healthy and must NOT be flagged.
for p in js_files:
    src = read(p)
    if re.search(r'_codeAt', src) and re.search(r'\b900\b', src) and 'onTouchEnd' in src:
        review('R3 possible timestamp blackout on swipe', os.path.relpath(p, APP))

print('\nFAIL: %d   REVIEW: %d' % (len(fails), len(reviews)))
if not fails:
    print('all deterministic checks passed; confirm REVIEW items manually')
sys.exit(1 if fails else 0)
