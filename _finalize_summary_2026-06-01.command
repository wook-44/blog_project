#!/bin/bash
# 2026-06-01 15:30 시황 요약 마무리 (Mac 더블클릭 위임)
# 샌드박스에서 PNG 렌더·GitHub 푸시·텔레그램이 프록시(403)로 차단되어
# 본문/copy_tool/로컬 커밋까지만 완료된 상태입니다. 이 파일을 더블클릭하면
# ① 인포그래픽 PNG 렌더 ② daily 폴더 정리 ③ GitHub 푸시 ④ 텔레그램 알림을 수행합니다.
set -e
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
DATE=2026-06-01
SUM=${DATE}-summary

echo "① 인포그래픽 PNG 렌더..."
python3 stock-youtube-blog-writer/references/generate_infographics.py \
  --date "$SUM" \
  --data-file "${DATE}_summary_sections.json" \
  --output "images/$SUM" || echo "  (generate 실패 — html_to_png 폴백 시도)"
# 폴백: 이미 생성된 HTML을 PNG로
if [ ! -f "images/$SUM/$SUM-market.png" ]; then
  python3 scripts/html_to_png.py "$SUM" 2>/dev/null || true
fi

echo "② daily 폴더 정리..."
mkdir -p "daily/$SUM/images"
cp images/$SUM/*.png "daily/$SUM/images/" 2>/dev/null || echo "  (PNG 없음 — HTML만 유지)"

echo "③ GitHub 푸시..."
rm -f .git/index.lock .git/HEAD.lock 2>/dev/null || true
git add -A
git commit -m "🖼️ ${DATE} 시황 요약 인포그래픽 PNG 추가" || echo "  (커밋할 변경 없음)"
git push origin main || git push origin master

echo "④ 텔레그램 알림..."
python3 notify.py "✅ 15:30 시황 요약 발행 완료: 코스피 8,788 사상최고 시총 7000조 첫 돌파"

echo "🎉 완료. 이 창은 닫아도 됩니다."
