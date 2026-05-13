"""
시리즈 내부 링크 에이전트 (Agent 09)
=====================================
역할: 새 포스트가 다루는 키워드가 최근 14일 내 다른 포스트에도 등장하면
      본문에 "📎 이전 분석" 링크를 자동 삽입 제안.
입력: 발행 직전 .md 경로
출력:
  - dry-run: 삽입할 위치와 링크 후보를 콘솔에 출력
  - --apply: 본문을 직접 수정 (백업 .bak 생성)
"""
import argparse
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

BLOG_DIR = Path(__file__).resolve().parents[2]

SERIES_KEYWORDS = [
    "코스피", "코스닥", "삼성전자", "SK하이닉스", "현대차", "기아",
    "엔비디아", "테슬라", "구글", "메타", "애플",
    "반도체", "이차전지", "방산", "AI", "로봇",
    "금리", "환율", "유가", "호르무즈", "이란", "트럼프", "FOMC",
    "외국인", "수급",
]

# 블로그 발행 URL 패턴 — 사용자가 네이버에 발행 시 슬러그/포스트번호 매핑은
# blog_index.json(있다면)에서 가져오고, 없으면 임시로 파일명을 사용.
INDEX_PATH = BLOG_DIR / "blog_index.json"


def load_index() -> dict:
    """파일명 → 발행 URL 매핑. 없으면 로컬 파일 경로 사용."""
    if INDEX_PATH.exists():
        import json
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {}


def find_recent_posts(target_date: datetime, days: int = 14):
    """target_date 이전 days일 내의 .md 포스트 (자기 자신 제외)."""
    posts = []
    for p in BLOG_DIR.glob("20*-*.md"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.stem)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if d >= target_date or (target_date - d).days > days:
            continue
        posts.append((d, p))
    return sorted(posts, key=lambda x: x[0], reverse=True)


def extract_keywords_in_body(text: str) -> list:
    """본문 첫 2000자 내에서 등장한 시리즈 키워드 추출."""
    head = text[:2000]
    return [kw for kw in SERIES_KEYWORDS if kw in head]


def title_of(post_path: Path) -> str:
    text = post_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else post_path.stem


def suggest_links(post_path: Path, index: dict) -> list:
    """현재 포스트에 추가할 링크 후보 목록 반환."""
    text = post_path.read_text(encoding="utf-8")
    date_m = re.match(r"(\d{4}-\d{2}-\d{2})", post_path.stem)
    if not date_m:
        return []
    target_date = datetime.strptime(date_m.group(1), "%Y-%m-%d")
    current_kws = set(extract_keywords_in_body(text))
    if not current_kws:
        return []

    recent = find_recent_posts(target_date)
    candidates = []
    used_kws = set()

    for past_date, past_path in recent:
        past_text = past_path.read_text(encoding="utf-8", errors="ignore")
        past_kws = set(extract_keywords_in_body(past_text))
        shared = (current_kws & past_kws) - used_kws
        if not shared:
            continue
        anchor_kw = sorted(shared, key=lambda k: -len(k))[0]
        used_kws.add(anchor_kw)
        url = index.get(past_path.stem) or f"./{past_path.name}"
        candidates.append({
            "anchor_keyword": anchor_kw,
            "past_title": title_of(past_path),
            "past_date": past_date.strftime("%Y-%m-%d"),
            "url": url,
            "past_path": str(past_path),
        })
        if len(candidates) >= 3:
            break
    return candidates


def insert_links(text: str, candidates: list) -> str:
    """각 후보를 본문 안 첫 키워드 등장 문단 직후에 삽입."""
    out = text
    for c in candidates:
        kw = c["anchor_keyword"]
        # 키워드가 등장하는 문단 찾기 (## 헤딩 제외)
        pattern = re.compile(rf"(^(?!#).+?{re.escape(kw)}.+?$)\n", re.MULTILINE)
        link_line = f"\n> 📎 이전 분석: [{c['past_title']} ({c['past_date'][5:]})]({c['url']})\n"
        m = pattern.search(out)
        if m and link_line.strip() not in out:
            out = out[: m.end()] + link_line + out[m.end():]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post", help="검사할 .md 경로")
    ap.add_argument("--apply", action="store_true", help="본문에 직접 삽입 (.bak 백업)")
    args = ap.parse_args()

    p = Path(args.post)
    if not p.exists():
        print(f"파일 없음: {p}", file=sys.stderr)
        sys.exit(2)

    index = load_index()
    candidates = suggest_links(p, index)

    if not candidates:
        print("최근 14일 내 매칭되는 키워드/포스트 없음. 시리즈 링크 불필요.")
        return

    print(f"\n📎 {p.name}에 추가할 시리즈 링크 후보 ({len(candidates)}개):")
    for c in candidates:
        print(f"  • [{c['anchor_keyword']}] → {c['past_date']}  {c['past_title']}")
        print(f"      {c['url']}")

    if args.apply:
        text = p.read_text(encoding="utf-8")
        new_text = insert_links(text, candidates)
        if new_text != text:
            shutil.copy(p, p.with_suffix(p.suffix + ".bak"))
            p.write_text(new_text, encoding="utf-8")
            print(f"\n✅ 적용 완료 (.bak 백업 생성).")
        else:
            print("\n변경사항 없음 (모두 이미 삽입됨).")
    else:
        print("\n--apply 옵션으로 실제 삽입 가능 (백업 .bak 자동 생성).")


if __name__ == "__main__":
    main()
