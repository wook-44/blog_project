"""
유튜브 플레이리스트 최신 영상 체크 (v2)
-----------------------------------------
변경사항 (버그 수정):
  1. SEEN_FILE → data/seen_videos.json (output/ 은 .gitignore 대상)
  2. RSS playlist_id 방식 제거 (YouTube 미지원) → API 전용
  3. maxResults=1 → 10 (누락 영상 일괄 감지)
  4. 신규 영상을 data/new_videos.csv 에 append
  5. data/seen_videos.txt 도 병행 갱신 (하위 호환)
"""

import os
import sys
import json
import csv
import time
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── 로깅 ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Playlist] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── 설정 ────────────────────────────────────────────────────────────────────
PLAYLIST_ID     = os.getenv("PLAYLIST_ID", "PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ✅ Fix 1: data/ 폴더 (gitignore 대상인 output/ 아님)
DATA_DIR        = Path("data")
SEEN_FILE       = DATA_DIR / "seen_videos.json"      # 주 seen 저장소
SEEN_TXT        = DATA_DIR / "seen_videos.txt"       # 하위 호환
NEW_VIDEOS_CSV  = DATA_DIR / "new_videos.csv"

# ✅ Fix 2: RSS 제거 (playlist_id 기반 RSS는 YouTube 미지원)
# ✅ Fix 3: maxResults=10 으로 늘려 누락 영상 일괄 감지
API_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
    "?part=snippet&maxResults=10&playlistId={playlist_id}&key={api_key}"
)


# ── HTTP ────────────────────────────────────────────────────────────────────
def _fetch_url(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; BlogBot/2.0)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ── YouTube Data API v3 ──────────────────────────────────────────────────────
def fetch_latest_via_api(max_results: int = 10) -> list[dict]:
    """
    YouTube Data API v3로 최신 영상 목록 반환.
    최대 max_results개, 최신 순.
    """
    if not YOUTUBE_API_KEY:
        logger.error("YOUTUBE_API_KEY 미설정 — API 조회 불가")
        return []

    url = API_URL.format(playlist_id=PLAYLIST_ID, api_key=YOUTUBE_API_KEY)
    # maxResults를 URL에 직접 반영
    url = url.replace("maxResults=10", f"maxResults={max_results}")

    try:
        logger.info(f"YouTube Data API 조회: maxResults={max_results}")
        raw  = _fetch_url(url)
        data = json.loads(raw)
        items = data.get("items", [])
        if not items:
            logger.warning("API 결과 없음 (items 빈 배열)")
            return []

        results = []
        for item in items:
            snippet  = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            video_id = resource.get("videoId", "")
            if not video_id:
                continue
            results.append({
                "video_id":    video_id,
                "title":       snippet.get("title", ""),
                "url":         f"https://www.youtube.com/watch?v={video_id}",
                "published":   snippet.get("publishedAt", ""),
                "channel":     snippet.get("videoOwnerChannelTitle", ""),
                "playlist_id": PLAYLIST_ID,
            })

        logger.info(f"API 조회 완료: {len(results)}개 항목")
        return results

    except urllib.error.HTTPError as e:
        logger.error(f"API HTTP 오류 {e.code}: {e.reason}")
        return []
    except Exception as e:
        logger.error(f"API 조회 실패: {e}")
        return []


# ── seen_videos 관리 ─────────────────────────────────────────────────────────
def load_seen_ids() -> set:
    """seen_videos.json + seen_videos.txt 모두 읽어 합산."""
    seen = set()

    # JSON (주 저장소)
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
            seen.update(data.get("seen_ids", []))
        except Exception as e:
            logger.warning(f"seen_videos.json 읽기 실패: {e}")

    # TXT (하위 호환)
    if SEEN_TXT.exists():
        try:
            for line in SEEN_TXT.read_text(encoding="utf-8").splitlines():
                vid = line.strip()
                if vid:
                    seen.add(vid)
        except Exception as e:
            logger.warning(f"seen_videos.txt 읽기 실패: {e}")

    logger.info(f"기존 seen 영상: {len(seen)}개")
    return seen


def save_seen_ids(seen: set):
    """seen_videos.json 과 seen_videos.txt 모두 저장."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    SEEN_FILE.write_text(
        json.dumps({"seen_ids": sorted(seen)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # TXT (하위 호환)
    SEEN_TXT.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")


def append_new_videos_csv(new_videos: list[dict]):
    """신규 영상을 data/new_videos.csv 에 append."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    fieldnames = ["checked_at", "video_id", "title", "url", "channel", "published", "summary"]

    write_header = not NEW_VIDEOS_CSV.exists() or NEW_VIDEOS_CSV.stat().st_size == 0

    with open(NEW_VIDEOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for v in new_videos:
            writer.writerow({
                "checked_at": now,
                "video_id":   v["video_id"],
                "title":      v["title"],
                "url":        v["url"],
                "channel":    v.get("channel", ""),
                "published":  v.get("published", ""),
                "summary":    v.get("summary", ""),
            })
    logger.info(f"new_videos.csv 에 {len(new_videos)}개 추가")


# ── 메인 ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="유튜브 플레이리스트 최신 영상 체크 v2")
    parser.add_argument("--output-json", default="output/latest_video.json",
                        help="최신 신규 영상 JSON 저장 경로 (파이프라인용)")
    parser.add_argument("--max-results", type=int, default=10,
                        help="API 조회 개수 (기본 10)")
    parser.add_argument("--force", action="store_true",
                        help="이미 본 영상이어도 강제 처리")
    args = parser.parse_args()

    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)

    # 1) API로 최신 영상 목록 조회 (최대 10개)
    videos = fetch_latest_via_api(max_results=args.max_results)
    if not videos:
        logger.error("영상 조회 실패. 종료.")
        sys.exit(1)

    # 2) seen 목록 로드
    seen_ids = load_seen_ids()

    # 3) 신규 영상 필터링
    new_videos = [v for v in videos if v["video_id"] not in seen_ids]

    if not new_videos and not args.force:
        logger.info(f"신규 영상 없음 (최근 {len(videos)}개 모두 기처리). 종료.")
        # output json 에 is_new=false 저장
        latest = videos[0]
        latest["is_new"] = False
        latest["checked_at"] = datetime.now(timezone.utc).isoformat()
        latest["new_count"] = 0
        Path(args.output_json).write_text(
            json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        sys.exit(0)

    # 4) 신규 영상 처리
    logger.info(f"🆕 신규 영상 {len(new_videos)}개 감지!")
    for v in new_videos:
        logger.info(f"  [{v['video_id']}] {v['title']}")

    # 5) seen 업데이트 & CSV append
    seen_ids.update(v["video_id"] for v in new_videos)
    save_seen_ids(seen_ids)
    append_new_videos_csv(new_videos)

    # 6) output JSON 저장 (파이프라인은 최신 1개만 사용)
    latest_new = new_videos[0]
    latest_new["is_new"] = True
    latest_new["checked_at"] = datetime.now(timezone.utc).isoformat()
    latest_new["new_count"] = len(new_videos)
    if len(new_videos) > 1:
        latest_new["other_new"] = [v["video_id"] for v in new_videos[1:]]

    Path(args.output_json).write_text(
        json.dumps(latest_new, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"저장: {args.output_json}")
    logger.info(f"✅ 완료. 신규 {len(new_videos)}개 / seen 총 {len(seen_ids)}개")


if __name__ == "__main__":
    main()
