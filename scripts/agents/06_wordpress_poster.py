"""
워드프레스 포스팅 에이전트 (Agent 06)
=======================================
방식: WordPress REST API v2 (Application Password 인증)
환경변수:
  WP_URL       : WordPress 사이트 URL (예: https://myblog.com)
  WP_USERNAME  : WordPress 사용자명
  WP_APP_PASS  : Application Password (WordPress 관리자 → 사용자 → 앱 비밀번호)
출력: output/posts/wordpress/{video_id}_result.json

※ Application Password 발급:
  WordPress 관리자 → 사용자 → 프로필 → 애플리케이션 비밀번호
"""

import os
import json
import logging
import base64
from datetime import datetime
from pathlib import Path

import requests

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WordPress Poster] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/06_wordpress_poster.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
WP_URL = os.environ.get("WP_URL", "").rstrip("/")
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")
OUTPUT_DIR = Path("output/posts/wordpress")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class WordPressPoster:
    def __init__(self):
        credentials = f"{WP_USERNAME}:{WP_APP_PASS}"
        token = base64.b64encode(credentials.encode()).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
        self.api_base = f"{WP_URL}/wp-json/wp/v2"
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # ── 카테고리 ID 조회/생성 ─────────────────────────
    def get_or_create_category(self, name: str) -> int:
        resp = self.session.get(f"{self.api_base}/categories", params={"search": name})
        categories = resp.json()
        for cat in categories:
            if cat.get("name") == name:
                return cat["id"]
        # 없으면 생성
        resp = self.session.post(
            f"{self.api_base}/categories",
            json={"name": name}
        )
        return resp.json().get("id", 0)

    # ── 태그 ID 조회/생성 ─────────────────────────────
    def get_or_create_tags(self, tag_names: list) -> list:
        tag_ids = []
        for name in tag_names[:10]:
            resp = self.session.get(f"{self.api_base}/tags", params={"search": name})
            tags = resp.json()
            found = next((t for t in tags if t["name"] == name), None)
            if found:
                tag_ids.append(found["id"])
            else:
                resp = self.session.post(f"{self.api_base}/tags", json={"name": name})
                tag_ids.append(resp.json().get("id", 0))
        return [tid for tid in tag_ids if tid]

    # ── Yoast SEO 메타 설정 ───────────────────────────
    def _yoast_meta(self, meta: dict) -> dict:
        """Yoast SEO 플러그인 메타 데이터"""
        return {
            "yoast_head_json": {
                "_yoast_wpseo_focuskw": meta.get("focus_keyword", ""),
                "_yoast_wpseo_metadesc": meta.get("meta_description", ""),
                "_yoast_wpseo_title": meta.get("title", ""),
            }
        }

    # ── 포스트 발행 ────────────────────────────────────
    def post(self, meta: dict, content: str) -> dict:
        result = {
            "platform": "wordpress",
            "video_id": meta.get("video_id"),
            "posted_at": None,
            "post_url": None,
            "post_id": None,
            "status": "failed",
            "error": None,
        }

        try:
            logger.info(f"WordPress 포스팅: {meta.get('title')}")

            category_id = self.get_or_create_category(meta.get("category", "주식"))
            tag_ids = self.get_or_create_tags(meta.get("tags", []))

            payload = {
                "title": meta.get("title", ""),
                "content": content,
                "status": "publish",
                "slug": meta.get("slug", ""),
                "excerpt": meta.get("meta_description", ""),
                "categories": [category_id],
                "tags": tag_ids,
                "meta": {
                    "_yoast_wpseo_focuskw": meta.get("focus_keyword", ""),
                    "_yoast_wpseo_metadesc": meta.get("meta_description", ""),
                },
            }

            resp = self.session.post(f"{self.api_base}/posts", json=payload)
            resp.raise_for_status()
            data = resp.json()

            result.update({
                "posted_at": datetime.now().isoformat(),
                "post_url": data.get("link", ""),
                "post_id": data.get("id", ""),
                "status": "success",
            })
            logger.info(f"WordPress 포스팅 성공: {data.get('link')}")

        except requests.HTTPError as e:
            result["error"] = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"WordPress API 오류: {result['error']}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"WordPress 포스팅 실패: {e}")

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
        print("Usage: python 06_wordpress_poster.py <meta_json_path>")
        sys.exit(1)

    meta_path = Path(sys.argv[1])
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    content_path = Path(meta["content_path"])
    with open(content_path, encoding="utf-8") as f:
        content = f.read()

    poster = WordPressPoster()
    result = poster.post(meta, content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
