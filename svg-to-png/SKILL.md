---
name: svg-to-png
description: |
  SVG 인포그래픽을 한글 깨짐 없는 PNG로 변환하는 스킬. NanumGothic(나눔고딕)을 포함한 한글 폰트를 우선 적용하며,
  Chrome headless 렌더링 방식으로 브라우저와 동일한 품질의 PNG를 생성한다.
  
  다음 상황에서 반드시 이 스킬을 사용한다:
  - "SVG를 PNG로 바꿔줘", "이미지 PNG로 만들어줘", "PNG로 변환해줘"
  - "한글이 깨져요", "폰트가 네모로 나와요", "글자가 깨졌어요"
  - SVG 파일이 있고 PNG 변환이 필요한 모든 경우
  - 블로그 인포그래픽 PNG 생성 요청
  - 섹션별 이미지를 PNG로 저장할 때
  - 나눔고딕 등 한글 폰트가 포함된 이미지를 PNG로 출력할 때
---

# SVG → PNG 변환 스킬 (한글 나눔고딕 지원)

## 핵심 원리

**왜 한글이 깨지는가?**  
Python 라이브러리(cairosvg, Pillow 등)는 시스템에 설치된 폰트를 못 찾거나 CJK 렌더링을 제대로 처리하지 못한다.  
이 스킬은 **Chrome headless** 방식으로 HTML 내부에 SVG를 임베드해 렌더링한다.  
macOS의 Chrome은 시스템에 설치된 NanumGothic을 그대로 사용하므로 한글이 완벽하게 표시된다.

## 변환 방법

`references/svg_to_png.py` 스크립트를 사용한다:

```bash
python /path/to/svg-to-png/references/svg_to_png.py \
  --input img1_market_status.svg \
  --output output/img1_market_status.png
```

여러 파일 일괄 변환:
```bash
python /path/to/svg-to-png/references/svg_to_png.py \
  --input img1.svg img2.svg img3.svg img4.svg img5.svg \
  --output ./images/
```

## 실행 순서

1. 변환할 SVG 파일 경로 확인
2. `svg_to_png.py` 실행 (Chrome 경로 자동 탐색)
3. PNG 저장 확인 후 사용자에게 링크 제공

## 출력 사양
- 크기: SVG viewBox 기준 (기본 800×450px, 2x 레티나 옵션 지원)
- 배경: SVG 배경색 그대로 유지
- 포맷: PNG (24-bit, 투명도 지원)

## 실패 시 대처

| 상황 | 해결책 |
|------|--------|
| Chrome 없음 | Chromium 자동 탐색, 없으면 brew install chromium 안내 |
| 폰트 없음 | macOS: `~/Library/Fonts/`에 NanumGothic 설치 필요 |
| 타임아웃 | `--timeout 30` 옵션으로 늘리기 |

자세한 스크립트 사용법은 `references/svg_to_png.py` 주석 참조.
