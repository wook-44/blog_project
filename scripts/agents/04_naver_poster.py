"""
네이버 블로그 포스팅 에이전트 (Agent 04)
==========================================
방식: Selenium Chrome 자동화 (네이버 공개 API 없음)
- 네이버 로그인 → 블로그 글쓰기 → 제목/내용/태그 입력 → 발행
환경변수:
  NAVER_ID      : 네이버 아이디
  NAVER_PW      : 네이버 비밀번호
  NAVER_BLOG_ID : 블로그 ID (예: myblog)
출력: output/posts/naver/{video_id}_result.json
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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Naver Poster] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/04_naver_poster.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
NAVER_ID = os.environ.get("NAVER_ID", "")
NAVER_PW = os.environ.get("NAVER_PW", "")
NAVER_BLOG_ID = os.environ.get("NAVER_BLOG_ID", "")
OUTPUT_DIR = Path("output/posts/naver")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
NAVER_WRITE_URL = "https://blog.naver.com/oedit/postWriteForm.naver"


class NaverBlogPoster:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36")
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
        logger.info("Chrome 드라이버 초기화 완료")

    def _slow_type(self, element, text: str, delay: float = 0.05):
        """봇 감지 우회: 한 글자씩 입력"""
        for char in text:
            element.send_keys(char)
            time.sleep(delay)

    # ── 로그인 ─────────────────────────────────────────
    def login(self):
        logger.info("네이버 로그인 시작")
        self.driver.get(NAVER_LOGIN_URL)
        time.sleep(2)

        # ID 입력
        id_input = self.wait.until(EC.presence_of_element_located((By.ID, "id")))
        id_input.clear()
        self._slow_type(id_input, NAVER_ID)
        time.sleep(0.5)

        # PW 입력
        pw_input = self.driver.find_element(By.ID, "pw")
        pw_input.clear()
        self._slow_type(pw_input, NAVER_PW)
        time.sleep(0.5)

        # 로그인 버튼
        login_btn = self.driver.find_element(By.ID, "log.login")
        login_btn.click()
        time.sleep(3)

        # 로그인 성공 확인
        if "nid.naver.com" in self.driver.current_url:
            # 2단계 인증 또는 캡차 처리
            logger.warning("추가 인증이 필요합니다. 수동으로 완료 후 Enter를 누르세요.")
            input("인증 완료 후 Enter...")

        logger.info(f"로그인 완료: {self.driver.current_url}")

    # ── HTML → 네이버 에디터 붙여넣기 ─────────────────
    def _paste_html_content(self, html_content: str):
        """네이버 스마트에디터에 HTML 콘텐츠 입력"""
        # iframe 진입
        try:
            iframe = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe#mainFrame")
            ))
            self.driver.switch_to.frame(iframe)
        except Exception:
            logger.info("mainFrame iframe 없음, 직접 접근 시도")

        # 에디터 본문 영역
        try:
            editor = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".se-content, .se-component-content, [contenteditable='true']")
            ))
            editor.click()
            time.sleep(0.5)

            # JavaScript로 HTML 삽입 (가장 안정적)
            escaped = html_content.replace("`", "\\`").replace("\\", "\\\\")
            self.driver.execute_script(
                "document.execCommand('insertHTML', false, arguments[0]);",
                html_content
            )
            logger.info("HTML 콘텐츠 삽입 완료")
        except Exception as e:
            logger.warning(f"HTML 삽입 실패, 텍스트 입력으로 fallback: {e}")
            # plain text fallback
            plain = re.sub(r'<[^>]+>', '', html_content)
            editor = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[contenteditable='true']")
            ))
            editor.send_keys(plain)

    # ── 포스팅 ─────────────────────────────────────────
    def post(self, meta: dict, content: str) -> dict:
        """
        meta: {title, tags, category, meta_description, ...}
        content: HTML 문자열
        """
        result = {
            "platform": "naver",
            "video_id": meta.get("video_id"),
            "posted_at": None,
            "post_url": None,
            "status": "failed",
            "error": None,
        }

        try:
            self._init_driver()
            self.login()

            # 글쓰기 페이지 이동
            write_url = f"https://blog.naver.com/{NAVER_BLOG_ID}/postwrite"
            self.driver.get(write_url)
            time.sleep(3)

            # iframe 전환
            try:
                main_frame = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe#mainFrame")
                ))
                self.driver.switch_to.frame(main_frame)
                time.sleep(2)
            except Exception:
                pass

            # 제목 입력
            title_input = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".se-title-text, input[placeholder*='제목']")
            ))
            title_input.click()
            title_input.send_keys(meta.get("title", ""))
            time.sleep(0.5)

            # 본문 입력
            self._paste_html_content(content)
            time.sleep(1)

            # 태그 입력
            try:
                tag_btn = self.driver.find_element(
                    By.CSS_SELECTOR, ".se-tag-field, button[data-testid='tag']"
                )
                tag_btn.click()
                time.sleep(0.5)
                tag_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[placeholder*='태그']"
                )
                for tag in meta.get("tags", [])[:10]:
                    tag_input.send_keys(tag)
                    tag_input.send_keys(Keys.RETURN)
                    time.sleep(0.3)
            except Exception as e:
                logger.warning(f"태그 입력 실패: {e}")

            # 발행 버튼
            publish_btn = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.publish-btn, button[data-action='publish']")
            ))
            publish_btn.click()
            time.sleep(2)

            # 발행 확인 팝업
            try:
                confirm_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.confirm, .btn-confirm")
                ))
                confirm_btn.click()
                time.sleep(3)
            except Exception:
                pass

            post_url = self.driver.current_url
            result.update({
                "posted_at": datetime.now().isoformat(),
                "post_url": post_url,
                "status": "success",
            })
            logger.info(f"네이버 포스팅 성공: {post_url}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"네이버 포스팅 실패: {e}")
        finally:
            if self.driver:
                time.sleep(2)
                self.driver.quit()

        # 결과 저장
        video_id = meta.get("video_id", "unknown")
        out_path = OUTPUT_DIR / f"{video_id}_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result


# ── CLI 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python 04_naver_poster.py <meta_json_path>")
        sys.exit(1)

    meta_path = Path(sys.argv[1])
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    content_path = Path(meta["content_path"])
    with open(content_path, encoding="utf-8") as f:
        content = f.read()

    poster = NaverBlogPoster(headless="--headless" in sys.argv)
    result = poster.post(meta, content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
