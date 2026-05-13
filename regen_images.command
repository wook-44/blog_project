#!/bin/bash
# regen_images.command
# 인포그래픽 HTML → PNG 재생성 (나눔고딕 한글 폰트 적용)

cd "/Users/chanwook/Documents/Claude/Projects/블로그"
echo "🖼️  인포그래픽 PNG 재생성 중 (Chrome headless)..."
echo ""

python3 scripts/html_to_png.py --all

echo ""
echo "🔄 HTML 복붙 도구 재생성 중..."
for date in 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24 \
            2026-04-28 2026-04-29 2026-04-30 \
            2026-05-06 2026-05-07 2026-05-08 2026-05-11 2026-05-12; do
  echo "  📅 $date"
  python3 scripts/generate_copy_tool.py "$date" 2>/dev/null || echo "  ⚠️  $date 스킵 (md 파일 없음)"
done

echo ""
echo "✅ 모두 완료! output/ 폴더에 업데이트된 HTML이 있습니다."
echo ""
read -p "엔터를 눌러 닫기..."
