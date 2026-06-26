#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render infographic HTML (inline SVG) -> PNG via cairosvg, in sandbox (no Chrome).
cairosvg does NOT support textLength/lengthAdjust, so the generator's overflow
safety-net (textLength compression) is emulated here by shrinking font-size with
accurate per-glyph width metrics (CJK ~1.0*size, ASCII ~0.58*size).
Also: foreignObject(div) -> wrapped <text>/<tspan>; #RRGGBBAA -> rgba(); stray & escaped.
"""
import re, sys, html
from pathlib import Path
import cairosvg

SIZE = 1080

def _cjk(ch):
    o = ord(ch)
    return (0xAC00 <= o <= 0xD7A3) or (0x3000 <= o <= 0x30FF) or (0x4E00 <= o <= 0x9FFF) \
        or (0xFF00 <= o <= 0xFFEF) or ch in '·—…‚„“”’‘'

def char_w(ch, size):
    if ch == ' ':
        return size * 0.30
    if _cjk(ch):
        return size * 1.02
    if ch in '|ㅣ!.,:;\'"`()[]':
        return size * 0.34
    if ch.isdigit():
        return size * 0.58
    return size * 0.60  # latin / %/+/- etc.

def text_w(s, size):
    return sum(char_w(c, size) for c in s)

def fit_size(text, max_w, cur_size, min_size=22):
    s = cur_size
    while s > min_size and text_w(text, s) > max_w:
        s -= 1
    return s

def hex8_to_rgba(m):
    h = m.group(0)
    r = int(h[1:3],16); g = int(h[3:5],16); b = int(h[5:7],16); a = int(h[7:9],16)/255
    return f"rgba({r},{g},{b},{a:.3f})"

def style_val(style, key, default=None):
    m = re.search(rf"{key}\s*:\s*([^;]+)", style)
    return m.group(1).strip() if m else default

def wrap_by_width(text, max_w, size):
    words = text.split(' ')
    lines, cur = [], ''
    for w in words:
        cand = (cur + ' ' + w).strip()
        if text_w(cand, size) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            while text_w(w, size) > max_w:
                # hard break long token
                i = len(w)
                while i > 1 and text_w(w[:i], size) > max_w:
                    i -= 1
                lines.append(w[:i]); w = w[i:]
            cur = w
    if cur:
        lines.append(cur)
    return lines

def convert_foreignobject(svg):
    pat = re.compile(
        r'<foreignObject\s+x="([0-9.]+)"\s+y="([0-9.]+)"\s+width="([0-9.]+)"\s+height="([0-9.]+)"\s*>\s*'
        r'<div[^>]*style="([^"]*)"[^>]*>(.*?)</div>\s*</foreignObject>',
        re.DOTALL)

    def repl(m):
        x = float(m.group(1)); y = float(m.group(2)); w = float(m.group(3)); h = float(m.group(4))
        style = m.group(5); inner = html.unescape(re.sub(r'<[^>]+>', '', m.group(6))).strip()
        color = style_val(style, 'color', '#FFFFFF')
        fs = float(re.sub(r'[^0-9.]', '', style_val(style, 'font-size', '25') or '25'))
        fw = style_val(style, 'font-weight', '700')
        is_flex = 'flex' in style
        # shrink font so each wrapped line fits, and total fits height
        lines = wrap_by_width(inner, w, fs)
        line_h = fs * 1.34
        # if block too tall for its box (non-flex hero), shrink font
        guard = 0
        while not is_flex and line_h * len(lines) > h + fs*1.3 and fs > 20 and guard < 20:
            fs -= 1; lines = wrap_by_width(inner, w, fs); line_h = fs*1.34; guard += 1
        if is_flex:
            block_h = line_h * len(lines)
            start = y + (h - block_h)/2 + fs*0.92
        else:
            start = y + fs
        tspans = ''.join(
            f'<tspan x="{x}" y="{start + i*line_h:.1f}">{html.escape(ln)}</tspan>'
            for i, ln in enumerate(lines))
        return (f'<text fill="{color}" font-size="{fs:.0f}" font-weight="{fw}" '
                f'font-family="NanumGothic,sans-serif">{tspans}</text>')

    return pat.sub(repl, svg)

# Clamp every <text> so it fits the canvas, using accurate CJK metrics.
# (cairosvg ignores textLength, and the generator under-estimates CJK width,
#  so long titles overflow. We shrink font-size to fit and drop textLength.)
_TEXT_RE = re.compile(r'<text\b([^>]*?)>(.*?)</text>', re.DOTALL)

def _attr(attrs, name, default=None):
    m = re.search(rf'{name}="([^"]*)"', attrs)
    return m.group(1) if m else default

def emulate_textlength(svg):
    def repl(m):
        attrs = m.group(1); content = m.group(2)
        # always strip textLength/lengthAdjust (cairosvg ignores them)
        attrs = re.sub(r'\s*textLength="[0-9.]+"', '', attrs)
        attrs = re.sub(r'\s*lengthAdjust="[^"]*"', '', attrs)
        if '<tspan' in content:
            return f'<text{attrs}>{content}</text>'  # already wrapped/fitted
        plain = re.sub(r'<[^>]+>', '', content)
        if not plain.strip():
            return f'<text{attrs}>{content}</text>'
        fs_m = re.search(r'font-size="([0-9.]+)"', attrs)
        if not fs_m:
            return f'<text{attrs}>{content}</text>'
        fs = float(fs_m.group(1))
        x = float(_attr(attrs, 'x', '0') or 0)
        anchor = _attr(attrs, 'text-anchor', 'start')
        margin = 20
        if anchor == 'end':
            avail = x - margin
        elif anchor == 'middle':
            avail = 2 * min(x, SIZE - x) - margin
        else:
            avail = SIZE - x - margin
        if avail <= 0:
            return f'<text{attrs}>{content}</text>'
        new_fs = fit_size(plain, avail, int(fs), min_size=20)
        if new_fs < int(fs):
            attrs = re.sub(r'font-size="[0-9.]+"', f'font-size="{new_fs}"', attrs)
        return f'<text{attrs}>{content}</text>'
    return _TEXT_RE.sub(repl, svg)

def render(html_path, png_path):
    raw = html_path.read_text(encoding='utf-8')
    m = re.search(r'<svg.*?</svg>', raw, re.DOTALL)
    if not m:
        print(f"  ! no svg in {html_path.name}"); return False
    svg = m.group(0)
    if 'foreignObject' in svg:
        svg = convert_foreignobject(svg)
    svg = emulate_textlength(svg)
    svg = re.sub(r'#[0-9A-Fa-f]{8}\b', hex8_to_rgba, svg)
    svg = re.sub(r'&(?!#?\w+;)', '&amp;', svg)
    cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(png_path),
                     output_width=SIZE, output_height=SIZE)
    kb = png_path.stat().st_size/1024
    print(f"  ✓ {png_path.name}  {kb:.0f}KB")
    return kb > 18

def main():
    html_dir = Path(sys.argv[1]); out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = True
    for hp in sorted(html_dir.glob('*.html')):
        if not render(hp, out_dir / (hp.stem + '.png')):
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
