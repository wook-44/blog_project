"""
YouTube 플레이리스트 신규 영상 체크 + Gemini 분석 스크립트.

- YouTube의 공개 RSS 피드를 사용해 새 영상을 감지한다 (API 키 불필요).
- 처음 보는 영상은 Gemini API로 한 줄 요약을 만들어 CSV에 추가한다.
- 이미 본 영상 ID는 data/seen_videos.txt 에 누적 저장한다.

환경변수:
  GEMINI_API_KEY  (필수) Google AI Studio 발급 키
  PLAYLIST_ID     (선택) 기본값 = '12시에 만나요' 플레이리스트
"""

from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

DEFAULT_PLAYLIST_ID = "PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX"
PLAYLIST_ID = os.environ.get("PLAYLIST_ID", DEFAULT_PLAYLIST_ID)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SEEN_FILE = DATA_DIR / "seen_videos.txt"
CSV_FILE = DATA_DIR / "new_videos.csv"

RSS_URL = f"https://www.youtube.com/feeds/videos.xml?playlist_id={PLAYLIST_ID}"

# Atom 네임스페이스
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[info] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[error] {msg}", file=sys.stderr, flush=True)


def http_get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "blog_project-rss-checker/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    import json
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# RSS 파싱
# ---------------------------------------------------------------------------

def fetch_playlist_entries(playlist_id: str) -> list[dict]:
    """RSS에서 최신 영상 목록을 끌어온다 (보통 최신 15개)."""
    log(f"RSS 피드 조회: {playlist_id}")
    try:
        raw = http_get(RSS_URL)
    except urllib.error.HTTPError as e:
        err(f"RSS HTTP {e.code}: {e.reason}")
        raise
    except urllib.error.URLError as e:
        err(f"RSS 연결 실패: {e.reason}")
        raise

    root = ET.fromstring(raw)
    entries = []
    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)
        author_el = entry.find("atom:author/atom:name", NS)
        desc_el = entry.find("media:group/media:description", NS)

        if video_id_el is None or title_el is None:
            continue

        entries.append({
            "video_id": (video_id_el.text or "").strip(),
            "title": (title_el.text or "").strip(),
            "published": (published_el.text or "").strip() if published_el is not None else "",
            "url": link_el.attrib.get("href", "") if link_el is not None else "",
            "channel": (author_el.text or "").strip() if author_el is not None else "",
            "description": (desc_el.text or "").strip() if desc_el is not None else "",
        })

    log(f"RSS 영상 {len(entries)}개 수신")
    return entries


# ---------------------------------------------------------------------------
# 본 영상 ID 관리
# ---------------------------------------------------------------------------

def load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    with SEEN_FILE.open("r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_seen(video_ids: Iterable[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SEEN_FILE.open("a", encoding="utf-8") as f:
        for vid in video_ids:
            f.write(vid + "\n")


# ---------------------------------------------------------------------------
# Gemini 분석
# ---------------------------------------------------------------------------

def analyze_with_gemini(entry: dict, api_key: str) -> str:
    """제목+설명을 기반으로 한 줄 요약 생성. 실패 시 빈 문자열."""
    title = entry["title"]
    desc = entry["description"][:1500]

    prompt = (
        "다음은 한국 주식·투자 유튜브 영상의 제목과 설명입니다. "
        "핵심 주제를 한국어 한 문장(최대 80자)으로 요약하세요. "
        "광고/정형 문구는 제외하고 영상의 실제 내용에 집중합니다.\n\n"
        f"[제목] {title}\n[설명] {desc}\n\n요약:"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200},
    }

    url = f"{GEMINI_ENDPOINT}?key={api_key}"
    try:
        data = http_post_json(url, payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        err(f"Gemini HTTP {e.code}: {body[:300]}")
        return ""
    except Exception as e:  # noqa: BLE001
        err(f"Gemini 호출 실패: {e}")
        return ""

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        err(f"Gemini 응답 구조 이상: {str(data)[:300]}")
        return ""


# ---------------------------------------------------------------------------
# CSV 기록
# ---------------------------------------------------------------------------

CSV_HEADER = ["checked_at", "video_id", "title", "url", "channel", "published", "summary"]


def append_csv(rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0
    with CSV_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_HEADER})


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        err("환경변수 GEMINI_API_KEY 가 비어있습니다.")
        return 1

    try:
        entries = fetch_playlist_entries(PLAYLIST_ID)
    except Exception as e:  # noqa: BLE001
        err(f"RSS 조회 실패로 종료: {e}")
        return 1

    if not entries:
        log("RSS에 영상이 없습니다. 종료.")
        return 0

    seen = load_seen()
    new_entries = [e for e in entries if e["video_id"] not in seen]
    log(f"신규 영상 {len(new_entries)}개")

    if not new_entries:
        return 0

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []
    for entry in new_entries:
        log(f"분석 중: {entry['title']}")
        summary = analyze_with_gemini(entry, api_key)
        rows.append({
            "checked_at": checked_at,
            "video_id": entry["video_id"],
            "title": entry["title"],
            "url": entry["url"],
            "channel": entry["channel"],
            "published": entry["published"],
            "summary": summary,
        })
        time.sleep(0.5)  # 가벼운 레이트리밋

    append_csv(rows)
    append_seen([e["video_id"] for e in new_entries])
    log(f"CSV 기록 완료: {CSV_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
