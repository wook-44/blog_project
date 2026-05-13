"""
제목·태그·후킹 린터 (Agent 00)
=================================
역할: 발행 직전, 톤북 룰 강제 검사 — fail 시 종료 코드 1
검사 항목:
  1) 제목 길이 28~32자
  2) 메인 키워드가 앞 12자 이내
  3) [날짜] 접두어 금지
  4) 첫 100자 후킹 문단 존재
  5) 영상 정보 테이블이 첫 200자 안에 없음
  6) 태그 30개 이상, 롱테일 비중 50% 이상
  7) 시리즈 내부 링크 1개 이상 (14일 내 매칭 키워드 있을 시)
사용: python scripts/agents/00_title_tag_linter.py path/to/post.md
"""
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

BLOG_DIR = Path(__file__).resolve().parents[2]

# ── 톤북 임계값 ────────────────────────────────────────
TITLE_MIN, TITLE_MAX = 28, 32
TITLE_KW_HEAD_LIMIT = 12          # 메인 키워드는 앞 12자 안에
HOOK_MIN, HOOK_MAX = 100, 200     # 첫 후킹 문단 길이
TAGS_MIN = 30
LONGTAIL_MIN_RATIO = 0.5          # 롱테일(7자 이상 한글) 비중
BODY_MIN_CHARS = 2200             # 공백포함 본문

MAIN_KEYWORDS = [
    "코스피", "코스닥", "삼성전자", "SK하이닉스", "현대차", "기아",
    "엔비디아", "테슬라", "애플", "구글", "마이크로소프트", "메타",
    "반도체", "AI", "로봇", "이차전지", "방산",
    "금리", "환율", "유가", "호르무즈", "FOMC", "트럼프",
]

VIDEO_META_PHRASES = [
    "📺 영상 정보", "## 영상 정보", "채널 |", "출연자 |",
    "업로드일 |", "영상 링크 |", "광수 생각", "오후장 한 마디",
    "방과후 경제교실",
]

DISCLAIMER_KEYWORDS = ["투자의 책임", "참고용", "본인에게 있"]


def parse_frontmatter(text: str):
    """간단한 마크다운 frontmatter 추출 (YAML-ish)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = text[3:end]
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def extract_title(text: str, meta: dict) -> str:
    if "title" in meta:
        return meta["title"].strip('"\'')
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_tags(text: str, meta: dict):
    """frontmatter의 tags 또는 본문 마지막 #태그 라인."""
    if "tags" in meta:
        raw = meta["tags"]
        raw = raw.strip("[]")
        return [t.strip().lstrip("#").strip() for t in raw.split(",") if t.strip()]
    tags = re.findall(r"#([\w가-힣]+)", text)
    return tags


def extract_hook(text: str) -> str:
    """# 제목 다음 첫 본문 문단."""
    body = re.sub(r"^---.*?---\n", "", text, count=1, flags=re.DOTALL)
    parts = re.split(r"^#\s+.+$", body, maxsplit=1, flags=re.MULTILINE)
    if len(parts) < 2:
        return ""
    rest = parts[1].lstrip("\n")
    # 첫 ## 소제목 전까지가 후킹 영역
    next_h = re.search(r"^##\s", rest, re.MULTILINE)
    hook = rest[: next_h.start()] if next_h else rest[:500]
    return hook.strip()


def find_main_keyword_position(title: str) -> tuple:
    """제목에서 메인 키워드 위치(없으면 -1)와 키워드 반환."""
    for kw in MAIN_KEYWORDS:
        pos = title.find(kw)
        if pos >= 0:
            return pos, kw
    return -1, ""


def classify_tag(tag: str) -> str:
    """main / sub / longtail 분류 (한글 글자수 기준)."""
    han = len(re.findall(r"[가-힣]", tag))
    if han <= 3:
        return "main"
    if han <= 6:
        return "sub"
    return "longtail"


def find_series_links(date_str: str, body: str) -> list:
    """본문에 이전 분석 링크가 있으면 리스트 반환."""
    return re.findall(r"이전 분석[^\[]*\[([^\]]+)\]\(([^)]+)\)", body)


def has_recent_keyword_post(date_str: str, body: str) -> bool:
    """14일 내 동일 키워드 포스트 존재 여부."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False
    posts = list(BLOG_DIR.glob("20*-*.md"))
    recent_kw = set()
    for p in posts:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.stem)
        if not m:
            continue
        try:
            pd = datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if pd >= d or (d - pd).days > 14:
            continue
        for kw in MAIN_KEYWORDS:
            if kw in p.stem or kw in p.read_text(encoding="utf-8", errors="ignore")[:500]:
                recent_kw.add(kw)
    body_kw = {kw for kw in MAIN_KEYWORDS if kw in body[:2000]}
    return bool(recent_kw & body_kw)


# ── 검사 함수 ─────────────────────────────────────────
def lint(post_path: Path) -> dict:
    text = post_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    issues = []
    passed = []

    # 0) 날짜 추출 (파일명 기준)
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", post_path.stem)
    date_str = date_match.group(1) if date_match else "unknown"

    title = extract_title(text, meta)
    tags = extract_tags(text, meta)
    hook = extract_hook(text)
    body_chars = len(re.sub(r"\s", "", body))

    # ── 검사 1: 제목 길이
    title_len = len(title)
    if not (TITLE_MIN <= title_len <= TITLE_MAX):
        issues.append(f"[T1] 제목 길이 {title_len}자 (권장 {TITLE_MIN}~{TITLE_MAX}자): {title!r}")
    else:
        passed.append(f"[T1] 제목 길이 OK ({title_len}자)")

    # ── 검사 2: 날짜 접두어 금지
    if re.match(r"\s*\[?\d{4}[\.\-/]\d{1,2}[\.\-/]\d{1,2}", title):
        issues.append(f"[T2] 제목 앞 날짜 접두어 발견 — 본문 메타로 옮길 것")
    else:
        passed.append(f"[T2] 날짜 접두어 없음")

    # ── 검사 3: 메인 키워드 앞쪽 배치
    pos, kw = find_main_keyword_position(title)
    if pos < 0:
        issues.append(f"[T3] 메인 키워드가 제목에 없음 (예: 코스피/삼성전자/SK하이닉스)")
    elif pos > TITLE_KW_HEAD_LIMIT:
        issues.append(f"[T3] 메인 키워드 '{kw}' 위치 {pos}자 — 앞 {TITLE_KW_HEAD_LIMIT}자 이내 권장")
    else:
        passed.append(f"[T3] 메인 키워드 '{kw}' 앞쪽 배치 OK ({pos}자)")

    # ── 검사 4: 첫 100자 후킹 문단
    hook_first = hook[:200]
    hook_chars = len(re.sub(r"\s", "", hook_first))
    if hook_chars < HOOK_MIN:
        issues.append(f"[H1] 첫 후킹 문단이 너무 짧음 ({hook_chars}자, 권장 {HOOK_MIN}~{HOOK_MAX}자)")
    else:
        passed.append(f"[H1] 첫 후킹 문단 길이 OK ({hook_chars}자)")

    # ── 검사 5: 영상 정보 테이블 첫 200자 차단
    leading = body[:400]
    leaked = [p for p in VIDEO_META_PHRASES if p in leading]
    if leaked:
        issues.append(f"[H2] 첫 200자에 영상 메타 노출: {leaked} — 부록(최하단)으로 이동")
    else:
        passed.append(f"[H2] 첫 영역 영상 메타 없음")

    # ── 검사 6: 후킹 영역 키워드 2회+
    if kw and kw != "":
        hook_kw_count = hook_first.count(kw)
        if hook_kw_count < 2:
            issues.append(f"[H3] 후킹 영역 '{kw}' 키워드 {hook_kw_count}회 — 2회 이상 권장")
        else:
            passed.append(f"[H3] 후킹 영역 키워드 반복 OK ({hook_kw_count}회)")

    # ── 검사 7: 태그 30개
    tag_count = len(tags)
    if tag_count < TAGS_MIN:
        issues.append(f"[G1] 태그 {tag_count}개 — 최소 {TAGS_MIN}개")
    else:
        passed.append(f"[G1] 태그 수 OK ({tag_count}개)")

    # ── 검사 8: 롱테일 비중
    if tags:
        longtail = sum(1 for t in tags if classify_tag(t) == "longtail")
        ratio = longtail / len(tags)
        if ratio < LONGTAIL_MIN_RATIO:
            issues.append(f"[G2] 롱테일 비중 {ratio:.0%} — {LONGTAIL_MIN_RATIO:.0%} 이상 권장 (현재 {longtail}/{len(tags)})")
        else:
            passed.append(f"[G2] 롱테일 비중 OK ({ratio:.0%})")

    # ── 검사 9: 본문 분량
    if body_chars < BODY_MIN_CHARS:
        issues.append(f"[B1] 본문 글자수 {body_chars}자 — {BODY_MIN_CHARS}자 이상")
    else:
        passed.append(f"[B1] 본문 분량 OK ({body_chars}자)")

    # ── 검사 10: 투자 주의 문구
    if not any(k in body for k in DISCLAIMER_KEYWORDS):
        issues.append(f"[B2] 투자 주의 문구 없음 — 본문 최하단에 필수")
    else:
        passed.append(f"[B2] 투자 주의 문구 존재")

    # ── 검사 11: 시리즈 내부 링크 — 비활성화됨
    # 네이버 에디터가 마크다운 링크 `[제목](경로)`를 렌더링 못해서 깨져 보임.
    # 사용자 요청으로 자동 추가 룰 제거 (2026-05-13).

    return {
        "post": str(post_path),
        "date": date_str,
        "title": title,
        "title_len": title_len,
        "tag_count": tag_count,
        "body_chars": body_chars,
        "issues": issues,
        "passed": passed,
        "ok": len(issues) == 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post", nargs="?", help="검사할 .md 경로")
    ap.add_argument("--all", action="store_true", help="블로그 폴더 전체 검사")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    ap.add_argument("--strict", action="store_true", help="이슈 있으면 종료코드 1")
    args = ap.parse_args()

    if args.all:
        targets = sorted(BLOG_DIR.glob("20*-*.md"))
    else:
        if not args.post:
            print("사용: 00_title_tag_linter.py <post.md> 또는 --all", file=sys.stderr)
            sys.exit(2)
        targets = [Path(args.post)]

    reports = [lint(p) for p in targets if p.is_file()]

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for r in reports:
            status = "✅ PASS" if r["ok"] else "❌ FAIL"
            print(f"\n{'='*70}")
            print(f"{status}  {Path(r['post']).name}")
            print(f"  제목({r['title_len']}자) · 태그({r['tag_count']}개) · 본문({r['body_chars']}자)")
            for p in r["passed"]:
                print(f"  ✓ {p}")
            for i in r["issues"]:
                print(f"  ✗ {i}")
        total = len(reports)
        failed = sum(1 for r in reports if not r["ok"])
        print(f"\n{'='*70}")
        print(f"총 {total}편 / 통과 {total-failed} / 실패 {failed}")

    if args.strict and any(not r["ok"] for r in reports):
        sys.exit(1)


if __name__ == "__main__":
    main()
