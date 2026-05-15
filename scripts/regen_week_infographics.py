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
    # INFOGRAPHIC_DATA 주석을 가진 파일만 후보
    candidates = [p for p in candidates if "INFOGRAPHIC_DATA:" in p.read_text(encoding="utf-8", errors="ignore")]
    if not candidates:
        raise SystemExit(f"{date_str} INFOGRAPHIC_DATA .md 없음")
    return candidates[0]


def daterange(start: str, end: str):
    d0 = datetime.strptime(start, "%Y-%m-%d")
    d1 = datetime.strptime(end, "%Y-%m-%d")
    cur = d0
    while cur <= d1:
        yield cur.strftime("%Y-%m-%d")
        cur += timedelta(days=1)


def notify_telegram(msg: str):
    """텔레그램 보고 (있을 때만, 실패 무시)."""
    try:
        notify_script = BLOG_DIR / "notify.py"
        config = BLOG_DIR / ".telegram_config"
        if not (notify_script.exists() and config.exists()):
            return
        import subprocess
        subprocess.run(
            ["python3", str(notify_script), msg],
            check=False, capture_output=True, timeout=20,
        )
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start", help="시작일 YYYY-MM-DD")
    ap.add_argument("end", help="종료일 YYYY-MM-DD")
    args = ap.parse_args()

    processed = []
    skipped = []
    for d in daterange(args.start, args.end):
        try:
            md = find_post(d)
        except SystemExit:
            print(f"  ⚠️  {d} 건너뜀 (md 없음)")
            skipped.append(d)
            continue
        data = extract_data(md)
        out_dir = BLOG_DIR / "images" / d
        print(f"\n📅 {d}  ← {md.name}")
        results = generate_all(d, data, out_dir)
        processed.append((d, len(results)))

    # 텔레그램 보고
    if processed:
        body = "\n".join(f"· {d} → {n}장" for d, n in processed)
        msg = f"🎨 <b>인포그래픽 HTML 생성 완료</b>\n{body}"
        if skipped:
            msg += f"\n건너뜀: {len(skipped)}일"
        notify_telegram(msg)


if __name__ == "__main__":
    main()
