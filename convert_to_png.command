#!/bin/bash
BLOG="/Users/chanwook/Documents/Claude/Projects/블로그"
SCRIPT="$BLOG/svg-to-png/references/svg_to_png.py"
OUT="$BLOG/images/2026-04-27"

mkdir -p "$OUT"
echo "🖼️  SVG → PNG 변환 시작..."
echo ""

# Pillow 없으면 자동 설치 (PNG 크롭용)
python3 -c "import PIL" 2>/dev/null || {
    echo "📦 Pillow 설치 중..."
    pip3 install Pillow --user --quiet 2>/dev/null || \
    pip3 install Pillow --quiet 2>/dev/null || \
    python3 -m pip install Pillow --user --quiet
}

python3 "$SCRIPT" \
  --input \
    "$BLOG/img1_market_status.svg" \
    "$BLOG/img2_market_structure.svg" \
    "$BLOG/img3_psychology.svg" \
    "$BLOG/img4_checklist.svg" \
    "$BLOG/img5_summary.svg" \
  --output "$OUT/" \
  --scale 2

echo ""
echo "저장 위치: $OUT"
ls -lh "$OUT"/*.png 2>/dev/null || echo "PNG 파일 없음"
read -p "엔터를 눌러 닫기..."
