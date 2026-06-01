#!/usr/bin/env python3
"""
fortify_html_fonts.py
─────────────────────
인포그래픽 HTML 안의 SVG <text> 태그 모두에 font-family를 직접 명시한다.

Why: Chrome headless가 일부 텍스트 컨텍스트에서 폰트 상속을 잃고 시스템
라틴 폰트로 폴백 → 한글 글리프 누락 발생 (memory: feedback_png_korean_fix).
SVG 루트 font-family 한 번 선언만으론 부족하다.

사용법:
  python3 scripts/fortify_html_fonts.py path/to/file1.html path/to/file2.html ...

각 파일을 in-place로 수정한다. 백업은 .html.bak으로 1회 자동 생성.
"""
import sys
import re
from pathlib import Path

FONT_FAMILY = "'NanumGothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
# font-family를 이미 가진 <text>는 건너뜀
TEXT_PATTERN = re.compile(r'<text\b(?![^>]*font-family)', flags=re.IGNORECASE)


def fortify(html_path: Path) -> int:
    """파일을 in-place로 수정하고 보강된 <text> 개수를 반환한다."""
    content = html_path.read_text(encoding='utf-8')
    backup = html_path.with_suffix(html_path.suffix + '.bak')
    if not backup.exists():
        backup.write_text(content, encoding='utf-8')

    new_content, n = TEXT_PATTERN.subn(
        f'<text font-family="{FONT_FAMILY}"', content
    )
    html_path.write_text(new_content, encoding='utf-8')
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    total = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"  ⚠️  파일 없음: {p}")
            continue
        n = fortify(p)
        total += n
        print(f"  ✓ {p.name}: {n}개 <text> 보강")

    print(f"\n총 {total}개 텍스트 태그에 폰트 직접 명시 완료.")


if __name__ == '__main__':
    main()
