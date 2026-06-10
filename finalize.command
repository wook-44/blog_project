#!/bin/bash
# finalize.command — 범용 마무리 (일회성 _finalize_*.command 대체, 2026-06-10)
# 샌드박스에서 PNG 렌더/푸시가 막혔을 때 Mac 더블클릭으로 마무리하는 위임 스크립트.
# ① 인포그래픽 PNG 렌더 ② copy_tool 재생성 ③ daily/ 정리 ④ GitHub 푸시 ⑤ 텔레그램 알림
#
# 사용법:
#   더블클릭                          → 오늘 날짜 본편 마무리
#   bash finalize.command 2026-06-09          → 해당 날짜 본편
#   bash finalize.command 2026-06-09 summary  → 해당 날짜 15:30 시황 요약
set -e
cd "$(dirname "$0")"
BASE="$(pwd)"
DATE="${1:-$(date +%Y-%m-%d)}"
MODE="${2:-main}"

if [ "$MODE" = "summary" ]; then
  TARGET="${DATE}-summary"
  SECTIONS="${DATE}_summary_sections.json"
  COPYGEN="scripts/gen_summary_copy_tool.py"
  COPYOUT="output/${DATE}_summary_copy_tool.html"
else
  TARGET="$DATE"
  SECTIONS="${DATE}_sections.json"
  COPYGEN="scripts/generate_copy_tool.py"
  COPYOUT="output/${DATE}_copy_tool.html"
fi

echo "① 인포그래픽 PNG 렌더 ($TARGET)..."
if [ -f "$SECTIONS" ]; then
  python3 stock-youtube-blog-writer/references/generate_infographics.py \
    --date "$TARGET" --data-file "$SECTIONS" --output "images/$TARGET" \
    || echo "  (generate 실패 — html_to_png 폴백)"
fi
if ! ls "images/$TARGET/"*.png >/dev/null 2>&1; then
  python3 scripts/html_to_png.py "$TARGET" 2>/dev/null || true
fi

echo "② copy_tool 재생성..."
# generate_copy_tool.py는 날짜를 위치 인자로 받음 (--date 아님)
python3 "$COPYGEN" "$DATE" || echo "  (copy_tool 재생성 스킵)"

echo "③ daily/$TARGET 정리..."
mkdir -p "daily/$TARGET/images"
cp images/$TARGET/*.png "daily/$TARGET/images/" 2>/dev/null || echo "  (PNG 없음)"
[ "$MODE" = "summary" ] && cp "${DATE}_summary_blog.md" "daily/$TARGET/blog_post.md" 2>/dev/null || true
cp "$COPYOUT" "daily/$TARGET/copy_tool.html" 2>/dev/null || true

echo "④ GitHub 푸시..."
bash "$BASE/push.command" "$DATE" "feat: ${TARGET} 마무리 (PNG+copy_tool)"

echo "⑤ 텔레그램 알림..."
python3 notify.py "✅ <b>${TARGET} 마무리 완료</b>
PNG $(ls images/$TARGET/*.png 2>/dev/null | wc -l | tr -d ' ')장 · copy_tool · 푸시 완료" 2>/dev/null || true

echo "🎉 완료"
