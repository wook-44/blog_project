"""
stock-youtube-blog-writer / generate_infographics.py  (v3 — 정사각형 모바일 최적)
================================================================================
- 1080×1080 정사각형 (Instagram/네이버 모바일 친화)
- 4/27 스타일 계승: 그라데이션 다크 네이비, hero 큰 숫자, 빼곡한 카드 그리드
- 톤북 v1: 외곽 padding 최소화, stat-card 4열, 인용구 박스
- 3종(market/psychology/summary) PNG 생성, insight는 본문 텍스트로만

사용:
  python generate_infographics.py --date 2026-05-13 \\
    --data '{"market":{...},"psychology":{...},"summary":{...}}' \\
    --output ./images/2026-05-13/
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

# ── 디자인 토큰 (4/27 스타일) ─────────────────────────────
SIZE = 1080  # 정사각형 한 변

COLORS = {
    "bg_start": "#0F172A",
    "bg_end":   "#1E293B",
    "card":     "#1E293B",
    "card_alt": "#1E3A5F",
    "border":   "#334155",
    "text_pri": "#FFFFFF",
    "text_sec": "#94A3B8",
    "text_dim": "#64748B",
}

ACCENTS = {
    "market":     {"icon": "📊", "label": "MARKET STATUS",       "kor": "시장 분석", "from": "#3B82F6", "to": "#06B6D4", "hero_from": "#F59E0B", "hero_to": "#EF4444"},
    "psychology": {"icon": "🧠", "label": "INVESTMENT PSYCHOLOGY","kor": "투자 심리", "from": "#A78BFA", "to": "#EC4899", "hero_from": "#FBBF24", "hero_to": "#F472B6"},
    "summary":    {"icon": "✅", "label": "KEY POINTS TODAY",     "kor": "핵심 포인트","from": "#10B981", "to": "#06B6D4", "hero_from": "#10B981", "hero_to": "#3B82F6"},
    "outlook":    {"icon": "🔭", "label": "MARKET OUTLOOK",       "kor": "전망/관전 포인트","from": "#0EA5E9", "to": "#22D3EE", "hero_from": "#22D3EE", "hero_to": "#A78BFA"},
    "checklist":  {"icon": "☑️", "label": "ACTION CHECKLIST",     "kor": "체크리스트","from": "#F97316", "to": "#EF4444", "hero_from": "#F97316", "hero_to": "#FBBF24"},
    "sector":     {"icon": "🏭", "label": "SECTOR ROTATION",      "kor": "섹터/순환매","from": "#14B8A6", "to": "#0EA5E9", "hero_from": "#14B8A6", "hero_to": "#3B82F6"},
    "risk":       {"icon": "⚠️", "label": "RISK FACTORS",         "kor": "리스크",    "from": "#EF4444", "to": "#F97316", "hero_from": "#EF4444", "hero_to": "#FBBF24"},
}

# 알 수 없는 키 fallback (회색 톤)
DEFAULT_ACCENT = {"icon": "📌", "label": "SECTION", "kor": "섹션", "from": "#94A3B8", "to": "#64748B", "hero_from": "#94A3B8", "hero_to": "#64748B"}


def html_doc(svg_inner: str) -> str:
    """공통 HTML 래퍼."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  /* 로컬 NanumGothic Bold/ExtraBold만 사용 — Regular(400)는 제거해서 항상 굵은 글자 보장 */
  @font-face {{ font-family: 'NanumGothic'; src: local('NanumGothic Bold'), local('NanumGothicBold'), local('나눔고딕 Bold'); font-weight: 700; }}
  @font-face {{ font-family: 'NanumGothic'; src: local('NanumGothicExtraBold'), local('NanumGothic ExtraBold'), local('나눔고딕 ExtraBold'); font-weight: 800 900; }}
  /* 400 weight 요청 시에도 700으로 폴백 */
  @font-face {{ font-family: 'NanumGothic'; src: local('NanumGothic Bold'), local('NanumGothicBold'); font-weight: 1 400; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-font-smoothing: antialiased; }}
  html, body {{ width: {SIZE}px; height: {SIZE}px; overflow: hidden; background: transparent; }}
  svg {{ width: {SIZE}px; height: {SIZE}px; display: block; }}
</style></head>
<body>{svg_inner}</body></html>"""


def _common_defs(accent_from: str, accent_to: str, hero_from: str, hero_to: str) -> str:
    return f"""<defs>
  <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" style="stop-color:{COLORS['bg_start']}"/>
    <stop offset="100%" style="stop-color:{COLORS['bg_end']}"/>
  </linearGradient>
  <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" style="stop-color:{accent_from}"/>
    <stop offset="100%" style="stop-color:{accent_to}"/>
  </linearGradient>
  <linearGradient id="hero" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" style="stop-color:{hero_from}"/>
    <stop offset="100%" style="stop-color:{hero_to}"/>
  </linearGradient>
  <filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>"""


def _header(date: str, label: str, title: str, accent_from: str, accent_to: str) -> str:
    """공통 헤더 (섹션 라벨 + 큰 타이틀 + 디바이더). 날짜 배지는 표시 안 함."""
    return f"""
  <!-- 상단 accent bar -->
  <rect x="0" y="0" width="{SIZE}" height="8" fill="url(#accent)"/>

  <!-- 섹션 라벨 -->
  <text x="48" y="80" fill="{COLORS['text_dim']}" font-size="20" font-weight="700" letter-spacing="6">{label}</text>

  <!-- 메인 타이틀 -->
  <text x="48" y="148" fill="{COLORS['text_pri']}" font-size="48" font-weight="800">{title}</text>

  <!-- 디바이더 -->
  <rect x="48" y="160" width="100" height="5" fill="url(#accent)" rx="2"/>
"""


def _footer(footer_quote: str, footer_author: str) -> str:
    """공통 푸터 — 인용구 박스 + 브랜딩."""
    quote_y = SIZE - 130
    return f"""
  <!-- 인용구 박스 -->
  <rect x="48" y="{quote_y}" width="{SIZE-96}" height="78" fill="{COLORS['card_alt']}" rx="14" opacity="0.55"/>
  <text x="68" y="{quote_y+30}" fill="{COLORS['text_sec']}" font-size="18">"</text>
  <text x="84" y="{quote_y+32}" fill="{COLORS['text_pri']}" font-size="21" font-weight="700">{footer_quote}</text>
  <text x="68" y="{quote_y+62}" fill="{COLORS['text_dim']}" font-size="16">— {footer_author}</text>

  <!-- 우측 하단 브랜딩 -->
  <text x="{SIZE-48}" y="{SIZE-24}" text-anchor="end" fill="{COLORS['border']}" font-size="14" letter-spacing="1">12시에 만나요 · 주식 분석 블로그</text>
"""


# ── MARKET 빌더 ────────────────────────────────────────────
def build_market_html(data: dict, date: str) -> str:
    a = ACCENTS["market"]
    title = data.get("title", "코스피가 보낸 신호")
    stats = data.get("stats", [])[:4]
    while len(stats) < 4:
        stats.append({"value": "—", "label": "데이터", "delta": ""})

    hero = stats[0]  # 첫 번째 스탯이 hero
    sub = stats[1:4]  # 나머지 3개가 카드
    chips = data.get("chips", [])[:5]
    points = data.get("points", [])[:3]
    footer_q = data.get("footer_quote", "")
    footer_a = data.get("footer_author", "12시에 만나요")

    # 우측 화살표 영역에 들어갈 보조 정보
    hero_delta = hero.get("delta", "")
    hero_label = hero.get("label", "")
    hero_value = hero.get("value", "—")

    # 카드 3개 (가로 배치, 카드 사이 간격 16px)
    card_w = (SIZE - 96 - 32) / 3  # 외곽 padding 48*2 = 96, 카드 사이 16*2 = 32
    cards_y = 370
    cards_svg = ""
    for i, s in enumerate(sub):
        x = 48 + i * (card_w + 16)
        cards_svg += f"""
  <rect x="{x}" y="{cards_y}" width="{card_w}" height="165" fill="{COLORS['card']}" rx="14" stroke="{COLORS['border']}" stroke-width="1"/>
  <text x="{x+card_w/2}" y="{cards_y+36}" text-anchor="middle" fill="{COLORS['text_dim']}" font-size="17" font-weight="700" letter-spacing="2">{s.get('label','')}</text>
  <text x="{x+card_w/2}" y="{cards_y+100}" text-anchor="middle" fill="{a['from']}" font-size="52" font-weight="900">{s.get('value','—')}</text>
  <text x="{x+card_w/2}" y="{cards_y+136}" text-anchor="middle" fill="{COLORS['text_sec']}" font-size="16">{s.get('delta','')}</text>"""

    # 칩 (5개) — 카드 아래
    chip_y = cards_y + 150
    chip_x = 48
    chips_svg = ""
    if chips:
        for c in chips:
            chip_w = len(c) * 14 + 36
            chips_svg += f"""
  <rect x="{chip_x}" y="{chip_y}" width="{chip_w}" height="40" fill="{a['from']}1A" rx="20" stroke="{a['from']}44" stroke-width="1"/>
  <text x="{chip_x+chip_w/2}" y="{chip_y+26}" text-anchor="middle" fill="{a['from']}" font-size="16" font-weight="700">{c}</text>"""
            chip_x += chip_w + 8

    # 주요 포인트 3개 — 칩 아래
    points_y = chip_y + 60
    points_svg = ""
    if points:
        points_svg = f"""
  <text x="48" y="{points_y}" fill="{COLORS['text_dim']}" font-size="17" font-weight="700" letter-spacing="2">주요 포인트</text>"""
        for i, p in enumerate(points):
            y = points_y + 40 + i * 44
            points_svg += f"""
  <circle cx="60" cy="{y-6}" r="14" fill="{a['from']}"/>
  <text x="60" y="{y-1}" text-anchor="middle" fill="{COLORS['bg_start']}" font-size="16" font-weight="800">{i+1}</text>
  <text x="88" y="{y}" fill="{COLORS['text_pri']}" font-size="21" font-weight="700">{p}</text>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}

  <!-- HERO 영역 -->
  <text x="48" y="280" fill="url(#hero)" font-size="120" font-weight="900" filter="url(#glow)">{hero_value}</text>
  <text x="48" y="328" fill="{COLORS['text_sec']}" font-size="24" font-weight="700">{hero_label}</text>

  <!-- 우측 변동 표시 -->
  <polygon points="{SIZE-180},210 {SIZE-150},260 {SIZE-120},210" fill="{a['from']}" opacity="0.95"/>
  <text x="{SIZE-150}" y="300" text-anchor="middle" fill="{a['from']}" font-size="22" font-weight="800">{hero_delta}</text>

  {cards_svg}
  {chips_svg}
  {points_svg}
{_footer(footer_q or '오늘의 시장은 숫자가 말한다', footer_a)}
</svg>"""
    return html_doc(svg)


# ── PSYCHOLOGY 빌더 ────────────────────────────────────────
def build_psychology_html(data: dict, date: str) -> str:
    a = ACCENTS["psychology"]
    title = data.get("title", "시장이 오를수록 심리가 중요하다")
    hero_msg = data.get("hero_msg", data.get("key_stat", ""))
    traps = data.get("traps", [])[:3]
    correction = data.get("correction", data.get("points", ["수급 데이터로 방향 재확인"])[-1])
    footer_q = data.get("footer_quote", "")
    footer_a = data.get("footer_author", "12시에 만나요")

    if not traps and data.get("points"):
        pts = data["points"]
        traps = [{"name": "함정", "desc": p} for p in pts[:3]]

    # 함정 3개 카드 (가로 배치)
    card_w = (SIZE - 96 - 32) / 3
    cards_y = 320
    cards_svg = ""
    for i, t in enumerate(traps):
        x = 48 + i * (card_w + 16)
        cards_svg += f"""
  <rect x="{x}" y="{cards_y}" width="{card_w}" height="260" fill="{COLORS['card']}" rx="16" stroke="{a['from']}44" stroke-width="2"/>
  <circle cx="{x+card_w/2}" cy="{cards_y+58}" r="40" fill="{a['from']}22"/>
  <text x="{x+card_w/2}" y="{cards_y+72}" text-anchor="middle" font-size="44">{['😱','🤯','😩'][i] if i<3 else '⚠️'}</text>
  <text x="{x+card_w/2}" y="{cards_y+138}" text-anchor="middle" fill="{a['from']}" font-size="24" font-weight="800">{t.get('name','함정')}</text>
  <foreignObject x="{x+16}" y="{cards_y+158}" width="{card_w-32}" height="80">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:{COLORS['text_sec']};font-size:17px;line-height:1.45;text-align:center;font-family:NanumGothic,sans-serif">{t.get('desc','')}</div>
  </foreignObject>"""

    # 교정 카드 (큰 카드, 함정 아래)
    cor_y = cards_y + 280
    correction_svg = f"""
  <rect x="48" y="{cor_y}" width="{SIZE-96}" height="140" fill="{a['to']}1A" rx="16" stroke="{a['to']}66" stroke-width="2"/>
  <text x="80" y="{cor_y+42}" fill="{a['to']}" font-size="17" font-weight="800" letter-spacing="3">✓ 교정 방법</text>
  <foreignObject x="80" y="{cor_y+55}" width="{SIZE-160}" height="78">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#FFFFFF;font-size:26px;font-weight:700;line-height:1.4;font-family:NanumGothic,sans-serif">{correction}</div>
  </foreignObject>"""

    # Hero 메시지 (헤더 아래, 함정 위)
    hero_svg = ""
    if hero_msg:
        hero_svg = f"""
  <text x="48" y="250" fill="url(#hero)" font-size="52" font-weight="900" filter="url(#glow)">{hero_msg}</text>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}
  {hero_svg}
  {cards_svg}
  {correction_svg}
{_footer(footer_q or '오르는 시장도, 빠지는 시장도 — 결국 심리가 결정한다', footer_a)}
</svg>"""
    return html_doc(svg)


# ── SUMMARY 빌더 ───────────────────────────────────────────
def build_summary_html(data: dict, date: str) -> str:
    a = ACCENTS["summary"]
    title = data.get("title", "오늘의 핵심 5포인트")
    points = data.get("points", [])[:5]
    while len(points) < 5:
        points.append("—")
    hero_takeaway = data.get("hero_takeaway", points[0] if points else "")
    footer_q = data.get("footer_quote", "")
    footer_a = data.get("footer_author", "12시에 만나요")

    # Hero takeaway 박스
    hero_svg = f"""
  <rect x="48" y="200" width="{SIZE-96}" height="140" fill="{a['from']}1A" rx="18" stroke="{a['from']}66" stroke-width="2"/>
  <text x="80" y="244" fill="{a['from']}" font-size="17" font-weight="800" letter-spacing="3">⭐ TODAY'S TAKEAWAY</text>
  <foreignObject x="80" y="258" width="{SIZE-160}" height="78">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#FFFFFF;font-size:30px;font-weight:800;line-height:1.35;font-family:NanumGothic,sans-serif">{hero_takeaway}</div>
  </foreignObject>"""

    # 5 포인트 (큰 번호 + 텍스트, 컴팩트 리스트)
    pts_y = 380
    pts_svg = ""
    for i, p in enumerate(points):
        y = pts_y + i * 92
        pts_svg += f"""
  <rect x="48" y="{y}" width="{SIZE-96}" height="78" fill="{COLORS['card']}" rx="12" stroke="{COLORS['border']}" stroke-width="1"/>
  <circle cx="92" cy="{y+39}" r="26" fill="url(#accent)"/>
  <text x="92" y="{y+48}" text-anchor="middle" fill="{COLORS['bg_start']}" font-size="26" font-weight="900">{i+1}</text>
  <foreignObject x="138" y="{y+16}" width="{SIZE-200}" height="50">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#FFFFFF;font-size:21px;font-weight:700;line-height:1.4;font-family:NanumGothic,sans-serif;display:flex;align-items:center;height:46px">{p}</div>
  </foreignObject>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}
  {hero_svg}
  {pts_svg}
{_footer(footer_q or '오늘 배운 것을 내일 매매에 반영한다', footer_a)}
</svg>"""
    return html_doc(svg)


BUILDERS = {
    "market":     build_market_html,
    "psychology": build_psychology_html,
    "summary":    build_summary_html,
    # 아래 키는 generic 빌더로 처리됨 — 별도 항목 추가시 ACCENTS만 채우면 OK
}


# ── GENERIC 빌더 ────────────────────────────────────────────
def build_generic_html(data: dict, date: str, section_key: str = "section") -> str:
    """알 수 없는 섹션 키 또는 사용자 커스텀 섹션을 위한 범용 빌더.
    data 스키마:
      title, hero_value/hero_label (선택), stats[], chips[], points[],
      footer_quote, footer_author
    """
    a = ACCENTS.get(section_key, DEFAULT_ACCENT)
    title = data.get("title", a["kor"])
    hero_value = data.get("hero_value", "")
    hero_label = data.get("hero_label", "")
    hero_delta = data.get("hero_delta", "")
    stats = data.get("stats", [])[:4]
    chips = data.get("chips", [])[:6]
    points = data.get("points", [])[:5]
    footer_q = data.get("footer_quote", "")
    footer_a = data.get("footer_author", "12시에 만나요")

    # Hero 영역 (있으면)
    hero_svg = ""
    if hero_value:
        hero_svg = f"""
  <text x="48" y="320" fill="url(#hero)" font-size="100" font-weight="900" filter="url(#glow)">{hero_value}</text>
  <text x="48" y="358" fill="{COLORS['text_sec']}" font-size="18" font-weight="700">{hero_label}</text>"""
        if hero_delta:
            hero_svg += f"""
  <text x="{SIZE-150}" y="335" text-anchor="middle" fill="{a['from']}" font-size="18" font-weight="800">{hero_delta}</text>"""

    # 카드 (있을 때만, 1~4개)
    cards_y = 400 if hero_value else 260
    cards_svg = ""
    n = len(stats)
    if n > 0:
        gap = 16
        total_gap = gap * (n - 1)
        card_w = (SIZE - 96 - total_gap) / n
        for i, s in enumerate(stats):
            x = 48 + i * (card_w + gap)
            cards_svg += f"""
  <rect x="{x}" y="{cards_y}" width="{card_w}" height="120" fill="{COLORS['card']}" rx="14" stroke="{COLORS['border']}" stroke-width="1"/>
  <text x="{x+card_w/2}" y="{cards_y+30}" text-anchor="middle" fill="{COLORS['text_dim']}" font-size="13" font-weight="700" letter-spacing="2">{s.get('label','')}</text>
  <text x="{x+card_w/2}" y="{cards_y+76}" text-anchor="middle" fill="{a['from']}" font-size="38" font-weight="900">{s.get('value','—')}</text>
  <text x="{x+card_w/2}" y="{cards_y+103}" text-anchor="middle" fill="{COLORS['text_sec']}" font-size="13">{s.get('delta','')}</text>"""

    # 칩
    chip_y = cards_y + (150 if stats else 0)
    chip_x = 48
    chips_svg = ""
    if chips:
        for c in chips:
            chip_w = len(c) * 14 + 36
            chips_svg += f"""
  <rect x="{chip_x}" y="{chip_y}" width="{chip_w}" height="40" fill="{a['from']}1A" rx="20" stroke="{a['from']}44" stroke-width="1"/>
  <text x="{chip_x+chip_w/2}" y="{chip_y+26}" text-anchor="middle" fill="{a['from']}" font-size="16" font-weight="700">{c}</text>"""
            chip_x += chip_w + 8

    # 포인트
    points_y = chip_y + (60 if chips else 30)
    points_svg = ""
    if points:
        points_svg = f"""
  <text x="48" y="{points_y}" fill="{COLORS['text_dim']}" font-size="13" font-weight="700" letter-spacing="2">주요 포인트</text>"""
        for i, p in enumerate(points):
            y = points_y + 32 + i * 36
            points_svg += f"""
  <circle cx="58" cy="{y-5}" r="11" fill="{a['from']}"/>
  <text x="58" y="{y-1}" text-anchor="middle" fill="{COLORS['bg_start']}" font-size="13" font-weight="800">{i+1}</text>
  <text x="80" y="{y}" fill="{COLORS['text_pri']}" font-size="16" font-weight="700">{p}</text>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}
  {hero_svg}
  {cards_svg}
  {chips_svg}
  {points_svg}
{_footer(footer_q or a['kor'] + ' 한 줄', footer_a)}
</svg>"""
    return html_doc(svg)


# ── HTML → PNG 변환 ──────────────────────────────────────────
def html_to_png_via_chrome(html_path: Path, png_path: Path) -> bool:
    chrome_candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome", "chromium-browser", "chromium",
    ]
    for chrome in chrome_candidates:
        try:
            subprocess.run([
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-sandbox",
                f"--window-size={SIZE},{SIZE}",
                f"--screenshot={png_path}",
                f"file://{html_path.resolve()}",
            ], capture_output=True, timeout=20)
            if png_path.exists() and png_path.stat().st_size > 5000:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def html_to_png_via_playwright(html_path: Path, png_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": SIZE, "height": SIZE})
            page.goto(f"file://{html_path.resolve()}")
            page.screenshot(path=str(png_path), clip={"x":0,"y":0,"width":SIZE,"height":SIZE})
            browser.close()
        return png_path.exists()
    except Exception:
        return False


def html_to_png_fallback(html_path: Path, png_path: Path) -> bool:
    """matplotlib 임시 안내 이미지 — 한글 깨짐 가능."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10.8, 10.8), dpi=100)
        fig.patch.set_facecolor("#0F172A")
        ax.set_facecolor("#0F172A")
        ax.axis("off")
        ax.text(0.5, 0.5,
                f"[PNG fallback]\nChrome 없음 — HTML 파일을 브라우저로 열어 확인:\n{html_path.name}",
                color="#E6EDF3", fontsize=14, ha="center", va="center",
                transform=ax.transAxes, linespacing=2.0)
        plt.tight_layout(pad=0)
        fig.savefig(str(png_path), dpi=100, bbox_inches="tight", facecolor="#0F172A")
        plt.close(fig)
        return True
    except Exception:
        return False


def convert_html_to_png(html_path: Path, png_path: Path) -> str:
    if html_to_png_via_playwright(html_path, png_path):
        return "playwright"
    if html_to_png_via_chrome(html_path, png_path):
        return "chrome-headless"
    # ❗ 한글 깨진 fallback PNG가 GDrive/Git에 올라가는 사고 방지
    # — Chrome 미설치 환경(샌드박스/CI)에선 PNG를 만들지 않음
    # 사용자가 Mac에서 별도 Chrome headless 실행 필요
    print(f"  ⚠️ Chrome 미설치 — {png_path.name} 생성 스킵 (Mac에서 별도 변환 필요)")
    return "skipped-no-chrome"


# ── 메인 생성 ─────────────────────────────────────────────────
def generate_all(date: str, infographic_data: dict, output_dir: Path) -> dict:
    """가변 빌더 — infographic_data에 있는 섹션만 생성한다.
    - 'market'/'psychology'/'summary'는 전용 빌더 사용
    - 그 외 키('outlook', 'checklist', 'sector', 'risk', 사용자 커스텀)는 generic 빌더
    - 데이터가 빈 dict면 스킵
    - 'insight' 키는 톤북 v1에 따라 이미지 생성 금지 → 자동 스킵
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    html_dir = output_dir / "html"
    html_dir.mkdir(exist_ok=True)

    SKIP_KEYS = {"insight"}  # 톤북 v1: insight는 이미지 X
    results = {}

    for key, data in infographic_data.items():
        if key in SKIP_KEYS:
            print(f"  ⏭️  {key}: 톤북 v1 룰로 이미지 생성 안 함")
            continue
        if not isinstance(data, dict) or not data:
            print(f"  ⏭️  {key}: 데이터 비어있음, 스킵")
            continue

        builder = BUILDERS.get(key)
        if builder is None:
            # 알 수 없는 키 → generic 빌더 (커스텀 섹션 가능)
            html_content = build_generic_html(data, date, key)
        else:
            html_content = builder(data, date)

        html_path = html_dir / f"{date}-{key}.html"
        png_path = output_dir / f"{date}-{key}.png"

        html_path.write_text(html_content, encoding="utf-8")
        method = convert_html_to_png(html_path, png_path)
        results[key] = {"png": str(png_path), "html": str(html_path), "method": method}
        print(f"  ✅ {png_path.name}  [{method}]")

    if not results:
        print("  ⚠️  생성된 인포그래픽 없음 — infographic_data 확인 필요")
    return results


# ── 테스트 데이터 ─────────────────────────────────────────────
TEST_DATA = {
    "market": {
        "title": "코스피, 8천 시대를 향한 발걸음",
        "stats": [
            {"value": "6,219", "label": "코스피 종가", "delta": "+0.44%"},
            {"value": "+22.6%", "label": "4월 수익률", "delta": "글로벌 1위"},
            {"value": "824p", "label": "12M Fwd EPS", "delta": "PER 7.5배"},
            {"value": "+405%", "label": "SK하이닉스 영업이익", "delta": "YoY"},
        ],
        "chips": ["호르무즈 봉쇄", "유가 +7%", "외국인 -2조", "기관 +2조"],
        "points": [
            "EPS 한 달 +24% 상향, 이익 사이클 진행",
            "SK하이닉스 영업이익률 70%대, HBM 독점",
            "지정학 악재를 반도체 실적으로 흡수",
        ],
        "footer_quote": "코스피 8천 시대, 이제는 현실적 목표",
        "footer_author": "이광수 (광수네 복덕방)",
    },
    "psychology": {
        "title": "공포에 팔지 마라, 학습하라",
        "hero_msg": "시장은 이미 메타 학습 중",
        "traps": [
            {"name": "헤드라인 매매", "desc": "뉴스 단어 보고 즉각 매도"},
            {"name": "지수 위치 혼동", "desc": "수치가 크다고 비싼 게 아니다"},
            {"name": "악재에 팔고 호재에 사기", "desc": "최악의 사이클 반복"},
        ],
        "correction": "뉴스 이후가 아닌 이전의 EPS·PER로 판단하라",
        "footer_quote": "오르는 시장도, 빠지는 시장도 — 심리가 결정한다",
        "footer_author": "12시에 만나요",
    },
    "summary": {
        "title": "오늘의 핵심 5포인트",
        "hero_takeaway": "코스피 6,219 상승은 메타 학습의 증거",
        "points": [
            "코스피 6,219.09 (+0.44%) 상승 마감",
            "SK하이닉스 영업이익 37.6조 YoY +405%",
            "12M Fwd EPS 824p, PER 7.5배 저평가",
            "코스피 8,000 목표 복수 기관 상향",
            "공포에 팔고 추격 매수 사이클 경계",
        ],
        "footer_quote": "오늘 배운 것을 내일 매매에 반영한다",
        "footer_author": "12시에 만나요",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--data", help="JSON string")
    ap.add_argument("--data-file", help="JSON file path")
    ap.add_argument("--output", required=True)
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        data = TEST_DATA
    elif args.data_file:
        data = json.loads(Path(args.data_file).read_text(encoding="utf-8"))
    elif args.data:
        data = json.loads(args.data)
    else:
        raise SystemExit("--data 또는 --data-file 또는 --test 필요")

    generate_all(args.date, data, Path(args.output))


if __name__ == "__main__":
    main()
