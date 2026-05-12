"""
stock-youtube-blog-writer / generate_infographics.py
-----------------------------------------------------
블로그 섹션별 인포그래픽 PNG 4장을 생성한다.
출력 크기: 1200×630px (블로그/SNS OG 이미지 최적)

방식: HTML 파일 생성 → Claude in Chrome으로 스크린샷 캡처
- 한글 폰트 깨짐 없음 (브라우저 시스템 폰트 사용)
- 별도 라이브러리 설치 불필요

사용법:
  python generate_infographics.py --date 2026-05-04 \\
    --data '{"market":{...},...}' \\
    --output /path/to/output/

테스트:
  python generate_infographics.py --test --output ./images
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

# ── 디자인 토큰 ─────────────────────────────────────────────
COLORS = {
    "bg":       "#0D1117",
    "card":     "#161B22",
    "border":   "#21262D",
    "text_pri": "#E6EDF3",
    "text_sec": "#8B949E",
    "market":   "#58A6FF",
    "psych":    "#BC8CFF",
    "summary":  "#3FB950",
    "insight":  "#FFA657",
}

SECTION_META = {
    "market":     {"icon": "📊", "label": "시장 분석",   "color": COLORS["market"],  "card_bg": "#1C2B3A"},
    "psychology": {"icon": "🧠", "label": "투자 심리",   "color": COLORS["psych"],   "card_bg": "#1E1B2E"},
    "summary":    {"icon": "✅", "label": "핵심 포인트", "color": COLORS["summary"], "card_bg": "#121D19"},
    "insight":    {"icon": "💡", "label": "인사이트",    "color": COLORS["insight"], "card_bg": "#1F1A0E"},
}

def base_css(accent: str) -> str:
    """accent 색상을 받아 공통 CSS를 반환한다."""
    return f"""
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1200px; height: 630px; overflow: hidden;
    background: {COLORS["bg"]};
    font-family: 'Apple SD Gothic Neo', 'AppleGothic', 'Malgun Gothic',
                 'Noto Sans KR', 'NanumGothic', sans-serif;
    color: {COLORS["text_pri"]};
    position: relative;
  }}
  .accent-bar {{
    position: absolute; left: 0; top: 0;
    width: 7px; height: 100%;
    background: {accent};
  }}
  .container {{
    padding: 36px 48px 28px 64px;
    height: 100%; display: flex; flex-direction: column;
  }}
  .header {{ margin-bottom: 16px; }}
  .section-title {{
    font-size: 26px; font-weight: 700;
    color: {COLORS["text_pri"]}; line-height: 1.2;
  }}
  .date {{ font-size: 13px; color: {COLORS["text_sec"]}; margin-top: 6px; }}
  .divider {{
    height: 1px; background: {COLORS["border"]};
    margin: 14px 0;
  }}
  .footer {{
    margin-top: auto;
    display: flex; justify-content: space-between; align-items: center;
    padding-top: 12px; border-top: 1px solid {COLORS["border"]};
    font-size: 12px; color: {COLORS["text_sec"]};
  }}
  .footer-tag {{ color: {accent}; font-weight: 600; }}
"""


# ── 섹션별 HTML 빌더 ─────────────────────────────────────────

def build_market_html(data: dict, date: str, accent: str, card_bg: str) -> str:
    key_stat = data.get("key_stat", "—")
    points   = data.get("points", [])[:4]
    title    = data.get("title", "시장 분석 & 투자 전략")
    icon     = SECTION_META["market"]["icon"]

    pts_html = "".join(f"""
      <div class="point">
        <span class="badge">{i+1}</span>
        <span class="pt-text">{p}</span>
      </div>""" for i, p in enumerate(points))

    css = base_css(accent) + f"""
      .body {{ display: flex; gap: 40px; flex: 1; align-items: flex-start; margin-top: 4px; }}
      .stat-card {{
        min-width: 220px; max-width: 220px; height: 180px;
        background: {card_bg}; border-radius: 14px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 10px;
        border: 1px solid {accent}22;
      }}
      .stat-value {{ font-size: 38px; font-weight: 800; color: {accent}; }}
      .stat-label {{ font-size: 13px; color: {COLORS["text_sec"]}; }}
      .points-wrap {{ flex: 1; }}
      .points-label {{ font-size: 12px; color: {COLORS["text_sec"]}; margin-bottom: 10px; letter-spacing: 0.5px; }}
      .point {{
        display: flex; align-items: center; gap: 14px;
        margin-bottom: 16px;
      }}
      .badge {{
        width: 26px; height: 26px; border-radius: 50%;
        background: {accent}; color: {COLORS["bg"]};
        font-size: 12px; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }}
      .pt-text {{ font-size: 14px; color: {COLORS["text_pri"]}; line-height: 1.4; }}
    """

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{css}</style></head><body>
<div class="accent-bar"></div>
<div class="container">
  <div class="header">
    <div class="section-title">{icon}&nbsp; {title}</div>
    <div class="date">{date}</div>
  </div>
  <div class="divider"></div>
  <div class="body">
    <div class="stat-card">
      <div class="stat-value">{key_stat}</div>
      <div class="stat-label">핵심 지표</div>
    </div>
    <div class="points-wrap">
      <div class="points-label">주요 포인트</div>
      {pts_html}
    </div>
  </div>
  <div class="footer">
    <span>12시에 만나요 | 주식 분석 블로그</span>
    <span class="footer-tag">{icon} 시장 분석</span>
  </div>
</div>
</body></html>"""


def build_psychology_html(data: dict, date: str, accent: str, card_bg: str) -> str:
    key_stat = data.get("key_stat", "주의")
    points   = data.get("points", [])[:3]
    title    = data.get("title", "투자 심리 & 행동 교정")
    icon     = SECTION_META["psychology"]["icon"]
    labels   = [("함정", accent), ("함정", accent), ("교정", COLORS["summary"])]

    pts_html = "".join(f"""
      <div class="point">
        <span class="tag" style="color:{labels[i][1] if i < len(labels) else accent};
          border-color:{labels[i][1] if i < len(labels) else accent}22">
          {labels[i][0] if i < len(labels) else "—"}
        </span>
        <span class="pt-text">{p}</span>
      </div>""" for i, p in enumerate(points))

    css = base_css(accent) + f"""
      .body {{ display: flex; gap: 40px; flex: 1; align-items: flex-start; margin-top: 4px; }}
      .warn-card {{
        min-width: 220px; max-width: 220px; height: 180px;
        background: {card_bg}; border-radius: 14px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 12px;
        border: 1px solid {accent}22;
      }}
      .warn-icon {{ font-size: 36px; }}
      .warn-text {{ font-size: 20px; font-weight: 800; color: {accent}; text-align: center; padding: 0 12px; }}
      .points-wrap {{ flex: 1; }}
      .list-label {{ font-size: 12px; color: {COLORS["text_sec"]}; margin-bottom: 10px; letter-spacing: 0.5px; }}
      .point {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 18px; }}
      .tag {{
        font-size: 10px; font-weight: 700; padding: 3px 8px;
        border: 1px solid; border-radius: 4px; flex-shrink: 0; margin-top: 2px;
      }}
      .pt-text {{ font-size: 14px; color: {COLORS["text_pri"]}; line-height: 1.5; }}
    """

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{css}</style></head><body>
<div class="accent-bar"></div>
<div class="container">
  <div class="header">
    <div class="section-title">{icon}&nbsp; {title}</div>
    <div class="date">{date}</div>
  </div>
  <div class="divider"></div>
  <div class="body">
    <div class="warn-card">
      <div class="warn-icon">⚠️</div>
      <div class="warn-text">{key_stat}</div>
    </div>
    <div class="points-wrap">
      <div class="list-label">체크리스트</div>
      {pts_html}
    </div>
  </div>
  <div class="footer">
    <span>12시에 만나요 | 주식 분석 블로그</span>
    <span class="footer-tag">{icon} 투자 심리</span>
  </div>
</div>
</body></html>"""


def build_summary_html(data: dict, date: str, accent: str, card_bg: str) -> str:
    points = data.get("points", [])[:5]
    title  = data.get("title", "오늘의 핵심 포인트")
    icon   = SECTION_META["summary"]["icon"]

    pts_html = "".join(f"""
      <div class="point">
        <div class="badge">{i+1}</div>
        <div class="pt-card"><span class="pt-text">{p}</span></div>
      </div>""" for i, p in enumerate(points))

    gap = 14 if len(points) >= 5 else 18

    css = base_css(accent) + f"""
      .body {{ flex: 1; margin-top: 4px; }}
      .point {{ display: flex; align-items: center; gap: 16px; margin-bottom: {gap}px; }}
      .badge {{
        width: 34px; height: 34px; border-radius: 50%;
        background: {accent}; color: {COLORS["bg"]};
        font-size: 15px; font-weight: 800;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }}
      .pt-card {{
        flex: 1; background: {COLORS["card"]}; border-radius: 8px;
        padding: 10px 18px;
      }}
      .pt-text {{ font-size: 14px; color: {COLORS["text_pri"]}; line-height: 1.4; }}
    """

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{css}</style></head><body>
<div class="accent-bar"></div>
<div class="container">
  <div class="header">
    <div class="section-title">{icon}&nbsp; {title}</div>
    <div class="date">{date}</div>
  </div>
  <div class="divider"></div>
  <div class="body">{pts_html}</div>
  <div class="footer">
    <span>12시에 만나요 | 주식 분석 블로그</span>
    <span class="footer-tag">{icon} 핵심 포인트</span>
  </div>
</div>
</body></html>"""


def build_insight_html(data: dict, date: str, accent: str, card_bg: str) -> str:
    quote = data.get("quote", "오늘 영상에서 얻은 핵심 한 줄")
    title = data.get("title", "내 인사이트")
    icon  = SECTION_META["insight"]["icon"]

    css = base_css(accent) + f"""
      .body {{
        flex: 1; display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        padding: 10px 0;
      }}
      .quote-wrap {{
        text-align: center; position: relative;
        padding: 0 40px; max-width: 880px;
      }}
      .open-quote, .close-quote {{
        font-size: 80px; color: {accent}; opacity: 0.35;
        font-family: Georgia, serif; line-height: 0.6;
      }}
      .open-quote {{ float: left; margin-right: 8px; }}
      .close-quote {{ float: right; margin-left: 8px; }}
      .quote-text {{
        font-size: 22px; font-weight: 700;
        color: {COLORS["text_pri"]}; line-height: 1.65;
        text-align: center; clear: both;
        padding: 8px 0;
      }}
      .quote-line {{
        width: 200px; height: 1px; background: {accent};
        opacity: 0.45; margin: 16px auto 10px;
      }}
      .quote-attr {{
        font-size: 12px; color: {COLORS["text_sec"]};
        font-style: italic; text-align: center;
      }}
    """

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{css}</style></head><body>
<div class="accent-bar"></div>
<div class="container">
  <div class="header">
    <div class="section-title">{icon}&nbsp; {title}</div>
    <div class="date">{date}</div>
  </div>
  <div class="divider"></div>
  <div class="body">
    <div class="quote-wrap">
      <div class="open-quote">&ldquo;</div>
      <div class="close-quote">&rdquo;</div>
      <div class="quote-text">{quote}</div>
      <div class="quote-line"></div>
      <div class="quote-attr">— 게임/앱 기획자의 시장 인사이트</div>
    </div>
  </div>
  <div class="footer">
    <span>12시에 만나요 | 주식 분석 블로그</span>
    <span class="footer-tag">{icon} 인사이트</span>
  </div>
</div>
</body></html>"""


BUILDERS = {
    "market":     build_market_html,
    "psychology": build_psychology_html,
    "summary":    build_summary_html,
    "insight":    build_insight_html,
}


# ── HTML → PNG 변환 ──────────────────────────────────────────

def html_to_png_via_chrome(html_path: Path, png_path: Path) -> bool:
    """Chrome headless로 HTML을 PNG로 변환. 실패 시 False 반환."""
    import subprocess
    chrome_candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome", "chromium-browser", "chromium",
    ]
    for chrome in chrome_candidates:
        try:
            result = subprocess.run([
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--window-size=1200,630",
                f"--screenshot={png_path}",
                f"file://{html_path.resolve()}",
            ], capture_output=True, timeout=15)
            if png_path.exists() and png_path.stat().st_size > 1000:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def html_to_png_via_playwright(html_path: Path, png_path: Path) -> bool:
    """playwright chromium으로 변환 (설치된 경우)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 630})
            page.goto(f"file://{html_path.resolve()}")
            page.screenshot(path=str(png_path), clip={"x":0,"y":0,"width":1200,"height":630})
            browser.close()
        return png_path.exists()
    except Exception:
        return False


def html_to_png_fallback(html_path: Path, png_path: Path) -> bool:
    """matplotlib로 HTML 경로를 텍스트 이미지로 변환 (최후 수단, 한글 깨짐 가능)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(12, 6.3), dpi=100)
        fig.patch.set_facecolor("#0D1117")
        ax.set_facecolor("#0D1117")
        ax.axis("off")
        ax.text(0.5, 0.5,
                f"[미리보기 불가]\n한글 폰트 미설치\nHTML 파일을 Chrome에서 열어 확인하세요:\n{html_path.name}",
                color="#E6EDF3", fontsize=14, ha="center", va="center",
                transform=ax.transAxes, linespacing=2.0)
        plt.tight_layout(pad=0)
        fig.savefig(str(png_path), dpi=100, bbox_inches="tight", facecolor="#0D1117")
        plt.close(fig)
        return True
    except Exception:
        return False


def convert_html_to_png(html_path: Path, png_path: Path) -> str:
    """가능한 방법으로 HTML → PNG 변환. 사용한 방법 반환."""
    if html_to_png_via_playwright(html_path, png_path):
        return "playwright"
    if html_to_png_via_chrome(html_path, png_path):
        return "chrome-headless"
    html_to_png_fallback(html_path, png_path)
    return "fallback (HTML 파일을 브라우저로 열어 확인하세요)"


# ── 메인 생성 로직 ────────────────────────────────────────────

def generate_all(date: str, infographic_data: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_dir = output_dir / "html"
    html_dir.mkdir(exist_ok=True)

    results = {}
    for key, builder in BUILDERS.items():
        data     = infographic_data.get(key, {})
        meta     = SECTION_META[key]
        accent   = meta["color"]
        card_bg  = meta["card_bg"]

        html_path = html_dir / f"{date}-{key}.html"
        png_path  = output_dir / f"{date}-{key}.png"

        html_content = builder(data, date, accent, card_bg)
        html_path.write_text(html_content, encoding="utf-8")

        method = convert_html_to_png(html_path, png_path)
        results[key] = {"png": str(png_path), "html": str(html_path), "method": method}
        print(f"  ✅ {png_path.name}  [{method}]")

    return results


# ── 테스트 데이터 ─────────────────────────────────────────────
TEST_DATA = {
    "market": {
        "title": "시장 분석 & 투자 전략",
        "key_stat": "+12.4%",
        "points": [
            "나스닥 기술주 12주 연속 상승세 지속",
            "빅테크 4사 합산 시총 15조 달러 돌파",
            "금리 동결 기대감에 성장주 재평가 시작",
            "AI 반도체 수요 2025년 전년비 +87% 전망",
        ],
    },
    "psychology": {
        "title": "투자 심리 & 행동 교정",
        "key_stat": "FOMO 주의",
        "points": [
            "급등 후 뒤늦은 추격 매수 — 평균 -18% 손실",
            "손절 타이밍 놓치면 평단 물타기 반복",
            "분할 매수 원칙 준수로 리스크 분산",
        ],
    },
    "summary": {
        "title": "오늘의 핵심 포인트",
        "points": [
            "금리 동결 시그널은 성장주 재진입 기회",
            "AI 수혜주 중 실적이 뒷받침되는 종목만 선별",
            "변동성 구간에서 현금 비중 30% 이상 유지",
            "섹터 로테이션: 반도체 → 소프트웨어로 이동 중",
        ],
    },
    "insight": {
        "title": "내 인사이트",
        "quote": "시장은 항상 기대보다 오래 비이성적일 수 있다.\n하지만 기업 실적은 거짓말을 하지 않는다.",
    },
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="블로그 섹션별 인포그래픽 PNG 생성")
    parser.add_argument("--date",   default=datetime.today().strftime("%Y-%m-%d"))
    parser.add_argument("--data",   default=None, help="인포그래픽 데이터 JSON 문자열")
    parser.add_argument("--output", default="./images")
    parser.add_argument("--test",   action="store_true", help="테스트 데이터로 실행")
    args = parser.parse_args()

    data = TEST_DATA if (args.test or not args.data) else json.loads(args.data)
    output_dir = Path(args.output) / args.date

    print(f"\n🖼  인포그래픽 생성 시작 ({args.date})")
    print(f"   저장 위치: {output_dir}\n")

    results = generate_all(args.date, data, output_dir)

    print(f"\n🎉 완료! 생성된 파일:")
    for key, info in results.items():
        print(f"   PNG : {info['png']}")
        print(f"   HTML: {info['html']}  (브라우저에서 직접 확인 가능)")
