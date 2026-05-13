"""
주차 단위 인포그래픽 일괄 재생성
사용: python scripts/regen_week_infographics.py 2026-04-20 2026-04-24
.md 본문 안 INFOGRAPHIC_DATA 주석에서 JSON을 추출해 generate_infographics에 넘긴다.
"""
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

BLOG_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BLOG_DIR / "stock-youtube-blog-writer" / "references"))
from generate_infographics import generate_all  # noqa: E402


def extract_data(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"INFOGRAPHIC_DATA:\s*(\{.*?\})\s*-->", text, re.DOTALL)
    if not m:
        raise SystemExit(f"INFOGRAPHIC_DATA 주석 없음: {md_path}")
    return json.loads(m.group(1))


def find_post(date_str: str) -> Path:
    candidates = list(BLOG_DIR.glob(f"{date_str}-*.md"))
    candidates = [p for p in candidates if not p.name.endswith(".bak")]
    if not candidates:
        raise SystemExit(f"{date_str} .md 없음")
    return candidates[0]


def daterange(start: str, end: str):
    d0 = datetime.strptime(start, "%Y-%m-%d")
    d1 = datetime.strptime(end, "%Y-%m-%d")
    cur = d0
    while cur <= d1:
        yield cur.strftime("%Y-%m-%d")
        cur += timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start", help="시작일 YYYY-MM-DD")
    ap.add_argument("end", help="종료일 YYYY-MM-DD")
    args = ap.parse_args()

    for d in daterange(args.start, args.end):
        try:
            md = find_post(d)
        except SystemExit:
            print(f"  ⚠️  {d} 건너뜀 (md 없음)")
            continue
        data = extract_data(md)
        out_dir = BLOG_DIR / "images" / d
        print(f"\n📅 {d}  ← {md.name}")
        generate_all(d, data, out_dir)


if __name__ == "__main__":
    main()
