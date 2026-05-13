#!/usr/bin/env python3
"""
티스토리 자동 포스팅 (Playwright)
- 제목 / 본문 / 이미지 / 태그 자동 입력 후 발행
- 첫 실행 시 브라우저 창에서 티스토리 로그인 필요 (1회)
- 이후 실행부터는 저장된 세션으로 자동 처리
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

# ─── 설정 ────────────────────────────────────────────────
BLOG_ID         = "pick-num"
BLOG_MANAGE_URL = f"https://{BLOG_ID}.tistory.com/manage/newpost"
USER_DATA_DIR   = Path(__file__).parent / ".playwright_profile"

# ─── 포스팅 내용 ──────────────────────────────────────────
def get_post_data():
    today = datetime.now().strftime("%Y-%m-%d")
    base  = Path(__file__).parent

    return {
        "title": f"[테스트] Playwright 자동 포스팅 — {today}",
        "body": (
            "Playwright를 이용한 티스토리 자동 포스팅 테스트입니다.\n\n"
            "이 글은 Claude가 Python Playwright로 자동 작성했습니다.\n"
            "이미지 업로드 및 태그 자동 입력 기능도 포함되어 있습니다."
        ),
        "images": [
            str(base / "images" / "2026-04-27" / "img1_market_status.png"),
            str(base / "images" / "2026-04-27" / "img2_market_structure.png"),
        ],
        "tags": "코스피 주식투자 증시분석 자동포스팅 테스트",
    }

# ─── 로그인 감지 헬퍼 ─────────────────────────────────────
def is_logged_in(url: str) -> bool:
    """manage 페이지에 있으면 로그인된 것으로 판단"""
    return f"{BLOG_ID}.tistory.com/manage" in url

# ─── 메인 ────────────────────────────────────────────────
async def post_to_tistory(post: dict):
    async with async_playwright() as p:

        USER_DATA_DIR.mkdir(exist_ok=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            slow_mo=100,
        )
        page = await context.new_page()

        # ── 1. 글쓰기 페이지 이동 ────────────────────────
        print("📄 글쓰기 페이지로 이동 중...")
        await page.goto(BLOG_MANAGE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── 2. 로그인 체크 및 대기 ───────────────────────
        current_url = page.url
        print(f"   현재 URL: {current_url}")

        if not is_logged_in(current_url):
            print("\n⚠️  로그인이 필요합니다.")
            print("   열린 브라우저 창에서 티스토리(카카오 계정)로 로그인하세요.")
            print("   로그인 완료되면 자동으로 진행됩니다 (최대 5분 대기)...")
            try:
                # 관리 페이지 URL이 될 때까지 대기
                await page.wait_for_url(
                    f"**/{BLOG_ID}.tistory.com/manage**",
                    timeout=300000  # 5분
                )
            except Exception:
                # wait_for_url 패턴 실패 시 페이지 변화 감지
                await page.wait_for_function(
                    f"() => window.location.href.includes('{BLOG_ID}.tistory.com/manage')",
                    timeout=300000
                )
            print("   ✅ 로그인 완료!")
            # manage/newpost로 이동
            await page.goto(BLOG_MANAGE_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

        # ── 3. 에디터 로드 대기 ──────────────────────────
        print("⏳ 에디터 로딩 대기 (최대 60초)...")

        # Tistory 에디터 로드 확인 — 다양한 셀렉터 시도
        editor_loaded = False
        for selector in [
            '.tt_editor',
            'iframe[id*="tistory"]',
            'iframe[name*="editor"]',
            '.CodeMirror',
            '[contenteditable="true"]',
            'input[type="file"]',
        ]:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                print(f"   에디터 감지: {selector}")
                editor_loaded = True
                break
            except Exception:
                continue

        if not editor_loaded:
            print("   ⚠️  에디터 자동 감지 실패, 15초 추가 대기...")
            await page.wait_for_timeout(15000)

        await page.wait_for_timeout(2000)

        # 현재 페이지 구조 파악
        page_url = page.url
        print(f"   에디터 URL: {page_url}")

        # ── 4. 제목 입력 ─────────────────────────────────
        print(f"✏️  제목 입력...")
        title_selectors = [
            'h2[contenteditable]',
            '[placeholder="제목을 입력하세요"]',
            '.title-input',
            'input[name="title"]',
            '#title',
        ]
        title_typed = False
        for sel in title_selectors:
            try:
                el = page.locator(sel).first
                await el.wait_for(timeout=3000)
                await el.click()
                await el.fill(post["title"])
                title_typed = True
                print(f"   제목 입력 완료 ({sel})")
                break
            except Exception:
                continue

        if not title_typed:
            print("   ⚠️  제목 셀렉터를 찾지 못했습니다.")

        await page.wait_for_timeout(500)

        # ── 5. 본문 입력 ─────────────────────────────────
        print("📝 본문 입력...")
        body_typed = False

        # TinyMCE iframe 내부 시도
        for frame_name_part in ["tistory_ifr", "editor"]:
            iframe = None
            for f in page.frames:
                if frame_name_part in f.name.lower():
                    iframe = f
                    break
            if iframe:
                try:
                    body_el = iframe.locator("body")
                    await body_el.wait_for(timeout=5000)
                    await body_el.click()
                    await body_el.type(post["body"], delay=30)
                    body_typed = True
                    print(f"   본문 입력 완료 (iframe: {iframe.name})")
                    break
                except Exception as e:
                    print(f"   iframe {iframe.name} 실패: {e}")

        if not body_typed:
            # fallback: contenteditable 영역
            for sel in ['.ProseMirror', '[role="textbox"]', '.ke-content', 'div[contenteditable="true"]']:
                try:
                    el = page.locator(sel).first
                    await el.wait_for(timeout=3000)
                    await el.click()
                    await page.keyboard.type(post["body"], delay=30)
                    body_typed = True
                    print(f"   본문 입력 완료 ({sel})")
                    break
                except Exception:
                    continue

        if not body_typed:
            print("   ⚠️  본문 영역을 찾지 못했습니다.")

        await page.wait_for_timeout(500)

        # ── 6. 이미지 업로드 ─────────────────────────────
        for i, img_path in enumerate(post.get("images", []), 1):
            if not Path(img_path).exists():
                print(f"⚠️  이미지 없음: {img_path}")
                continue

            print(f"🖼️  이미지 {i} 업로드: {Path(img_path).name}")
            try:
                # 이미지 버튼 클릭
                img_btn_selectors = [
                    'button.image-btn',
                    '[title="이미지"]',
                    '[aria-label*="이미지"]',
                    'button[data-type="image"]',
                ]
                btn_clicked = False
                for btn_sel in img_btn_selectors:
                    try:
                        await page.click(btn_sel, timeout=3000)
                        btn_clicked = True
                        break
                    except Exception:
                        continue

                if btn_clicked:
                    await page.wait_for_timeout(300)
                    # 드롭다운 메뉴 "사진" 클릭
                    try:
                        await page.click('text=사진', timeout=3000)
                        await page.wait_for_timeout(200)
                    except Exception:
                        pass

                # set_input_files로 파일 업로드
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(img_path)
                await page.wait_for_timeout(4000)
                print(f"   ✅ 이미지 {i} 업로드 완료")
            except Exception as e:
                print(f"   ⚠️  이미지 {i} 업로드 실패: {e}")

        # ── 7. 태그 입력 ─────────────────────────────────
        if post.get("tags"):
            print("🏷️  태그 입력...")
            tag_selectors = [
                'input[placeholder*="태그"]',
                'input[name="tag"]',
                '.tag-input input',
            ]
            for sel in tag_selectors:
                try:
                    tag_el = page.locator(sel).first
                    await tag_el.wait_for(timeout=3000)
                    await tag_el.click()
                    await tag_el.type(post["tags"], delay=50)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(500)
                    print("   태그 입력 완료")
                    break
                except Exception:
                    continue

        # ── 8. 발행 ──────────────────────────────────────
        print("🚀 발행 중...")
        complete_selectors = [
            'button:has-text("완료")',
            '.btn-complete',
            'button.publish',
            'button[type="submit"]',
        ]
        for sel in complete_selectors:
            try:
                await page.click(sel, timeout=5000)
                print(f"   완료 버튼 클릭 ({sel})")
                break
            except Exception:
                continue

        await page.wait_for_timeout(2000)

        # 발행 확인 팝업 처리
        publish_selectors = [
            'button:has-text("발행")',
            'button:has-text("공개")',
            '.btn-publish',
        ]
        for sel in publish_selectors:
            try:
                btn = page.locator(sel)
                if await btn.count() > 0:
                    await btn.first.click()
                    print(f"   발행 확인 클릭 ({sel})")
                    break
            except Exception:
                continue

        await page.wait_for_timeout(3000)
        print(f"\n✅ 포스팅 완료!")
        print(f"   블로그: https://{BLOG_ID}.tistory.com")

        await page.wait_for_timeout(3000)
        await context.close()


if __name__ == "__main__":
    post = get_post_data()
    asyncio.run(post_to_tistory(post))
