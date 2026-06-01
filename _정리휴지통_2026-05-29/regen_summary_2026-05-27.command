#!/bin/bash
# 2026-05-27 시황 요약 PNG 한글 깨짐 수정 — fortify + 재렌더 + copy_tool 재생성
set -e
cd "$(dirname "$0")"

DATE="2026-05-27-summary"
SUMMARY_DATE="2026-05-27"

echo "================================="
echo "  써머리 PNG 한글 깨짐 수정"
echo "================================="
echo ""

echo "[1/3] html_to_png.py 실행 (Playwright + NanumGothic) ..."
python3 scripts/html_to_png.py "$DATE"

echo ""
echo "[2/3] PNG → daily/ 폴더 동기화 (있으면) ..."
SRC_PNG="images/${DATE}/${DATE}-market.png"
DST_DIR="daily/${DATE}/images"
if [ -d "$DST_DIR" ]; then
  cp "$SRC_PNG" "$DST_DIR/" && echo "  ✅ $DST_DIR/${DATE}-market.png 복사"
fi

echo ""
echo "[3/3] gen_summary_copy_tool.py 재실행 ..."
python3 scripts/gen_summary_copy_tool.py "$SUMMARY_DATE"

echo ""
echo "================================="
echo "  완료. 결과 PNG/카피툴 위치:"
echo "  - images/${DATE}/${DATE}-market.png"
echo "  - output/${SUMMARY_DATE}_summary_copy_tool.html"
echo "================================="

# 텔레그램 알림 (있으면)
if [ -f notify.py ] && [ -f .telegram_config ]; then
  python3 notify.py "✅ 5/27 써머리 PNG 한글 깨짐 수정 완료" || true
fi

echo ""
read -p "엔터를 누르면 창이 닫힙니다..."
