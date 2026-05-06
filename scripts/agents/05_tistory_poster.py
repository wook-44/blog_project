"""
티스토리 포스팅 에이전트 (Agent 05)
=====================================
방식: Tistory Open API (OAuth 2.0) — 공식 REST API
환경변수:
  TISTORY_APP_ID      : Tistory 앱 ID
  TISTORY_SECRET_KEY  : Tistory 앱 Secret Key
  TISTORY_ACCESS_TOKEN: OAuth 액세스 토큰
  TISTORY_BLOG_NAME   : 블로그명 (예: myblog)
출력: output/posts/tistory/{video_id}_result.json

※ 토큰 발급:
  https://www.tistory.com/oauth/authorize?client_id={APP_ID}&redirect_uri={REDIRECT}&response_type=code
  → code를 받아 아래 get_access_token()으로 토큰 교환
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Tistory Poster] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/05_tistory_poster.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
TISTORY_APP_ID = os.environ.get("TISTORY_APP_ID", "")
TISTORY_SECRET_KEY = os.environ.get("TISTORY_SECRET_KEY", "")
TISTORY_ACCESS_TOKEN = os.environ.get("TISTORY_ACCESS_TOKEN", "")
TISTORY_BLOG_NAME = os.environ.get("TISTORY_BLOG_NAME", "")
OUTPUT_DIR = Path("output/posts/tistory")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "https://www.tistory.com/apis"


class TistoryPoster:
    def __init__(self):
        self.token = TISTORY_ACCESS_TOKEN
        self.blog_name = TISTORY_BLOG_NAME
        self.session = requests.Session()

    # ── 인증 ───────────────────────────────────────────
    @staticmethod
    def get_auth_url(app_id: str, redirect_uri: str) -> str:
        """OAuth 인증 URL 생성 (최초 1회 수동 실행)"""
        params = urlencode({
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        })
        return f"https://www.tistory.com/oauth/authorize?{params}"

    @staticmethod
    def get_access_token(app_id: str, secret: str, code: str, redirect_uri: str) -> str:
        """Authorization code → Access Token 교환"""
        url = "https://www.tistory.com/oauth/access_token"
        params = {
            "client_id": app_id,
            "client_secret": secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        }
        resp = requests.get(url, params=params)
        # 응답: access_token=XXX&...
        token = dict(p.split("=") for p in resp.text.split("&")).get("access_token", "")
        logger.info(f"액세스 토큰 발급: {token[:10]}...")
        return token

    # ── 카테고리 조회 ──────────────────────────────────
    def get_category_id(self, category_name: str) -> str:
        """카테고리 이름으로 ID 반환"""
        url = f"{API_BASE}/category/list"
        params = {
            "access_token": self.token,
            "output": "json",
            "blogName": self.blog_name,
        }
        resp = self.session.get(url, params=params)
        data = resp.json()
        categories = data.get("tistory", {}).get("item", {}).get("categories", [])
        for cat in categories:
            if cat.get("label") == category_name:
                return cat.get("id", "0")
        return "0"  # 미분류

    # ── 포스트 발행 ────────────────────────────────────
    def post(self, meta: dict, content: str) -> dict:
        result = {
            "platform": "tistory",
            "video_id": meta.get("video_id"),
            "posted_at": None,
            "post_url": None,
            "post_id": None,
            "status": "failed",
            "error": None,
        }

        try:
            logger.info(f"티스토리 포스팅: {meta.get('title')}")

            # 카테고리 ID 조회
            category_id = self.get_category_id(meta.get("category", "주식"))

            # 포스트 작성 API
            url = f"{API_BASE}/post/write"
            payload = {
                "access_token": self.token,
                "output": "json",
                "blogName": self.blog_name,
                "title": meta.get("title", ""),
                "content": content,
                "visibility": "3",      # 0:비공개, 1:보호, 3:공개
                "category": category_id,
                "tag": ",".join(meta.get("tags", [])[:10]),
                "acceptComment": "1",
                "published": "",        # 빈 값 = 즉시 발행
            }

            resp = self.session.post(url, data=payload)
            resp.raise_for_status()
            data = resp.json()

            tistory_data = data.get("tistory", {})
            post_id = tistory_data.get("postId", "")
            post_url = tistory_data.get("url", "")

            if tistory_data.get("status") == "200":
                result.update({
                    "posted_at": datetime.now().isoformat(),
                    "post_url": post_url,
                    "post_id": post_id,
                    "status": "success",
                })
                logger.info(f"티스토리 포스팅 성공: {post_url}")
            else:
                result["error"] = str(data)
                logger.error(f"티스토리 API 오류: {data}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"티스토리 포스팅 실패: {e}")

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
        print("Usage: python 05_tistory_poster.py <meta_json_path>")
        print("\n[토큰 발급]")
        print(f"1. 인증 URL: {TistoryPoster.get_auth_url(TISTORY_APP_ID, 'https://your-redirect.com')}")
        print("2. 코드 받아서 TISTORY_ACCESS_TOKEN 환경변수 설정")
        sys.exit(1)

    meta_path = Path(sys.argv[1])
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    content_path = Path(meta["content_path"])
    with open(content_path, encoding="utf-8") as f:
        content = f.read()

    poster = TistoryPoster()
    result = poster.post(meta, content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
