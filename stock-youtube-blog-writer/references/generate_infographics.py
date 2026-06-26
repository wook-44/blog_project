"""
stock-youtube-blog-writer / generate_infographics.py  (v3 — 정사각형 모바일 최적)
================================================================================
- 1080×1080 정사각형 (Instagram/네이버 모바일 친화)
- 4/27 스타일 계승: 그라데이션 다크 네이비, hero 큰 숫자, 빼곡한 카드 그리드
- 톤북 v1: 외곽 padding 최소화, stat-card 4열, 인용구 박스
- 3~5장 가변: 필수 market/psychology/summary + 선택 outlook/sector/risk/checklist
- insight는 본문 텍스트로만 (SKIP_KEYS로 자동 스킵)

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
    # 2026-06-24: 네온 톤다운 — hero 숫자용 소프트(거의 흰색) 그라데이션
    "hero_soft_a": "#F1F5F9",
    "hero_soft_b": "#CBD5E1",
}

ACCENTS = {
    "market":     {"icon": "📊", "label": "MARKET STATUS",       "kor": "시장 분석", "from": "#3B82F6", "to": "#06B6D4", "hero_from": "#F59E0B", "hero_to": "#EF4444"},
    "psychology": {"icon": "🧠", "label": "INVESTMENT PSYCHOLOGY","kor": "투자 심리", "from": "#A78BFA", "to": "#EC4899", "hero_from": "#FBBF24", "hero_to": "#F472B6"},
    "summary":    {"icon": "✅", "label": "KEY POINTS TODAY",     "kor": "핵심 포인트","from": "#10B981", "to": "#06B6D4", "hero_from": "#10B981", "hero_to": "#3B82F6"},
    "outlook":    {"icon": "🔭", "label": "MARKET OUTLOOK",       "kor": "전망/관전 포인트","from": "#0EA5E9", "to": "#22D3EE", "hero_from": "#22D3EE", "hero_to": "#A78BFA"},
    "checklist":  {"icon": "☑️", "label": "ACTION CHECKLIST",     "kor": "체크리스트","from": "#F97316", "to": "#EF4444", "hero_from": "#F97316", "hero_to": "#FBBF24"},
    "sector":     {"icon": "🏭", "label": "SECTOR ROTATION",      "kor": "섹터/순환매","from": "#14B8A6", "to": "#0EA5E9", "hero_from": "#14B8A6", "hero_to": "#3B82F6"},
    "risk":       {"icon": "⚠️", "label": "RISK FACTORS",         "kor": "리스크",    "from": "#EF4444", "to": "#F97316", "hero_from": "#EF4444", "hero_to": "#FBBF24"},
    # ── v2 영상 리뷰 포맷: 코너별 리뷰 기준 ──
    "news":       {"icon": "📰", "label": "MIDDAY MONEY NEWS",    "kor": "정오의 머니 뉴스","from": "#3B82F6", "to": "#06B6D4", "hero_from": "#F59E0B", "hero_to": "#EF4444"},
    "flows":      {"icon": "🔁", "label": "FLOWS & STOCKS",       "kor": "수급 & 종목","from": "#14B8A6", "to": "#0EA5E9", "hero_from": "#14B8A6", "hero_to": "#3B82F6"},
    "gwangsoo":   {"icon": "🗣️", "label": "GWANGSOO'S WARNING",   "kor": "광수생각",  "from": "#A78BFA", "to": "#EC4899", "hero_from": "#FBBF24", "hero_to": "#F472B6"},
}

# 알 수 없는 키 fallback (회색 톤)
DEFAULT_ACCENT = {"icon": "📌", "label": "SECTION", "kor": "섹션", "from": "#94A3B8", "to": "#64748B", "hero_from": "#94A3B8", "hero_to": "#64748B"}


def fit_font(text: str, max_width: float, base_size: int, char_factor: float = 0.55, min_size: int = 24) -> int:
    """텍스트가 max_width 안에 들어오도록 폰트 크기를 자동 축소.
    - char_factor: 폰트 사이즈 대비 평균 글자 너비 비율 (900 weight 기준 0.55)
    - 영문/숫자/특수문자 혼합은 한글보다 좁아서 약간 보수적 추정
    - 추정 너비 = len(text) * size * char_factor (실측 ±10%)
    """
    if not text:
        return base_size
    # 한글이 섞여 있으면 더 넓게 잡음
    has_kor = any('가' <= ch <= '힣' for ch in text)
    cf = max(char_factor, 0.62) if has_kor else char_factor
    est = len(text) * base_size * cf
    if est <= max_width:
        return base_size
    new_size = int(max_width / (len(text) * cf))
    return max(min_size, min(base_size, new_size))


def clamp_attr(text: str, max_width: float, size: int, char_factor: float = 0.62) -> str:
    """추정 너비가 max_width를 넘으면 SVG textLength로 강제 압축(절대 캔버스 밖으로 안 나가게).
    fit_font로 1차 축소 후에도 추정 오차로 넘칠 수 있어, 마지막 안전장치로 사용한다."""
    if not text:
        return ""
    has_kor = any('가' <= ch <= '힣' for ch in text)
    cf = max(char_factor, 0.62) if has_kor else char_factor
    est = len(text) * size * cf
    if est > max_width:
        return f' textLength="{int(max_width)}" lengthAdjust="spacingAndGlyphs"'
    return ""


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
    <stop offset="0%" style="stop-color:{COLORS['hero_soft_a']}"/>
    <stop offset="100%" style="stop-color:{COLORS['hero_soft_b']}"/>
  </linearGradient>
  <!-- 2026-06-24: 네온(글로우) 제거 — 헤로 숫자는 글로우 없이 깔끔하게. 섹션 컬러는 accent bar/칩에만 -->
  <filter id="glow"><feGaussianBlur stdDeviation="0" result="b"/><feMerge><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>"""


def _header(date: str, label: str, title: str, accent_from: str, accent_to: str) -> str:
    """공통 헤더 (섹션 라벨 + 큰 타이틀 + 디바이더). 날짜 배지는 표시 안 함."""
    _title_w = SIZE - 96
    title_size = fit_font(title, _title_w, base_size=58, char_factor=0.68, min_size=30)
    _title_clamp = clamp_attr(title, _title_w, title_size, char_factor=0.68)
    return f"""
  <!-- 상단 accent bar -->
  <rect x="0" y="0" width="{SIZE}" height="8" fill="url(#accent)"/>

  <!-- 섹션 라벨 -->
  <text x="48" y="80" fill="{COLORS['text_dim']}" font-size="24" font-weight="700" letter-spacing="6">{label}</text>

  <!-- 메인 타이틀 -->
  <text x="48" y="148" fill="{COLORS['text_pri']}" font-size="{title_size}" font-weight="800"{_title_clamp}>{title}</text>

  <!-- 디바이더 -->
  <rect x="48" y="160" width="100" height="5" fill="url(#accent)" rx="2"/>
"""


def _footer(footer_quote: str, footer_author: str, accent_from: str = "#3B82F6") -> str:
    """공통 푸터 — 인용구 박스 + 브랜딩. 강조형 카드(좌측 accent 막대 + 흰색 큰 인용)."""
    quote_y = SIZE - 170
    _q_w = SIZE - 96 - 80  # 박스 내부, 좌측 인용부호/우측 여백 제외
    q_size = fit_font(footer_quote, _q_w, base_size=32, char_factor=0.64, min_size=20)
    _q_clamp = clamp_attr(footer_quote, _q_w, q_size, char_factor=0.64)
    return f"""
  <!-- 인용구 박스 -->
  <rect x="48" y="{quote_y}" width="{SIZE-96}" height="120" fill="{COLORS['card_alt']}" rx="16" opacity="0.75"/>
  <rect x="48" y="{quote_y}" width="6" height="120" fill="{accent_from}" rx="3"/>
  <text x="76" y="{quote_y+44}" fill="{accent_from}" font-size="38" font-weight="900">"</text>
  <text x="104" y="{quote_y+50}" fill="#FFFFFF" font-size="{q_size}" font-weight="800"{_q_clamp}>{footer_quote}</text>
  <text x="76" y="{quote_y+92}" fill="{COLORS['text_sec']}" font-size="20" font-weight="700">— {footer_author}</text>

  <!-- 우측 하단 브랜딩 -->
  <text x="{SIZE-48}" y="{SIZE-22}" text-anchor="end" fill="{COLORS['text_dim']}" font-size="17" font-weight="700" letter-spacing="1">12시에 만나요 · 주식 분석 블로그</text>
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

    # 방향 자동 판정: 하락 키워드/부호 없으면 ▲ 상승
    # 한국 주식 관례: 상승=빨강, 하락=파랑 (글로벌과 반대)
    _dir_str = f"{hero_delta} {hero_value} {hero_label}"
    is_down = any(k in _dir_str for k in ['▼', '↓', '하락', '폭락', '급락']) or _dir_str.lstrip().startswith('-')
    # delta 텍스트에서 ▲/▼ 글리프 제거 (폴리곤이 이미 표시)
    hero_delta_clean = hero_delta.replace('▲', '').replace('▼', '').strip()
    if is_down:
        # 하락 = 파랑(▼)
        _poly_pts = f"{SIZE-180},220 {SIZE-120},220 {SIZE-150},275"
        _poly_color = "#3B82F6"
    else:
        # 상승 = 빨강(▲)
        _poly_pts = f"{SIZE-180},275 {SIZE-120},275 {SIZE-150},220"
        _poly_color = "#EF4444"

    # 카드 3개 (가로 배치, 카드 사이 간격 16px)
    card_w = (SIZE - 96 - 32) / 3  # 외곽 padding 48*2 = 96, 카드 사이 16*2 = 32
    cards_y = 380
    card_h = 180
    cards_svg = ""
    for i, s in enumerate(sub):
        x = 48 + i * (card_w + 16)
        val = s.get('value', '—')
        # 카드 안쪽 24px씩 padding 확보
        val_size = fit_font(val, card_w - 48, base_size=58, char_factor=0.55, min_size=30)
        label = s.get('label', '')
        label_size = fit_font(label, card_w - 24, base_size=19, char_factor=0.65, min_size=15)
        delta = s.get('delta', '')
        delta_size = fit_font(delta, card_w - 24, base_size=18, char_factor=0.62, min_size=14)
        cards_svg += f"""
  <rect x="{x}" y="{cards_y}" width="{card_w}" height="{card_h}" fill="{COLORS['card']}" rx="14" stroke="{COLORS['border']}" stroke-width="1"/>
  <text x="{x+card_w/2}" y="{cards_y+40}" text-anchor="middle" fill="{COLORS['text_dim']}" font-size="{label_size}" font-weight="700" letter-spacing="2">{label}</text>
  <text x="{x+card_w/2}" y="{cards_y+112}" text-anchor="middle" fill="{a['from']}" font-size="{val_size}" font-weight="900">{val}</text>
  <text x="{x+card_w/2}" y="{cards_y+154}" text-anchor="middle" fill="{COLORS['text_sec']}" font-size="{delta_size}">{delta}</text>"""

    # 칩 (5개) — 카드 끝나는 곳 아래 (자동 줄바꿈)
    chip_y = cards_y + card_h + 24
    chip_x = 48
    chip_h = 42
    chip_max_x = SIZE - 48
    chips_svg = ""
    if chips:
        for c in chips:
            chip_w = max(len(c) * 16 + 32, 80)
            # 줄바꿈
            if chip_x + chip_w > chip_max_x:
                chip_x = 48
                chip_y += chip_h + 10
            chips_svg += f"""
  <rect x="{chip_x}" y="{chip_y}" width="{chip_w}" height="{chip_h}" fill="{a['from']}1A" rx="21" stroke="{a['from']}55" stroke-width="1"/>
  <text x="{chip_x+chip_w/2}" y="{chip_y+27}" text-anchor="middle" fill="{a['from']}" font-size="18" font-weight="700">{c}</text>"""
            chip_x += chip_w + 10
        chip_bottom = chip_y + chip_h
    else:
        chip_bottom = chip_y

    # 주요 포인트 3개 — 칩 아래
    points_y = chip_bottom + 36
    points_svg = ""
    if points:
        points_svg = f"""
  <text x="48" y="{points_y}" fill="{COLORS['text_dim']}" font-size="19" font-weight="700" letter-spacing="2">주요 포인트</text>"""
        for i, p in enumerate(points):
            y = points_y + 42 + i * 42
            points_svg += f"""
  <circle cx="60" cy="{y-7}" r="14" fill="{a['from']}"/>
  <text x="60" y="{y-2}" text-anchor="middle" fill="{COLORS['bg_start']}" font-size="18" font-weight="800">{i+1}</text>
  <text x="86" y="{y}" fill="{COLORS['text_pri']}" font-size="23" font-weight="700">{p}</text>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}

  <!-- HERO 영역 -->
  <text x="48" y="270" fill="url(#hero)" font-size="{fit_font(hero_value, SIZE-260, base_size=118, char_factor=0.60, min_size=56)}" font-weight="900" filter="url(#glow)"{clamp_attr(hero_value, SIZE-260, fit_font(hero_value, SIZE-260, base_size=118, char_factor=0.60, min_size=56), char_factor=0.60)}>{hero_value}</text>
  <text x="48" y="318" fill="{COLORS['text_sec']}" font-size="24" font-weight="700">{hero_label}</text>

  <!-- 우측 변동 표시 (방향 자동 분기) -->
  <polygon points="{_poly_pts}" fill="{_poly_color}" opacity="0.95"/>
  <text x="{SIZE-150}" y="312" text-anchor="middle" fill="{_poly_color}" font-size="22" font-weight="800">{hero_delta_clean}</text>

  {cards_svg}
  {chips_svg}
  {points_svg}
{_footer(footer_q or '오늘의 시장은 숫자가 말한다', footer_a, a['from'])}
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
  <rect x="{x}" y="{cards_y}" width="{card_w}" height="290" fill="{COLORS['card']}" rx="16" stroke="{a['from']}44" stroke-width="2"/>
  <circle cx="{x+card_w/2}" cy="{cards_y+66}" r="44" fill="{a['from']}22"/>
  <text x="{x+card_w/2}" y="{cards_y+82}" text-anchor="middle" font-size="53">{['😱','🤯','😩'][i] if i<3 else '⚠️'}</text>
  <text x="{x+card_w/2}" y="{cards_y+158}" text-anchor="middle" fill="{a['from']}" font-size="29" font-weight="800">{t.get('name','함정')}</text>
  <foreignObject x="{x+16}" y="{cards_y+182}" width="{card_w-32}" height="96">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:{COLORS['text_sec']};font-size:20px;line-height:1.5;text-align:center;font-family:NanumGothic,sans-serif;word-break:keep-all;overflow-wrap:break-word">{t.get('desc','')}</div>
  </foreignObject>"""

    # 교정 카드 (큰 카드, 함정 아래)
    cor_y = cards_y + 310
    correction_svg = f"""
  <rect x="48" y="{cor_y}" width="{SIZE-96}" height="160" fill="{a['to']}1A" rx="16" stroke="{a['to']}66" stroke-width="2"/>
  <text x="80" y="{cor_y+48}" fill="{a['to']}" font-size="20" font-weight="800" letter-spacing="3">✓ 교정 방법</text>
  <foreignObject x="80" y="{cor_y+62}" width="{SIZE-160}" height="92">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#FFFFFF;font-size:31px;font-weight:700;line-height:1.45;font-family:NanumGothic,sans-serif;word-break:keep-all;overflow-wrap:break-word">{correction}</div>
  </foreignObject>"""

    # Hero 메시지 (헤더 아래, 함정 위)
    hero_svg = ""
    if hero_msg:
        _hm_w = SIZE - 96
        hm_size = fit_font(hero_msg, _hm_w, base_size=62, char_factor=0.66, min_size=34)
        _hm_clamp = clamp_attr(hero_msg, _hm_w, hm_size, char_factor=0.66)
        hero_svg = f"""
  <text x="48" y="250" fill="url(#hero)" font-size="{hm_size}" font-weight="900" filter="url(#glow)"{_hm_clamp}>{hero_msg}</text>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}
  {hero_svg}
  {cards_svg}
  {correction_svg}
{_footer(footer_q or '오르는 시장도, 빠지는 시장도 — 결국 심리가 결정한다', footer_a, a['from'])}
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
  <rect x="48" y="200" width="{SIZE-96}" height="160" fill="{a['from']}1A" rx="18" stroke="{a['from']}66" stroke-width="2"/>
  <text x="80" y="244" fill="{a['from']}" font-size="20" font-weight="800" letter-spacing="3">⭐ TODAY'S TAKEAWAY</text>
  <foreignObject x="80" y="260" width="{SIZE-160}" height="94">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#FFFFFF;font-size:36px;font-weight:800;line-height:1.4;font-family:NanumGothic,sans-serif;word-break:keep-all;overflow-wrap:break-word">{hero_takeaway}</div>
  </foreignObject>"""

    # 5 포인트 (큰 번호 + 텍스트, 컴팩트 리스트)
    pts_y = 380
    pts_svg = ""
    for i, p in enumerate(points):
        y = pts_y + i * 92
        pts_svg += f"""
  <rect x="48" y="{y}" width="{SIZE-96}" height="92" fill="{COLORS['card']}" rx="12" stroke="{COLORS['border']}" stroke-width="1"/>
  <circle cx="92" cy="{y+46}" r="30" fill="url(#accent)"/>
  <text x="92" y="{y+57}" text-anchor="middle" fill="{COLORS['bg_start']}" font-size="31" font-weight="900">{i+1}</text>
  <foreignObject x="142" y="{y+18}" width="{SIZE-204}" height="60">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:#FFFFFF;font-size:25px;font-weight:700;line-height:1.4;font-family:NanumGothic,sans-serif;display:flex;align-items:center;height:56px;word-break:keep-all;overflow-wrap:break-word">{p}</div>
  </foreignObject>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}
  {hero_svg}
  {pts_svg}
{_footer(footer_q or '오늘 배운 것을 내일 매매에 반영한다', footer_a, a['from'])}
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
  <text x="48" y="320" fill="url(#hero)" font-size="120" font-weight="900" filter="url(#glow)">{hero_value}</text>
  <text x="48" y="358" fill="{COLORS['text_sec']}" font-size="22" font-weight="700">{hero_label}</text>"""
        if hero_delta:
            hero_svg += f"""
  <text x="{SIZE-150}" y="335" text-anchor="middle" fill="{a['from']}" font-size="22" font-weight="800">{hero_delta}</text>"""

    # 카드 (있을 때만, 1~4개)
    cards_y = 400 if hero_value else 260
    card_h = 150
    cards_svg = ""
    n = len(stats)
    if n > 0:
        gap = 16
        total_gap = gap * (n - 1)
        card_w = (SIZE - 96 - total_gap) / n
        for i, s in enumerate(stats):
            x = 48 + i * (card_w + gap)
            val = s.get('value', '—')
            val_size = fit_font(val, card_w - 40, base_size=48, char_factor=0.55, min_size=26)
            label = s.get('label', '')
            label_size = fit_font(label, card_w - 24, base_size=17, char_factor=0.65, min_size=13)
            delta = s.get('delta', '')
            delta_size = fit_font(delta, card_w - 24, base_size=17, char_factor=0.62, min_size=13)
            cards_svg += f"""
  <rect x="{x}" y="{cards_y}" width="{card_w}" height="{card_h}" fill="{COLORS['card']}" rx="14" stroke="{COLORS['border']}" stroke-width="1"/>
  <text x="{x+card_w/2}" y="{cards_y+36}" text-anchor="middle" fill="{COLORS['text_dim']}" font-size="{label_size}" font-weight="700" letter-spacing="2">{label}</text>
  <text x="{x+card_w/2}" y="{cards_y+96}" text-anchor="middle" fill="{a['from']}" font-size="{val_size}" font-weight="900">{val}</text>
  <text x="{x+card_w/2}" y="{cards_y+130}" text-anchor="middle" fill="{COLORS['text_sec']}" font-size="{delta_size}">{delta}</text>"""

    # 칩 (자동 줄바꿈)
    chip_y = cards_y + card_h + 24 if stats else cards_y
    chip_x = 48
    chip_h = 42
    chip_max_x = SIZE - 48
    chips_svg = ""
    if chips:
        for c in chips:
            chip_w = max(len(c) * 16 + 32, 80)
            if chip_x + chip_w > chip_max_x:
                chip_x = 48
                chip_y += chip_h + 10
            chips_svg += f"""
  <rect x="{chip_x}" y="{chip_y}" width="{chip_w}" height="{chip_h}" fill="{a['from']}1A" rx="21" stroke="{a['from']}55" stroke-width="1"/>
  <text x="{chip_x+chip_w/2}" y="{chip_y+27}" text-anchor="middle" fill="{a['from']}" font-size="18" font-weight="700">{c}</text>"""
            chip_x += chip_w + 10
        chip_bottom = chip_y + chip_h
    else:
        chip_bottom = chip_y

    # 포인트
    points_y = chip_bottom + (36 if chips else 30)
    points_svg = ""
    if points:
        points_svg = f"""
  <text x="48" y="{points_y}" fill="{COLORS['text_dim']}" font-size="17" font-weight="700" letter-spacing="2">주요 포인트</text>"""
        for i, p in enumerate(points):
            y = points_y + 38 + i * 40
            points_svg += f"""
  <circle cx="60" cy="{y-7}" r="13" fill="{a['from']}"/>
  <text x="60" y="{y-2}" text-anchor="middle" fill="{COLORS['bg_start']}" font-size="17" font-weight="800">{i+1}</text>
  <text x="84" y="{y}" fill="{COLORS['text_pri']}" font-size="21" font-weight="700">{p}</text>"""

    svg = f"""<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" font-family="'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
{_common_defs(a['from'], a['to'], a['hero_from'], a['hero_to'])}
  <rect width="{SIZE}" height="{SIZE}" fill="url(#bg)"/>
{_header(date, a['label'], title, a['from'], a['to'])}
  {hero_svg}
  {cards_svg}
  {chips_svg}
  {points_svg}
{_footer(footer_q or a['kor'] + ' 한 줄', footer_a, a['from'])}
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
# ════════════════════════════════════════════════════════════════
# E/F 플랫 리디자인 (2026-06-23 사용자 확정 / 2026-06-26 구현)
#   - "AI티"(그라데이션 글로우·이모지·균일 다크카드 적층) 제거 → 라이트 플랫
#   - E = build_colorblock_html : 베이지 배경 + 원색 컬러블록 2열
#   - F = build_datachart_html  : 흰 배경 + 가로 막대(상승=빨강/하락=파랑)
#   - assign_styles : E_PRI(summary/news/gwangsoo/checklist) / F_PRI(sector/market/flows/outlook/risk)
#   - F인데 막대 데이터 없으면 E로 자동 폴백(빈 차트 방지)
# ════════════════════════════════════════════════════════════════
import re as _re

FLAT = {
    "beige": "#F2EFE8", "ink": "#1A1A1A", "white": "#FFFFFF",
    "grid": "#E5E7EB",
    "up_red": "#E8413A", "down_blue": "#2E6FD6",
    # 컬러블록 팔레트: 빨강/노랑/초록/파랑/먹
    "pal": ["#E8413A", "#F2B705", "#2FA84F", "#2E6FD6", "#1A1A1A"],
}


def _tw(s: str, size: float) -> float:
    w = 0.0
    for ch in s:
        o = ord(ch)
        if ch == ' ':
            w += size * 0.30
        elif 0xAC00 <= o <= 0xD7A3 or 0x3000 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF:
            w += size * 1.02
        elif ch in '·—…':
            w += size * 1.0
        elif ch in '|ㅣ!.,:;\'"`()[]':
            w += size * 0.34
        elif ch.isdigit():
            w += size * 0.58
        else:
            w += size * 0.60
    return w


def _esc(s: str) -> str:
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _wrap(text: str, max_w: float, size: float):
    lines, cur = [], ''
    for word in str(text).split(' '):
        cand = (cur + ' ' + word).strip()
        if _tw(cand, size) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            while _tw(word, size) > max_w and len(word) > 1:
                i = len(word)
                while i > 1 and _tw(word[:i], size) > max_w:
                    i -= 1
                lines.append(word[:i]); word = word[i:]
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _block(text: str, x: float, y: float, max_w: float, size: float, fill: str,
           weight: int = 800, line_h: float = None, anchor: str = 'start'):
    line_h = line_h or size * 1.32
    lines = _wrap(text, max_w, size)
    tspans = ''.join(
        f'<tspan x="{x:.0f}" y="{y + i*line_h:.0f}">{_esc(ln)}</tspan>'
        for i, ln in enumerate(lines))
    return (f'<text text-anchor="{anchor}" fill="{fill}" font-size="{size:.0f}" '
            f'font-weight="{weight}">{tspans}</text>', len(lines))


def _fit(text: str, max_w: float, base: int, min_size: int = 30) -> int:
    s = base
    while s > min_size and _tw(text, s) > max_w:
        s -= 1
    return s


def _flat_label_title(parts, label, title, ink):
    parts.append(f'<rect x="0" y="0" width="{SIZE}" height="10" fill="{ink}"/>')
    parts.append(f'<text x="64" y="94" fill="{ink}" font-size="24" font-weight="800" '
                 f'letter-spacing="6" opacity="0.55">{_esc(label)}</text>')
    ts = _fit(title, SIZE - 128, 56, 34)
    tb, tl = _block(title, 64, 156, SIZE - 128, ts, ink, 900, line_h=ts * 1.18)
    parts.append(tb)
    return int(156 + tl * ts * 1.18)


def _flat_footer(parts, fq, ink, max_w=SIZE - 280):
    if fq:
        qy = SIZE - 96
        parts.append(f'<rect x="48" y="{qy-34}" width="6" height="62" fill="{ink}"/>')
        qb, _ = _block(fq, 72, qy, max_w, 26, ink, 800, line_h=34)
        parts.append(qb)
    parts.append(f'<text x="{SIZE-48}" y="{SIZE-26}" text-anchor="end" fill="{ink}" '
                 f'opacity="0.45" font-size="17" font-weight="700">12시에 만나요 · 주식 분석 블로그</text>')


def _extract_metric(s: str) -> str:
    m = _re.search(r'-?\d[\d,]*\.?\d*\s*%', str(s))
    if m:
        return m.group(0).replace(' ', '')
    m = _re.search(r'\d[\d,]*', str(s))
    return ''


def parse_bars(data: dict):
    """data['bars']=[{label,pct}] 우선, 없으면 stats의 value/delta에서 부호 % 추출."""
    out = []
    for b in (data.get('bars') or []):
        try:
            out.append((str(b.get('label', '')), float(b.get('pct'))))
        except (TypeError, ValueError):
            pass
    if out:
        return out[:6]
    for s in (data.get('stats') or []):
        for fld in ('value', 'delta'):
            m = _re.search(r'(-?\d+(?:\.\d+)?)\s*%', str(s.get(fld, '')))
            if m:
                out.append((str(s.get('label', '')), float(m.group(1))))
                break
    return out[:6]


def build_colorblock_html(data: dict, date: str, key: str = 'section') -> str:
    """E — 베이지 배경 + 원색 컬러블록 (플랫)."""
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    F = FLAT
    beige, ink, pal = F['beige'], F['ink'], F['pal']
    title = data.get('title') or a['kor']
    parts = [f'<rect width="{SIZE}" height="{SIZE}" fill="{beige}"/>']
    y = _flat_label_title(parts, a['label'], title, ink) + 40

    hero_v = data.get('hero_value', '')
    hero_l = data.get('hero_label', '')
    takeaway = data.get('hero_takeaway', '')
    stats = data.get('stats') or []
    points = data.get('points') or []
    ci = 0

    # 1) hero band (full width)
    if hero_v:
        col = pal[ci % len(pal)]; ci += 1
        bh = 188
        parts.append(f'<rect x="48" y="{y}" width="{SIZE-96}" height="{bh}" fill="{col}" rx="18"/>')
        hs = _fit(hero_v, SIZE - 96 - 360, 92, 46)
        parts.append(f'<text x="84" y="{y+116}" fill="#FFFFFF" font-size="{hs}" font-weight="900">{_esc(hero_v)}</text>')
        lb, _ = _block(hero_l, SIZE - 84, y + 92, 340, 30, "#FFFFFF", 700, line_h=38, anchor='end')
        parts.append(lb)
        y += bh + 22
    elif takeaway:
        col = pal[ci % len(pal)]; ci += 1
        tl = _wrap(takeaway, SIZE - 96 - 72, 34)
        bh = max(150, 56 + len(tl) * 48)
        parts.append(f'<rect x="48" y="{y}" width="{SIZE-96}" height="{bh}" fill="{col}" rx="18"/>')
        tb, _ = _block(takeaway, 84, y + 64, SIZE - 96 - 72, 34, "#FFFFFF", 800, line_h=48)
        parts.append(tb)
        y += bh + 22

    # 2) grid 2-col from stats(우선) else points
    items = []
    if stats:
        for s in stats[:4]:
            items.append((s.get('value', ''), s.get('label', '')))
    else:
        for p in points[:4]:
            items.append((_extract_metric(p), p))

    n = len(items)
    if n:
        gap = 22
        cols = 2
        cw = (SIZE - 96 - gap) / cols
        rows = (n + cols - 1) // cols
        foot = 150
        avail = (SIZE - foot) - y
        ch = max(150, min(232, (avail - (rows - 1) * gap) / rows))
        for i, (big, small) in enumerate(items):
            r, c = i // cols, i % cols
            bx = 48 + c * (cw + gap)
            by = y + r * (ch + gap)
            col = pal[ci % len(pal)]; ci += 1
            tc = "#1A1A1A" if col == "#F2B705" else "#FFFFFF"
            parts.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{cw:.0f}" height="{ch:.0f}" fill="{col}" rx="16"/>')
            if big:
                bs = _fit(big, cw - 48, 56, 30)
                parts.append(f'<text x="{bx+26:.0f}" y="{by+76:.0f}" fill="{tc}" font-size="{bs}" font-weight="900">{_esc(big)}</text>')
                sb, _ = _block(small, bx + 26, by + 116, cw - 52, 24, tc, 700, line_h=31)
                parts.append(sb)
            else:
                sb, _ = _block(small, bx + 26, by + 58, cw - 52, 27, tc, 800, line_h=37)
                parts.append(sb)

    _flat_footer(parts, data.get('footer_quote', ''), ink)
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(parts) + '</svg>')
    return html_doc(svg)


def build_datachart_html(data: dict, date: str, key: str = 'section') -> str:
    """F — 흰 배경 + 가로 막대 차트 (상승=빨강·하락=파랑)."""
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    F = FLAT
    white, ink, grid = F['white'], F['ink'], F['grid']
    up, down = F['up_red'], F['down_blue']
    title = data.get('title') or a['kor']
    parts = [f'<rect width="{SIZE}" height="{SIZE}" fill="{white}"/>']
    top = _flat_label_title(parts, a['label'], title, ink) + 54

    bars = parse_bars(data)
    maxabs = max((abs(p) for _, p in bars), default=1.0) or 1.0
    n = len(bars)
    chart_bottom = SIZE - 230
    row_h = min(160, (chart_bottom - top) / max(1, n))
    label_w = 280
    x0 = 64 + label_w
    bar_max = SIZE - 72 - x0 - 150
    parts.append(f'<line x1="{x0}" y1="{top-6:.0f}" x2="{x0}" y2="{top + n*row_h:.0f}" stroke="{grid}" stroke-width="3"/>')
    for i, (lab, pct) in enumerate(bars):
        cy = top + i * row_h + row_h / 2
        ls = _fit(lab, label_w - 20, 34, 22)
        parts.append(f'<text x="64" y="{cy+ls*0.34:.0f}" fill="{ink}" font-size="{ls}" font-weight="800">{_esc(lab)}</text>')
        L = abs(pct) / maxabs * bar_max
        col = down if pct < 0 else up
        parts.append(f'<rect x="{x0}" y="{cy-34:.0f}" width="{max(6,L):.0f}" height="68" fill="{col}" rx="8"/>')
        arrow = '▼' if pct < 0 else '▲'
        parts.append(f'<text x="{x0+max(6,L)+18:.0f}" y="{cy+13:.0f}" fill="{col}" font-size="38" font-weight="900">{arrow} {abs(pct):.1f}%</text>')

    # key-stat strip (hero)
    hero_v = data.get('hero_value', '')
    hero_l = data.get('hero_label', '')
    if hero_v:
        # 키-스탯 띠가 있으면 푸터 인용구는 생략(겹침 방지) — 띠 + 브랜딩만
        sy = SIZE - 150
        parts.append(f'<rect x="48" y="{sy}" width="{SIZE-96}" height="74" fill="{ink}" rx="12"/>')
        parts.append(f'<text x="78" y="{sy+49}" fill="#FFFFFF" font-size="34" font-weight="900">{_esc(hero_v)}</text>')
        kl, _ = _block(hero_l, SIZE - 78, sy + 47, 560, 25, "#FFFFFF", 700, line_h=31, anchor='end')
        parts.append(kl)
        parts.append(f'<text x="{SIZE-48}" y="{SIZE-18}" text-anchor="end" fill="{ink}" '
                     f'opacity="0.45" font-size="16" font-weight="700">12시에 만나요 · 주식 분석 블로그</text>')
    else:
        _flat_footer(parts, data.get('footer_quote', ''), ink)
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(parts) + '</svg>')
    return html_doc(svg)


# ════════════════════════════════════════════════════════════════
# 코너별 개별 디자인 콘셉트 (2026-06-26 사용자 요청: "각 이미지마다 디자인 콘셉을 다르게")
#   summary  → bigtype    : 매거진 빅타이포 + 넘버링 리스트 (크림)
#   news     → newscard   : 신문 1면 마스트헤드 + 컬럼 (흰)
#   flows    → barchart   : 가로 막대 차트 (= build_datachart_html, 흰)
#   gwangsoo → checklist  : 원칙 체크리스트 행 카드 (크림)
#   market   → indexboard : 지표 보드(데이터 테이블) (오프화이트)
#   outlook  → timeline   : 관전 포인트 타임라인 (크림)
# ════════════════════════════════════════════════════════════════

def build_bigtype(data: dict, date: str, key: str = 'summary') -> str:
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    cream, ink, accent = "#F4EFE4", "#1A1A1A", FLAT['up_red']
    title = data.get('title') or a['kor']
    take = data.get('hero_takeaway', '') or title
    points = (data.get('points') or [])[:5]
    P = [f'<rect width="{SIZE}" height="{SIZE}" fill="{cream}"/>']
    P.append(f'<rect x="0" y="0" width="{SIZE}" height="10" fill="{accent}"/>')
    P.append(f'<text x="64" y="96" fill="{accent}" font-size="24" font-weight="800" letter-spacing="6">{_esc(a["label"])}</text>')
    # big headline takeaway
    hs = 46
    while len(_wrap(take, SIZE - 128, hs)) > 3 and hs > 32:
        hs -= 2
    hb, hl = _block(take, 64, 168, SIZE - 128, hs, ink, 900, line_h=hs * 1.28)
    P.append(hb)
    y = int(168 + hl * hs * 1.28) + 26
    P.append(f'<rect x="64" y="{y}" width="{SIZE-128}" height="4" fill="{ink}"/>')
    y += 40
    n = max(1, len(points))
    avail = (SIZE - 96) - y
    rh = min(150, avail / n)
    for i, p in enumerate(points):
        ry = y + i * rh
        P.append(f'<text x="64" y="{ry+52:.0f}" fill="{accent}" font-size="46" font-weight="900">{i+1:02d}</text>')
        tb, _ = _block(p, 168, ry + 34, SIZE - 168 - 56, 28, ink, 700, line_h=37)
        P.append(tb)
        if i < n - 1:
            P.append(f'<rect x="168" y="{ry+rh-14:.0f}" width="{SIZE-168-64}" height="1.5" fill="#D8D0BE"/>')
    P.append(f'<text x="{SIZE-48}" y="{SIZE-26}" text-anchor="end" fill="{ink}" opacity="0.45" font-size="17" font-weight="700">12시에 만나요 · 주식 분석 블로그</text>')
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(P) + '</svg>')
    return html_doc(svg)


def build_newscard(data: dict, date: str, key: str = 'news') -> str:
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    white, ink = "#FFFFFF", "#1A1A1A"
    accent = FLAT['up_red']
    title = data.get('title') or a['kor']
    dstr = str(date).replace('-', '.')
    stats = (data.get('stats') or [])[:3]
    hv = data.get('hero_value', ''); hl = data.get('hero_label', '')
    fq = data.get('footer_quote', '')
    P = [f'<rect width="{SIZE}" height="{SIZE}" fill="{white}"/>']
    # masthead
    P.append(f'<rect x="0" y="0" width="{SIZE}" height="78" fill="{ink}"/>')
    P.append(f'<text x="48" y="52" fill="#FFFFFF" font-size="30" font-weight="900" letter-spacing="2">12시에 만나요 · 머니브리프</text>')
    P.append(f'<text x="{SIZE-48}" y="51" text-anchor="end" fill="#FFFFFF" opacity="0.85" font-size="24" font-weight="700">{dstr}</text>')
    # kicker + headline
    P.append(f'<text x="48" y="150" fill="{accent}" font-size="24" font-weight="800" letter-spacing="5">{_esc(a["label"])}</text>')
    ts = _fit(title, SIZE - 96, 52, 32)
    tb, tl = _block(title, 48, 210, SIZE - 96, ts, ink, 900, line_h=ts * 1.18)
    P.append(tb)
    y = int(210 + tl * ts * 1.18) + 24
    P.append(f'<rect x="48" y="{y}" width="{SIZE-96}" height="5" fill="{ink}"/>')
    y += 46
    # lead hero
    if hv:
        hsz = _fit(hv, 520, 96, 52)
        P.append(f'<text x="48" y="{y+78:.0f}" fill="{ink}" font-size="{hsz}" font-weight="900">{_esc(hv)}</text>')
        lb, _ = _block(hl, SIZE - 48, y + 44, 440, 30, ink, 700, line_h=38, anchor='end')
        P.append(lb)
        y += 130
    # 3 columns (newspaper)
    if stats:
        gap = 28
        cw = (SIZE - 96 - gap * (len(stats) - 1)) / len(stats)
        for i, s in enumerate(stats):
            cx = 48 + i * (cw + gap)
            P.append(f'<rect x="{cx:.0f}" y="{y}" width="{cw:.0f}" height="4" fill="{accent}"/>')
            lab, _ = _block(s.get('label', ''), cx, y + 40, cw, 23, "#6B7280", 700, line_h=29)
            P.append(lab)
            vs = _fit(s.get('value', ''), cw, 46, 26)
            P.append(f'<text x="{cx:.0f}" y="{y+104:.0f}" fill="{ink}" font-size="{vs}" font-weight="900">{_esc(s.get("value",""))}</text>')
            dl, _ = _block(s.get('delta', ''), cx, y + 140, cw, 22, "#6B7280", 600, line_h=28)
            P.append(dl)
    # pull quote
    if fq:
        qy = SIZE - 92
        P.append(f'<rect x="48" y="{qy-34}" width="6" height="60" fill="{accent}"/>')
        qb, _ = _block(fq, 72, qy, SIZE - 240, 26, ink, 800, line_h=34)
        P.append(qb)
    P.append(f'<text x="{SIZE-48}" y="{SIZE-22}" text-anchor="end" fill="{ink}" opacity="0.45" font-size="16" font-weight="700">12시에 만나요 · 주식 분석 블로그</text>')
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(P) + '</svg>')
    return html_doc(svg)


def build_checklist(data: dict, date: str, key: str = 'gwangsoo') -> str:
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    cream, ink = "#EFEBE0", "#1A1A1A"
    pal = FLAT['pal']
    title = data.get('title') or a['kor']
    stats = (data.get('stats') or [])[:4]
    points = data.get('points') or []
    fq = data.get('footer_quote', '')
    P = [f'<rect width="{SIZE}" height="{SIZE}" fill="{cream}"/>']
    y0 = _flat_label_title(P, a['label'], title, ink) + 36
    items = []
    if stats:
        for s in stats:
            items.append((s.get('value', ''), (s.get('label', ''), s.get('delta', ''))))
    else:
        for p in points[:4]:
            items.append((p, ('', '')))
    n = max(1, len(items))
    avail = (SIZE - 150) - y0
    rh = min(180, avail / n)
    for i, (head, sub) in enumerate(items):
        ry = y0 + i * rh
        col = pal[i % len(pal)]
        card_h = rh - 18
        P.append(f'<rect x="48" y="{ry:.0f}" width="{SIZE-96}" height="{card_h:.0f}" fill="#FFFFFF" rx="14"/>')
        P.append(f'<rect x="48" y="{ry:.0f}" width="14" height="{card_h:.0f}" fill="{col}" rx="7"/>')
        # marker square
        msz = 56
        my = ry + card_h / 2 - msz / 2
        P.append(f'<rect x="84" y="{my:.0f}" width="{msz}" height="{msz}" fill="{col}" rx="12"/>')
        P.append(f'<circle cx="{84+msz/2:.0f}" cy="{my+msz/2:.0f}" r="9" fill="#FFFFFF"/>')
        hx = 84 + msz + 28
        hs = _fit(str(head), SIZE - hx - 60, 36, 26)
        P.append(f'<text x="{hx:.0f}" y="{ry+card_h/2-2:.0f}" fill="{ink}" font-size="{hs}" font-weight="900">{_esc(head)}</text>')
        subtxt = ' · '.join([t for t in sub if t]) if isinstance(sub, tuple) else str(sub)
        if subtxt:
            sb, _ = _block(subtxt, hx, ry + card_h / 2 + 32, SIZE - hx - 60, 24, "#6B7280", 700, line_h=30)
            P.append(sb)
    _flat_footer(P, fq, ink)
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(P) + '</svg>')
    return html_doc(svg)


def build_indexboard(data: dict, date: str, key: str = 'market') -> str:
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    bg, ink = "#FAFAF7", "#1A1A1A"
    up, down = FLAT['up_red'], FLAT['down_blue']
    title = data.get('title') or a['kor']
    stats = (data.get('stats') or [])[:5]
    fq = data.get('footer_quote', '')
    P = [f'<rect width="{SIZE}" height="{SIZE}" fill="{bg}"/>']
    y0 = _flat_label_title(P, a['label'], title, ink) + 40
    # header row
    colL, colV, colD = 64, SIZE - 430, SIZE - 64
    P.append(f'<text x="{colL}" y="{y0}" fill="#6B7280" font-size="22" font-weight="800" letter-spacing="2">종목·지수</text>')
    P.append(f'<text x="{colV}" y="{y0}" text-anchor="end" fill="#6B7280" font-size="22" font-weight="800">현재</text>')
    P.append(f'<text x="{colD}" y="{y0}" text-anchor="end" fill="#6B7280" font-size="22" font-weight="800">등락</text>')
    y0 += 18
    P.append(f'<rect x="64" y="{y0}" width="{SIZE-128}" height="3" fill="{ink}"/>')
    y0 += 14
    n = max(1, len(stats))
    avail = (SIZE - 200) - y0
    rh = min(140, avail / n)
    for i, s in enumerate(stats):
        ry = y0 + i * rh
        if i % 2 == 1:
            P.append(f'<rect x="56" y="{ry:.0f}" width="{SIZE-112}" height="{rh:.0f}" fill="#FFFFFF" rx="10"/>')
        cy = ry + rh / 2
        lab = s.get('label', ''); val = s.get('value', ''); dlt = s.get('delta', '')
        ls = _fit(lab, colV - colL - 220, 34, 22)
        P.append(f'<text x="{colL}" y="{cy+ls*0.34:.0f}" fill="{ink}" font-size="{ls}" font-weight="800">{_esc(lab)}</text>')
        vs = _fit(val, 280, 44, 26)
        P.append(f'<text x="{colV}" y="{cy+vs*0.34:.0f}" text-anchor="end" fill="{ink}" font-size="{vs}" font-weight="900">{_esc(val)}</text>')
        dcol = down if ('▼' in dlt or '-' in dlt or '하회' in dlt or '하락' in dlt) else (up if '▲' in dlt else "#6B7280")
        ds = _fit(dlt, 360, 26, 17)
        P.append(f'<text x="{colD}" y="{cy+ds*0.34:.0f}" text-anchor="end" fill="{dcol}" font-size="{ds}" font-weight="800">{_esc(dlt)}</text>')
    _flat_footer(P, fq, ink)
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(P) + '</svg>')
    return html_doc(svg)


def build_timeline(data: dict, date: str, key: str = 'outlook') -> str:
    a = ACCENTS.get(key, DEFAULT_ACCENT)
    cream, ink = "#EEF1EC", "#1A1A1A"
    node_pal = ["#E8413A", "#F2B705", "#2FA84F", "#2E6FD6"]
    title = data.get('title') or a['kor']
    stats = (data.get('stats') or [])[:4]
    points = data.get('points') or []
    fq = data.get('footer_quote', '')
    P = [f'<rect width="{SIZE}" height="{SIZE}" fill="{cream}"/>']
    y0 = _flat_label_title(P, a['label'], title, ink) + 50
    items = stats if stats else [{'value': '', 'label': p, 'delta': ''} for p in points[:4]]
    n = max(1, len(items))
    line_x = 110
    avail = (SIZE - 170) - y0
    step = min(190, avail / n)
    P.append(f'<line x1="{line_x}" y1="{y0}" x2="{line_x}" y2="{y0 + (n-1)*step + 40:.0f}" stroke="#C9D0C6" stroke-width="4"/>')
    for i, s in enumerate(items):
        ny = y0 + i * step + 20
        col = node_pal[i % len(node_pal)]
        P.append(f'<circle cx="{line_x}" cy="{ny}" r="20" fill="{col}"/>')
        P.append(f'<circle cx="{line_x}" cy="{ny}" r="8" fill="#FFFFFF"/>')
        tx = line_x + 56
        head = s.get('value', '') or s.get('label', '')
        hs = _fit(str(head), SIZE - tx - 60, 40, 26)
        P.append(f'<text x="{tx}" y="{ny-4:.0f}" fill="{ink}" font-size="{hs}" font-weight="900">{_esc(head)}</text>')
        sub = ' · '.join([t for t in [s.get('label', ''), s.get('delta', '')] if t]) if s.get('value') else ''
        if sub:
            sb, _ = _block(sub, tx, ny + 34, SIZE - tx - 60, 25, "#5B6660", 700, line_h=32)
            P.append(sb)
    _flat_footer(P, fq, ink)
    svg = (f'<svg viewBox="0 0 {SIZE} {SIZE}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="NanumGothic,sans-serif">' + ''.join(P) + '</svg>')
    return html_doc(svg)


# 코너별 콘셉트 라우팅 (표준 6코너). 없으면 assign_styles의 E/F로 폴백.
CONCEPT_MAP = {
    "summary":  build_bigtype,
    "news":     build_newscard,
    "flows":    build_datachart_html,   # barchart
    "gwangsoo": build_checklist,
    "market":   build_indexboard,
    "outlook":  build_timeline,
}


def assign_styles(keys):
    E_PRI = ['summary', 'news', 'gwangsoo', 'checklist', 'psychology']
    F_PRI = ['sector', 'market', 'flows', 'outlook', 'risk']
    st = {}
    for k in keys:
        if k in F_PRI:
            st[k] = 'F'
        else:
            st[k] = 'E'  # E_PRI + 미지정은 E(빈 차트 방지)
    return st


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

    # E/F 플랫 스타일 배정 (2026-06-23 확정)
    styles = assign_styles(list(infographic_data.keys()))

    for key, data in infographic_data.items():
        if key in SKIP_KEYS:
            print(f"  ⏭️  {key}: 톤북 v1 룰로 이미지 생성 안 함")
            continue
        if not isinstance(data, dict) or not data:
            print(f"  ⏭️  {key}: 데이터 비어있음, 스킵")
            continue

        concept = CONCEPT_MAP.get(key)
        if concept is not None:
            # barchart(flows)인데 막대 데이터 부족하면 컬러블록으로 폴백
            if concept is build_datachart_html and len(parse_bars(data)) < 2:
                html_content = build_colorblock_html(data, date, key)
                print(f"  🎨 {key}: concept=colorblock(fallback)")
            else:
                html_content = concept(data, date, key)
                print(f"  🎨 {key}: concept={concept.__name__}")
        else:
            style = styles.get(key, 'E')
            if style == 'F' and len(parse_bars(data)) < 2:
                style = 'E'
            html_content = build_datachart_html(data, date, key) if style == 'F' else build_colorblock_html(data, date, key)
            print(f"  🎨 {key}: style={style}")

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
