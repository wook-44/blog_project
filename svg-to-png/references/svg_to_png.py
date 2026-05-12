"""
svg_to_png.py
─────────────
SVG → PNG 변환기 (한글 나눔고딕 완벽 지원)

방식: SVG를 HTML에 임베드 → Chrome headless 스크린샷
- NanumGothic 등 macOS 시스템 폰트를 그대로 사용해 한글 깨짐 없음
- 추가 라이브러리 설치 불필요 (표준 라이브러리 + subprocess만 사용)

사용법:
  # 단일 파일
  python svg_to_png.py --input img1.svg --output ./out/img1.png

  # 여러 파일 일괄 변환
  python svg_to_png.py --input img1.svg img2.svg --output ./out/

  # 레티나(2x) 해상도
  python svg_to_png.py --input img1.svg --output ./out/ --scale 2

  # 커스텀 크기 지정
  python svg_to_png.py --input img1.svg --output ./out/ --width 1200 --height 630
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


# ── Chrome 실행 파일 후보 (macOS + Linux) ─────────────────────────────
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "google-chrome-stable",
    "chromium-browser",
    "chromium",
]


def find_chrome() -> Optional[str]:
    """사용 가능한 Chrome/Chromium 경로를 반환한다."""
    for candidate in CHROME_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
        # PATH에서 찾기
        result = subprocess.run(
            ["which", candidate], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


def get_svg_dimensions(svg_path: Path) -> tuple[int, int]:
    """SVG viewBox 또는 width/height 속성에서 크기를 추출한다."""
    content = svg_path.read_text(encoding="utf-8")

    # viewBox 파싱: "0 0 800 450"
    vb = re.search(r'viewBox\s*=\s*["\'][\d.]+ [\d.]+ ([\d.]+) ([\d.]+)["\']', content)
    if vb:
        return int(float(vb.group(1))), int(float(vb.group(2)))

    # width/height 속성 파싱
    w = re.search(r'\bwidth\s*=\s*["\'](\d+)', content)
    h = re.search(r'\bheight\s*=\s*["\'](\d+)', content)
    if w and h:
        return int(w.group(1)), int(h.group(1))

    return 800, 450  # 기본값


def build_html_wrapper(svg_content: str, width: int, height: int) -> str:
    """
    SVG를 HTML에 임베드한다.
    - @font-face로 macOS 시스템 나눔고딕 우선 로드
    - Google Fonts를 웹 폴백으로 선언 (인터넷 연결 시)
    - body 크기를 SVG와 동일하게 고정해 스크린샷 영역 정확히 맞춤
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  /* 시스템 나눔고딕 우선 로드 */
  @font-face {{
    font-family: 'NanumGothic';
    src: local('NanumGothic'),
         local('Nanum Gothic'),
         local('나눔고딕');
    font-weight: 400;
  }}
  @font-face {{
    font-family: 'NanumGothic';
    src: local('NanumGothic Bold'),
         local('NanumGothicBold'),
         local('나눔고딕 Bold');
    font-weight: 700;
  }}
  @font-face {{
    font-family: 'NanumGothic';
    src: local('NanumGothicExtraBold'),
         local('NanumGothic ExtraBold'),
         local('나눔고딕 ExtraBold');
    font-weight: 800 900;
  }}

  /* 폴백: 나눔바른고딕, Apple SD Gothic Neo, Noto Sans KR */
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-font-smoothing: antialiased;
  }}
  html, body {{
    width: {width}px;
    height: {height}px;
    overflow: hidden;
    background: transparent;
  }}
  svg {{
    width: {width}px;
    height: {height}px;
    display: block;
  }}
</style>
</head>
<body>
{svg_content}
</body>
</html>"""


def svg_to_png(
    svg_path: Path,
    png_path: Path,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: float = 1.0,
    timeout: int = 20,
) -> bool:
    """
    SVG 파일을 PNG로 변환한다.

    Returns:
        True if successful, False otherwise.
    """
    chrome = find_chrome()
    if not chrome:
        print(
            "❌ Chrome/Chromium을 찾을 수 없습니다.\n"
            "   설치: brew install --cask google-chrome\n"
            "   또는: brew install chromium"
        )
        return False

    # SVG 크기 결정
    svg_w, svg_h = get_svg_dimensions(svg_path)
    render_w = int((width or svg_w) * scale)
    render_h = int((height or svg_h) * scale)

    # SVG 내용 읽기
    svg_content = svg_path.read_text(encoding="utf-8")

    # SVG에 font-family가 없으면 나눔고딕 추가
    if "NanumGothic" not in svg_content and "font-family" not in svg_content:
        svg_content = svg_content.replace(
            "<svg",
            "<svg font-family=\"'NanumGothic', 'Nanum Gothic', 'Apple SD Gothic Neo', sans-serif\"",
            1,
        )

    # SVG에 명시적 width/height 주입 (viewBox 비율 유지)
    import re as _re
    svg_content = _re.sub(
        r'(<svg\b)([^>]*)(>)',
        lambda m: (
            m.group(1)
            + _re.sub(r'\s+(width|height)="[^"]*"', '', m.group(2))
            + f' width="{render_w}" height="{render_h}"'
            + m.group(3)
        ),
        svg_content,
        count=1,
    )

    # HTML 래퍼 생성
    # Chrome headless는 하단에 보이지 않는 여백을 남기므로
    # 창을 render_h + 150px로 크게 잡고 나중에 크롭한다
    CHROME_BOTTOM_MARGIN = 150
    html_content = build_html_wrapper(svg_content, render_w, render_h)

    # 임시 HTML 파일 생성
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    png_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--disable-extensions",
            "--force-device-scale-factor=1",
            f"--window-size={render_w},{render_h + CHROME_BOTTOM_MARGIN}",  # 여유 높이
            f"--screenshot={png_path.resolve()}",
            f"file://{Path(tmp_path).resolve()}",
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=timeout)

        if png_path.exists() and png_path.stat().st_size > 500:
            # 크롭: Chrome이 찍은 스크린샷에서 정확히 render_w × render_h만 잘라낸다
            cropped = False
            try:
                from PIL import Image as _Img
                _img = _Img.open(png_path)
                _w, _h = _img.size
                if _w >= render_w and _h >= render_h:
                    _img.crop((0, 0, render_w, render_h)).save(png_path, optimize=True)
                    cropped = True
            except ImportError:
                pass
            if not cropped:
                # Pillow 없을 때: macOS 내장 sips 사용
                subprocess.run(
                    ["sips", "--cropToHeightWidth", str(render_h), str(render_w),
                     "--cropOffset", "0", "0", str(png_path)],
                    capture_output=True,
                )

            size_kb = png_path.stat().st_size / 1024
            print(f"  ✅ {png_path.name}  ({render_w}×{render_h}px, {size_kb:.1f}KB)")
            return True
        else:
            print(f"  ❌ 변환 실패: {png_path.name}")
            if result.stderr:
                print(f"     Chrome 오류: {result.stderr.decode()[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ❌ 타임아웃 ({timeout}초): {svg_path.name}")
        print(f"     --timeout 옵션으로 시간을 늘려보세요")
        return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False
    finally:
        os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="SVG → PNG 변환기 (한글 나눔고딕 지원)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        nargs="+",
        required=True,
        help="입력 SVG 파일 (여러 개 가능)",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="출력 경로 (파일명 또는 디렉토리)",
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=None,
        help="출력 너비 (기본: SVG viewBox 크기)",
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=None,
        help="출력 높이 (기본: SVG viewBox 크기)",
    )
    parser.add_argument(
        "--scale", "-s",
        type=float,
        default=1.0,
        help="배율 (2.0 = 레티나 2x, 기본: 1.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Chrome 타임아웃 초 (기본: 20)",
    )

    args = parser.parse_args()

    # Chrome 확인
    chrome = find_chrome()
    if chrome:
        print(f"🌐 Chrome 경로: {chrome}")
    else:
        print("❌ Chrome을 찾을 수 없습니다. brew install --cask google-chrome")
        sys.exit(1)

    # 출력 경로 처리
    output_path = Path(args.output)
    is_dir_output = (
        output_path.is_dir()
        or str(args.output).endswith("/")
        or len(args.input) > 1
    )

    if is_dir_output:
        output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n📐 스케일: {args.scale}x  |  타임아웃: {args.timeout}초\n")

    success_count = 0
    for svg_file in args.input:
        svg_path = Path(svg_file)
        if not svg_path.exists():
            print(f"  ⚠️  파일 없음: {svg_file}")
            continue

        # PNG 출력 경로 결정
        if is_dir_output:
            png_path = output_path / (svg_path.stem + ".png")
        else:
            png_path = output_path

        if svg_to_png(
            svg_path=svg_path,
            png_path=png_path,
            width=args.width,
            height=args.height,
            scale=args.scale,
            timeout=args.timeout,
        ):
            success_count += 1

    total = len(args.input)
    print(f"\n완료: {success_count}/{total}개 변환 성공")

    if success_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
