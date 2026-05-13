#!/usr/bin/env python3
"""
html_to_png.py
--------------
Playwright(Chrome for Testing)로 인포그래픽 HTML → PNG 변환
NanumGothic 나눔고딕 폰트를 1순위로 강제 적용해 한글 깨짐 없이 렌더링

사용법:
  python3 scripts/html_to_png.py YYYY-MM-DD        # 특정 날짜
  python3 scripts/html_to_png.py --all             # images/ 내 모든 날짜

결과:
  images/YYYY-MM-DD/YYYY-MM-DD-{section}.png
"""

import asyncio
import sys
import glob
from pathlib import Path
from playwright.async_api import async_playwright

BASE = Path(__file__).parent.parent
IMG_BASE = BASE / "images"
USER_DATA_DIR = BASE / ".playwright_profile"

# NanumGothic을 최우선으로 강제 적용하는 CSS
# Google Fonts에서 로드하여 로컬 설치 여부와 무관하게 한글 렌더링 보장
NANUM_FONT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
* {
  font-family: 'NanumGothic', 'Nanum Gothic', 'Apple SD Gothic Neo',
               'Malgun Gothic', 'Noto Sans KR', sans-serif !important;
}
"""


async def html_to_png(html_path: Path, out_path: Path, width: int = 900, height: int = 900):
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": width, "height": height},
        )
        page = await context.new_page()
        file_url = f"file://{html_path.resolve()}"
        await page.goto(file_url, wait_until="networkidle", timeout=20000)
        # NanumGothic 강제 주입 (로컬 설치 여부 무관)
        await page.add_style_tag(content=NANUM_FONT_CSS)
        # 폰트 다운로드 및 렌더링 완료 대기
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(out_path), full_page=False, clip={"x": 0, "y": 0, "width": width, "height": height})  # width/height now 900×900 by default
        await context.close()
        print(f"  ✅ {out_path.name}")


async def process_date(date_str: str):
    html_dir = IMG_BASE / date_str / "html"
    if not html_dir.exists():
        print(f"  ⚠️  {date_str}: html/ 폴더 없음 — 스킵")
        return 0

    html_files = sorted(html_dir.glob("*.html"))
    if not html_files:
        print(f"  ⚠️  {date_str}: HTML 파일 없음 — 스킵")
        return 0

    out_dir = IMG_BASE / date_str
    count = 0
    for html_file in html_files:
        # 파일명에서 섹션명 추출 (예: 2026-04-20-market.html → 2026-04-20-market.png)
        out_name = html_file.stem + ".png"
        out_path = out_dir / out_name
        await html_to_png(html_file, out_path)
        count += 1

    return count


async def main():
    if "--all" in sys.argv:
        # images/ 아래 html/ 폴더가 있는 모든 날짜 처리
        dates = sorted([d.parent.parent.name for d in IMG_BASE.glob("*/html/*.html")])
        dates = sorted(set(dates))
        print(f"📅 전체 {len(dates)}개 날짜 처리: {', '.join(dates)}")
    elif len(sys.argv) >= 2:
        dates = [sys.argv[1]]
        print(f"📅 날짜: {dates[0]}")
    else:
        print("사용법: python3 scripts/html_to_png.py YYYY-MM-DD | --all")
        sys.exit(1)

    total = 0
    for date_str in dates:
        print(f"\n🗓️  {date_str}")
        count = await process_date(date_str)
        total += count

    print(f"\n✅ 완료: 총 {total}개 PNG 생성")


if __name__ == "__main__":
    asyncio.run(main())
