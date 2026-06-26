#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render infographic HTML (inline SVG) -> PNG via cairosvg, in sandbox (no Chrome).
- foreignObject(div) blocks -> wrapped <text>/<tspan>
- 8-digit hex (#RRGGBBAA) -> rgba()
"""
import re, sys, html
from pathlib import Path
import cairosvg

SIZE = 1080

def hex8_to_rgba(m):
    h = m.group(0)
    r = int(h[1:3], 16); g = int(h[3:5], 16); b = int(h[5:7], 16); a = int(h[7:9], 16) / 255
    return f"rgba({r},{g},{b},{a:.3f})"

def style_val(style, key, default=None):
    m = re.search(rf"{key}\s*:\s*([^;]+)", style)
    return m.group(1).strip() if m else default

def wrap_text(text, max_chars):
    # greedy wrap on spaces, but Korean has few spaces -> also hard-break long tokens
    words = text.split(' ')
    lines, cur = [], ''
    for w in words:
        cand = (cur + ' ' + w).strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            # hard break very long token
            while len(w) > max_chars:
                lines.append(w[:max_chars]); w = w[max_chars:]
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
        is_flex = 'flex' in style  # single-line vertically-centered point row
        max_chars = max(6, int(w / (fs * 0.92)))
        lines = wrap_text(inner, max_chars)
        line_h = fs * 1.32
        if is_flex:
            # vertically center within h
            block_h = line_h * len(lines)
            start_baseline = y + (h - block_h) / 2 + fs
        else:
            start_baseline = y + fs
        tspans = []
        for i, ln in enumerate(lines):
            ty = start_baseline + i * line_h
            tspans.append(f'<tspan x="{x}" y="{ty:.1f}">{html.escape(ln)}</tspan>')
        return (f'<text fill="{color}" font-size="{fs:.0f}" font-weight="{fw}" '
                f'font-family="NanumGothic,sans-serif">' + ''.join(tspans) + '</text>')

    return pat.sub(repl, svg)

def render(html_path: Path, png_path: Path):
    raw = html_path.read_text(encoding='utf-8')
    m = re.search(r'<svg.*?</svg>', raw, re.DOTALL)
    if not m:
        print(f"  ! no svg in {html_path.name}"); return False
    svg = m.group(0)
    if 'foreignObject' in svg:
        svg = convert_foreignobject(svg)
    svg = re.sub(r'#[0-9A-Fa-f]{8}\b', hex8_to_rgba, svg)
    # escape stray ampersands not part of an entity (e.g. "수급 & 종목")
    svg = re.sub(r'&(?!#?\w+;)', '&amp;', svg)
    cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(png_path),
                     output_width=SIZE, output_height=SIZE)
    kb = png_path.stat().st_size / 1024
    print(f"  ✓ {png_path.name}  {kb:.0f}KB")
    return kb > 18

def main():
    html_dir = Path(sys.argv[1]); out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = True
    for hp in sorted(html_dir.glob('*.html')):
        png = out_dir / (hp.stem + '.png')
        if not render(hp, png):
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
