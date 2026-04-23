#!/usr/bin/env python3
"""
YouTube 플레이리스트 신규 영상 체크 + Gemini 분석.

매일 실행되어:
  1) YouTube Data API v3로 플레이리스트의 현재 영상 목록을 조회합니다.
  2) data/seen_videos.txt 에 기록된 이전 상태와 비교해 신규 영상을 찾습니다.
  3) 신규 영상마다 Gemini API 로 영상 분석을 요청합니다.
  4) 결과를 data/new_videos.csv 에 append 하고 seen_videos.txt 를 갱신합니다.

최초 실행(seen_videos.txt 비어있음)에는 현재 목록을 "이미 본 상태"로
스냅샷만 저장하고 Gemini 호출/CSV 기록은 건너뜁니다.
(과도한 API 사용 방지)

필요한 환경변수:
  GEMINI_API_KEY    : Gemini 분석용 (동시에 YouTube Data API v3 키로도 사용)
  YOUTUBE_API_KEY   : (선택) 별도의 YouTube API 키를 쓸 경우. 없으면 GEMINI_API_KEY 사용.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
PLAYLIST_ID = "PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SEEN_FILE = DATA_DIR / "seen_videos.txt"
CSV_FILE = DATA_DIR / "new_videos.csv"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip() or GEMINI_API_KEY

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

YT_API_BASE = "https://www.googleapis.com/youtube/v3/playlistItems"

ANALYSIS_PROMPT = """당신은 게임/앱 제품 기획자를 돕는 분석가입니다. 아래 YouTube 영상을 시청하고 한국어로 다음 구조로 정리해 주세요.

1) 핵심 요약 (3~5문장)
2) 핵심 포인트 (불릿 5개 이내)
3) 제품 기획 관점 인사이트 (2~3개, 어떻게 기획에 적용할 수 있는지)

출력은 간결·명확하게, 총 500자 이내로."""

CSV_FIELDS = [
    "checked_at",
    "published",
    "title",
    "url",
    "channel",
    "video_id",
    "gemini_analysis",
]


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    return {
        line.strip()
        for line in SEEN_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def save_seen(seen: set[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")


def fetch_playlist() -> list[dict]:
    """YouTube Data API v3의 playlistItems.list로 전체 페이지를 순회하여 수집."""
    if not YT_API_KEY:
        raise RuntimeError(
            "YouTube API 키가 설정되지 않았습니다. GEMINI_API_KEY(또는 YOUTUBE_API_KEY) 환경변수를 확인하세요."
        )

    entries: list[dict] = []
    page_token: str | None = None

    while True:
        params: dict[str, str | int] = {
            "part": "snippet,contentDetails",
            "playlistId": PLAYLIST_ID,
            "maxResults": 50,
            "key": YT_API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        url = f"{YT_API_BASE}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "blog-project-check/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"YouTube API HTTP {e.code}: {body[:500]}\n"
                "→ Google Cloud Console에서 'YouTube Data API v3' 가 활성화되어 있는지 확인하세요."
            ) from None

        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            video_id = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")
            if not video_id:
                continue
            entries.append(
                {
                    "video_id": video_id,
                    "title": (snippet.get("title") or "").strip(),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "published": (content.get("videoPublishedAt") or snippet.get("publishedAt") or "").strip(),
                    "channel": (snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle") or "").strip(),
                }
            )

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return entries


def analyze_with_gemini(video_url: str) -> str:
    if not GEMINI_API_KEY:
        return "(GEMINI_API_KEY 미설정 — 분석 건너뜀)"

    body = {
        "contents": [
            {
                "parts": [
                    {"text": ANALYSIS_PROMPT},
                    {"fileData": {"fileUri": video_url}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
    }
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read())
    except Exception as e:  # noqa: BLE001
        return f"(Gemini 분석 실패: {e})"

    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        return f"(Gemini 응답 파싱 실패: {json.dumps(payload)[:500]})"


def append_csv(rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0
    with CSV_FILE.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"[info] YouTube API로 플레이리스트 조회: {PLAYLIST_ID}")
    videos = fetch_playlist()
    print(f"[info] 수집된 영상 수: {len(videos)}")

    if not videos:
        print("[warn] 영상이 조회되지 않았습니다. 플레이리스트 ID 또는 API 키 권한을 확인하세요.")
        return 0

    seen = load_seen()

    if not seen:
        seen.update(v["video_id"] for v in videos)
        save_seen(seen)
        print(f"[info] 최초 실행: 현재 {len(seen)}개 영상을 초기 스냅샷으로 저장했습니다.")
        print("[info] 다음 실행부터 신규 영상 감지 + Gemini 분석을 수행합니다.")
        return 0

    new_videos = [v for v in videos if v["video_id"] not in seen]
    print(f"[info] 신규 영상: {len(new_videos)}개")

    if not new_videos:
        print("[info] 새로 올라온 영상이 없습니다.")
        return 0

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    for v in new_videos:
        print(f"[info] 분석: {v['title']}")
        analysis = analyze_with_gemini(v["url"])
        rows.append(
            {
                "checked_at": now_iso,
                "published": v["published"],
                "title": v["title"],
                "url": v["url"],
                "channel": v["channel"],
                "video_id": v["video_id"],
                "gemini_analysis": analysis,
            }
        )
        time.sleep(1)

    append_csv(rows)
    seen.update(v["video_id"] for v in new_videos)
    save_seen(seen)
    print(f"[info] {len(rows)}개 행을 {CSV_FILE.name}에 기록했습니다.")
    print(f"[info] seen_videos.txt 누적: {len(seen)}개")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)
