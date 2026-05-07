"""
유튜브 플레이리스트 최신 영상 체크
- RSS 피드 조회 (3회 재시도)
- RSS 실패 시 YouTube Data API v3 폴백
- 최신 영상이 새 영상이면 output/latest_video.json 저장
"""

import os
import sys
import json
import time
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── 로깅 ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Playlist] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────────────────────────
PLAYLIST_ID   = os.getenv("PLAYLIST_ID", "PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")          # 없으면 RSS만 사용
SEEN_FILE     = Path("output/seen_videos.json")
RSS_URL       = f"https://www.youtube.com/feeds/videos.xml?playlist_id={PLAYLIST_ID}"
API_URL       = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
    f"?part=snippet&maxResults=1&playlistId={PLAYLIST_ID}&key={{api_key}}"
)
RSS_RETRIES   = 3
RSS_RETRY_DELAY = 5   # 초


# ── RSS 피드 파싱 ─────────────────────────────────────────────────────────────
def _fetch_url(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; BlogBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_latest_via_rss() -> dict | None:
    """RSS 피드로 최신 영상 정보 반환. 실패하면 None."""
    for attempt in range(1, RSS_RETRIES + 1):
        try:
            logger.info(f"RSS 피드 조회 (시도 {attempt}/{RSS_RETRIES}): {PLAYLIST_ID}")
            raw = _fetch_url(RSS_URL)
            return _parse_rss(raw)
        except urllib.error.HTTPError as e:
            logger.warning(f"RSS HTTP {e.code}: {e.reason}")
            if attempt < RSS_RETRIES:
                logger.info(f"{RSS_RETRY_DELAY}초 후 재시도...")
                time.sleep(RSS_RETRY_DELAY)
        except Exception as e:
            logger.warning(f"RSS 조회 오류: {e}")
            if attempt < RSS_RETRIES:
                time.sleep(RSS_RETRY_DELAY)
    logger.error("RSS 조회 모두 실패")
    return None


def _parse_rss(raw: bytes) -> dict:
    """XML 파싱 없이 정규식으로 최신 항목 추출."""
    import re
    text = raw.decode("utf-8", errors="replace")

    # <entry> 블록 첫 번째만
    entry_m = re.search(r"<entry>(.*?)</entry>", text, re.DOTALL)
    if not entry_m:
        raise ValueError("RSS에서 <entry> 없음")
    entry = entry_m.group(1)

    def tag(name):
        m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", entry, re.DOTALL)
        return m.group(1).strip() if m else ""

    video_id_m = re.search(r"<yt:videoId>(.*?)</yt:videoId>", entry)
    video_id   = video_id_m.group(1).strip() if video_id_m else ""

    published  = tag("published")
    title      = tag("title")

    # CDATA 언랩
    title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title)

    return {
        "video_id":   video_id,
        "title":      title,
        "url":        f"https://www.youtube.com/watch?v={video_id}",
        "published":  published,
        "playlist_id": PLAYLIST_ID,
    }


# ── YouTube Data API 폴백 ─────────────────────────────────────────────────────
def fetch_latest_via_api() -> dict | None:
    """YouTube Data API v3로 최신 영상 정보 반환."""
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY 미설정 — API 폴백 불가")
        return None

    url = API_URL.format(api_key=YOUTUBE_API_KEY)
    try:
        logger.info("YouTube Data API v3로 폴백 시도")
        raw  = _fetch_url(url)
        data = json.loads(raw)
        items = data.get("items", [])
        if not items:
            logger.error("API 결과 없음")
            return None
        snippet  = items[0]["snippet"]
        resource = snippet["resourceId"]
        video_id = resource["videoId"]
        return {
            "video_id":    video_id,
            "title":       snippet.get("title", ""),
            "url":         f"https://www.youtube.com/watch?v={video_id}",
            "published":   snippet.get("publishedAt", ""),
            "playlist_id": PLAYLIST_ID,
        }
    except Exception as e:
        logger.error(f"API 조회 실패: {e}")
        return None


# ── 새 영상 여부 판단 ──────────────────────────────────────────────────────────
def is_new_video(video_id: str) -> bool:
    if not SEEN_FILE.exists():
        return True
    try:
        seen = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return video_id not in seen.get("seen_ids", [])
    except Exception:
        return True


def mark_seen(video_id: str):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    seen = {"seen_ids": []}
    if SEEN_FILE.exists():
        try:
            seen = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if video_id not in seen["seen_ids"]:
        seen["seen_ids"].append(video_id)
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="유튜브 플레이리스트 최신 영상 체크")
    parser.add_argument("--output-json", default="output/latest_video.json",
                        help="결과 JSON 저장 경로")
    parser.add_argument("--force", action="store_true",
                        help="이미 본 영상이어도 강제 처리")
    args = parser.parse_args()

    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)

    # 1) RSS 시도
    video_info = fetch_latest_via_rss()

    # 2) RSS 실패 시 API 폴백
    if video_info is None:
        video_info = fetch_latest_via_api()

    # 3) 모두 실패
    if video_info is None:
        logger.error("RSS와 API 모두 실패. 종료.")
        sys.exit(1)

    logger.info(f"최신 영상: [{video_info['video_id']}] {video_info['title']}")

    # 4) 새 영상 판단
    new = is_new_video(video_info["video_id"])
    if not new and not args.force:
        logger.info("이미 처리한 영상. 종료 (is_new=false)")
        video_info["is_new"] = False
    else:
        video_info["is_new"] = True
        mark_seen(video_info["video_id"])
        logger.info("새 영상 감지! (is_new=true)")

    video_info["checked_at"] = datetime.now(timezone.utc).isoformat()

    out_path = Path(args.output_json)
    out_path.write_text(json.dumps(video_info, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"저장: {out_path}")


if __name__ == "__main__":
    main()
