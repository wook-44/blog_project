"""
어려운 용어에 괄호 풀이 추가 — 5월 9편 일괄.
첫 번째 출현에만 풀이를 붙이고, 이후엔 그대로 유지.
사용: python scripts/simplify_jargon.py 2026-05-01-...md 2026-05-04-...md ...
"""
import re
import sys
from pathlib import Path

# 용어 → 첫 출현 시 추가할 괄호 풀이
GLOSSARY = [
    ("Sell the news", "발표 직후 차익실현 매도"),
    ("Buy the rumor, Sell the fact", "소문에 사고 사실에 팔라"),
    ("FOMO", "Fear Of Missing Out, 못 사면 손해라는 두려움"),
    ("AI CapEx", "AI 인프라 투자비"),
    ("AI 인프라 투자비", None),  # placeholder — never expand
    ("MSCI 선진국 편입", "글로벌 큰돈이 자동으로 한국 주식을 사게 되는 자격"),
    ("MSCI 선진국 지수 편입", "글로벌 큰돈이 자동으로 한국 주식을 사게 되는 자격"),
    ("롱텀 머니", "연기금처럼 단기 매매 안 하는 장기 외국인 자금"),
    ("패스트트랙", "빠른 절차"),
    ("NBER", "미국 국가경제연구소"),
    ("EPS", "주당순이익"),
    ("HBM", "고대역폭 메모리, AI 반도체 핵심"),
    ("PER", "주가수익비율"),
    ("PBR", "주가순자산비율"),
    ("어닝 서프라이즈", "예상보다 훨씬 좋은 실적 발표"),
    ("선반영", "주가에 미리 반영된 상태"),
    ("차익실현", "수익 확정 매도"),
    ("바벨 전략", "양쪽 끝(안전+공격) 분산"),
    ("순환매", "한 섹터가 쉬면 다른 섹터로 자금이 옮겨가는 흐름"),
    ("섹터 로테이션", "한 업종에서 다른 업종으로 주도주 이동"),
    ("CPI", "소비자물가지수, 인플레 지표"),
    ("FOMC", "미국 연준 통화정책 회의"),
    ("피지컬 AI", "AI를 로봇 같은 물리적 실체에 탑재한 것"),
    ("LTV", "주택 담보 대비 대출 비율"),
]


def add_glossary(text: str) -> str:
    """본문에서 각 용어 첫 출현 시 괄호 풀이 추가."""
    # INFOGRAPHIC_DATA 영역은 건드리지 않음
    parts = text.split("<!--\nINFOGRAPHIC_DATA")
    body = parts[0]
    rest = ("<!--\nINFOGRAPHIC_DATA" + parts[1]) if len(parts) > 1 else ""

    for term, gloss in GLOSSARY:
        if gloss is None:
            continue
        # 이미 풀이가 붙은 경우 스킵
        pattern_already = re.compile(re.escape(term) + r"\s*\(")
        if pattern_already.search(body):
            continue
        # 본문 첫 출현 위치
        pattern = re.compile(r"(?<![가-힣\w])" + re.escape(term) + r"(?![가-힣\w])")
        m = pattern.search(body)
        if m:
            # 첫 출현에만 (풀이) 삽입
            body = body[: m.end()] + f"({gloss})" + body[m.end():]
    return body + rest


def main():
    targets = sys.argv[1:]
    if not targets:
        print("Usage: simplify_jargon.py file.md [file.md ...]")
        sys.exit(2)
    changed = 0
    for p in targets:
        path = Path(p)
        if not path.exists():
            print(f"  ⚠️  {p} 없음")
            continue
        orig = path.read_text(encoding="utf-8")
        new = add_glossary(orig)
        if new != orig:
            path.write_text(new, encoding="utf-8")
            added = new.count("(") - orig.count("(")
            print(f"  ✓ {path.name}: +{added} 풀이 추가")
            changed += 1
        else:
            print(f"  · {path.name}: 변경 없음")
    print(f"\n총 {changed}편 갱신")


if __name__ == "__main__":
    main()
