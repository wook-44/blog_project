"""
브런치/미디엄 포스팅 에이전트 (Agent 07)
==========================================
방식: Selenium Chrome 자동화 (두 플랫폼 모두 공개 쓰기 API 없음)

[브런치]
- 카카오 계정으로 로그인 → 새 글쓰기 → 마크다운 → 발행

[미디엄]
- Medium 계정 로그인 → New Story → 내용 붙여넣기 → Publish
- Medium Integration Token이 있다면 API 방식도 지원

환경변수:
  BRUNCH_EMAIL    : 카카오 이메일
  BRUNCH_PW       : 카카오 비밀번호
  MEDIUM_EMAIL    : 미디엄 이메일
  MEDIUM_PW       : 미디엄 비밀번호
  MEDIUM_TOKEN    : (선택) Medium Integration Token
출력: output/posts/brunch/{video_id}_result.json
      output/posts/medium/{video_id}_result.json
"""

import os
import json
import time
import logging
import re
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Brunch/Medium Poster] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/07_brunch_medium_poster.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
BRUNCH_EMAIL = os.environ.get("BRUNCH_EMAIL", "")
BRUNCH_PW = os.environ.get("BRUNCH_PW", "")
MEDIUM_EMAIL = os.environ.get("MEDIUM_EMAIL", "")
MEDIUM_PW = os.environ.get("MEDIUM_PW", "")
MEDIUM_TOKEN = os.environ.get("MEDIUM_TOKEN", "")


def _init_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def _md_to_plain(md_text: str) -> str:
    """마크다운 → plain text (에디터 입력용)"""
    text = re.sub(r'^#{1,6}\s+', '', md_text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


# ══════════════════════════════════════════════════════
# 브런치 포스터
# ══════════════════════════════════════════════════════
class BrunchPoster:
    OUTPUT_DIR = Path("output/posts/brunch")

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def post(self, meta: dict, content: str) -> dict:
        result = {
            "platform": "brunch",
            "video_id": meta.get("video_id"),
            "posted_at": None,
            "post_url": None,
            "status": "failed",
            "error": None,
        }

        driver = None
        try:
            driver = _init_driver(self.headless)
            wait = WebDriverWait(driver, 20)

            # 브런치 로그인 (카카오 계정)
            driver.get("https://brunch.co.kr")
            time.sleep(2)

            login_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a[href*='login'], .btn_login")
            ))
            login_btn.click()
            time.sleep(2)

            # 카카오 로그인 선택
            try:
                kakao_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a[href*='kakao'], .btn_kakao")
                ))
                kakao_btn.click()
                time.sleep(2)

                email_input = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[name='email'], #loginId")
                ))
                email_input.send_keys(BRUNCH_EMAIL)
                pw_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                pw_input.send_keys(BRUNCH_PW)
                pw_input.send_keys(Keys.RETURN)
                time.sleep(3)
            except Exception as e:
                logger.warning(f"자동 로그인 실패, 수동 로그인 필요: {e}")
                input("브런치 로그인 완료 후 Enter 입력...")

            # 글쓰기 이동
            driver.get("https://brunch.co.kr/write")
            time.sleep(3)

            # 제목 입력
            title_el = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".title-wrap input, [placeholder*='제목']")
            ))
            title_el.click()
            title_el.send_keys(meta.get("title", ""))
            time.sleep(0.5)

            # 본문 입력 (마크다운 → plain text)
            plain_content = _md_to_plain(content)
            body_el = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".ProseMirror, [contenteditable='true'].article-body, .article")
            ))
            body_el.click()
            # 클립보드 방식으로 붙여넣기 (긴 텍스트)
            driver.execute_script(
                "arguments[0].innerText = arguments[1]",
                body_el, plain_content
            )
            time.sleep(1)

            # 발행 버튼
            publish_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.btn_publish, .btn-publish, button[data-type='publish']")
            ))
            publish_btn.click()
            time.sleep(2)

            # 발행 확인
            try:
                confirm = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".btn_confirm, button.confirm")
                ))
                confirm.click()
                time.sleep(3)
            except Exception:
                pass

            post_url = driver.current_url
            result.update({
                "posted_at": datetime.now().isoformat(),
                "post_url": post_url,
                "status": "success",
            })
            logger.info(f"브런치 포스팅 성공: {post_url}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"브런치 포스팅 실패: {e}")
        finally:
            if driver:
                time.sleep(2)
                driver.quit()

        video_id = meta.get("video_id", "unknown")
        out_path = self.OUTPUT_DIR / f"{video_id}_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result


# ══════════════════════════════════════════════════════
# 미디엄 포스터
# ══════════════════════════════════════════════════════
class MediumPoster:
    OUTPUT_DIR = Path("output/posts/medium")

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _post_via_api(self, meta: dict, content: str) -> dict:
        """Medium Integration Token이 있을 때 API 사용"""
        headers = {
            "Authorization": f"Bearer {MEDIUM_TOKEN}",
            "Content-Type": "application/json",
        }
        # 사용자 ID 조회
        me_resp = requests.get("https://api.medium.com/v1/me", headers=headers)
        me_resp.raise_for_status()
        user_id = me_resp.json()["data"]["id"]

        payload = {
            "title": meta.get("title", ""),
            "contentFormat": "markdown",
            "content": f"# {meta.get('title', '')}\n\n{content}",
            "tags": meta.get("tags", [])[:5],
            "publishStatus": "public",
        }
        resp = requests.post(
            f"https://api.medium.com/v1/users/{user_id}/posts",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return {
            "post_url": data.get("url", ""),
            "post_id": data.get("id", ""),
        }

    def _post_via_chrome(self, meta: dict, content: str) -> dict:
        """Chrome 자동화로 미디엄 포스팅"""
        driver = None
        try:
            driver = _init_driver(self.headless)
            wait = WebDriverWait(driver, 20)

            driver.get("https://medium.com/m/signin")
            time.sleep(2)

            # 이메일 로그인
            email_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'email')]")
            ))
            email_btn.click()
            time.sleep(1)

            email_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='email']")
            ))
            email_input.send_keys(MEDIUM_EMAIL)
            email_input.send_keys(Keys.RETURN)
            time.sleep(2)

            pw_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='password']")
            ))
            pw_input.send_keys(MEDIUM_PW)
            pw_input.send_keys(Keys.RETURN)
            time.sleep(4)

            # 새 글쓰기
            driver.get("https://medium.com/new-story")
            time.sleep(3)

            # 제목
            title_el = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "h3[data-placeholder='Title']")
            ))
            title_el.click()
            title_el.send_keys(meta.get("title", ""))
            title_el.send_keys(Keys.RETURN)
            time.sleep(0.5)

            # 본문
            body_el = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "p[data-placeholder='Tell your story...'], .graf--p")
            ))
            body_el.click()
            plain = _md_to_plain(content)
            driver.execute_script("arguments[0].innerText = arguments[1]", body_el, plain)
            time.sleep(1)

            # Publish 버튼
            publish_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Publish')]")
            ))
            publish_btn.click()
            time.sleep(2)

            # Publish Now 확인
            publish_now = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Publish now')]")
            ))
            publish_now.click()
            time.sleep(3)

            post_url = driver.current_url
            return {"post_url": post_url, "post_id": ""}

        finally:
            if driver:
                time.sleep(2)
                driver.quit()

    def post(self, meta: dict, content: str) -> dict:
        result = {
            "platform": "medium",
            "video_id": meta.get("video_id"),
            "posted_at": None,
            "post_url": None,
            "post_id": None,
            "status": "failed",
            "error": None,
        }

        try:
            if MEDIUM_TOKEN:
                logger.info("Medium API 방식으로 포스팅")
                data = self._post_via_api(meta, content)
            else:
                logger.info("Medium Chrome 자동화로 포스팅")
                data = self._post_via_chrome(meta, content)

            result.update({
                "posted_at": datetime.now().isoformat(),
                "post_url": data["post_url"],
                "post_id": data.get("post_id", ""),
                "status": "success",
            })
            logger.info(f"미디엄 포스팅 성공: {data['post_url']}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"미디엄 포스팅 실패: {e}")

        video_id = meta.get("video_id", "unknown")
        out_path = self.OUTPUT_DIR / f"{video_id}_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result


# ── CLI 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    import sys

    platform = sys.argv[1] if len(sys.argv) > 1 else "brunch"
    meta_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not meta_path:
        print("Usage: python 07_brunch_medium_poster.py [brunch|medium] <meta_json_path>")
        sys.exit(1)

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    with open(meta["content_path"], encoding="utf-8") as f:
        content = f.read()

    headless = "--headless" in sys.argv

    if platform == "brunch":
        poster = BrunchPoster(headless=headless)
    else:
        poster = MediumPoster(headless=headless)

    result = poster.post(meta, content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
