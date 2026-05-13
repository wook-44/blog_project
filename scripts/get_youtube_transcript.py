#!/usr/bin/env python3
"""
get_youtube_transcript.py
--------------------------
Playwright로 YouTube 영상 자막을 추출해 텍스트 파일로 저장.
Chrome for Testing을 직접 제어하므로 컴퓨터-유즈 권한 승인 불필요.

사용법:
  python3 scripts/get_youtube_transcript.py <YouTube_URL> [출력_날짜 YYYY-MM-DD]

예시:
  python3 scripts/get_youtube_transcript.py https://www.youtube.com/watch?v=Ksj5Xcha3E0 2026-04-20

결과:
  /Users/chanwook/Documents/Claude/Projects/블로그/data/transcripts/YYYY-MM-DD_transcript.txt
"""

import asyncio
import sys
import re
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

BASE = Path(__file__).parent.parent
TRANSCRIPT_DIR = BASE / "data" / "transcripts"
USER_DATA_DIR = BASE / ".playwright_profile"


async def extract_transcript(video_url: str, date_str: str) -> str:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            slow_mo=200,
        )
        page = await context.new_page()

        print(f"🎬 영상 이동 중: {video_url}")
        await page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # 로그인 체크 (필요시)
        if "accounts.google.com" in page.url:
            print("⚠️  YouTube 로그인이 필요합니다. 브라우저에서 로그인 후 Enter...")
            input()
            await page.goto(video_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

        # 영상 제목 수집
        title = ""
        try:
            title = await page.title()
            print(f"📌 영상 제목: {title}")
        except Exception:
            pass

        # ── 방법 1: "..." 버튼 → 자막 열기 ─────────────────
        transcript_text = ""
        try:
            print("📜 자막 버튼 탐색 중...")
            # 더보기 버튼 클릭
            more_btn = page.locator(
                'button[aria-label="더보기"], tp-yt-paper-button#expand, '
                'yt-button-shape button[aria-label*="more"], '
                '#description-inline-expander button'
            )
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await page.wait_for_timeout(1000)

            # "..." 또는 "공유" 옆 메뉴 버튼
            menu_btn = page.locator(
                'button[aria-label="...에 대한 추가 작업"], '
                'ytd-menu-renderer yt-icon-button, '
                '#actions button[aria-label*="More actions"]'
            )
            if await menu_btn.count() > 0:
                await menu_btn.first.click()
                await page.wait_for_timeout(800)
                # 자막(스크립트) 열기 클릭
                transcript_btn = page.locator(
                    'ytd-menu-service-item-renderer:has-text("자막"), '
                    'ytd-menu-service-item-renderer:has-text("transcript"), '
                    'yt-formatted-string:has-text("자막")'
                )
                if await transcript_btn.count() > 0:
                    await transcript_btn.first.click()
                    await page.wait_for_timeout(2000)
                    print("✅ 자막 패널 열림")

        except Exception as e:
            print(f"   방법1 실패: {e}")

        # ── 방법 2: 자막 패널 텍스트 수집 ───────────────────
        try:
            transcript_panel = page.locator(
                'ytd-transcript-renderer, '
                'ytd-transcript-segment-list-renderer, '
                '#segments-container'
            )
            await transcript_panel.wait_for(timeout=5000)
            segments = await page.locator(
                'ytd-transcript-segment-renderer yt-formatted-string, '
                '.segment-text'
            ).all_text_contents()
            if segments:
                transcript_text = "\n".join(s.strip() for s in segments if s.strip())
                print(f"✅ 자막 {len(segments)}개 세그먼트 추출 완료")
        except Exception as e:
            print(f"   자막 패널 추출 실패: {e}")

        # ── 방법 3: 페이지 전체 텍스트에서 자막 탐색 ──────────
        if not transcript_text:
            print("   방법3: 페이지 텍스트 전체 탐색...")
            try:
                body_text = await page.inner_text("body")
                # 자막 특징적 패턴 (시간 + 텍스트 반복)
                lines = [l.strip() for l in body_text.split("\n") if l.strip()]
                # 짧고 반복적인 대화 라인 추출
                potential = [l for l in lines if 3 < len(l) < 200]
                if len(potential) > 50:
                    transcript_text = "\n".join(potential[20:])  # 앞부분 UI 스킵
                    print(f"   페이지 텍스트 {len(potential)}줄 추출")
            except Exception as e:
                print(f"   방법3 실패: {e}")

        # ── 방법 4: 설명란 텍스트 수집 ──────────────────────
        description = ""
        try:
            desc_el = page.locator(
                '#description ytd-text-inline-expander, '
                '#description-inline-expander, '
                'ytd-expandable-video-description-body-renderer'
            )
            if await desc_el.count() > 0:
                description = await desc_el.first.inner_text()
                print(f"   설명란 {len(description)}자 수집")
        except Exception:
            pass

        await context.close()

        # ── 결과 저장 ────────────────────────────────────────
        out_path = TRANSCRIPT_DIR / f"{date_str}_transcript.txt"
        content = f"[제목]\n{title}\n\n[URL]\n{video_url}\n\n"
        if transcript_text:
            content += f"[자막]\n{transcript_text}\n"
        if description:
            content += f"\n[영상 설명]\n{description}\n"

        out_path.write_text(content, encoding="utf-8")
        print(f"\n✅ 저장 완료: {out_path}")
        print(f"   크기: {out_path.stat().st_size / 1024:.1f} KB")
        return str(out_path)


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/get_youtube_transcript.py <URL> [YYYY-MM-DD]")
        sys.exit(1)

    url = sys.argv[1]
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    asyncio.run(extract_transcript(url, date_str))


if __name__ == "__main__":
    main()
