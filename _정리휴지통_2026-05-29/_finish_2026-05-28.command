#!/bin/bash
# _finish_2026-05-28.command
# 17:30 Claude 스케줄 결과 인계 — Mac에서 PNG 생성 + copy_tool 재생성 + Git 푸시
# 더블클릭하여 실행하세요.

set -e
cd "$(dirname "$0")"
BLOG="$(pwd)"
DATE="2026-05-28"
HTML_DIR="$BLOG/images/$DATE/html"
OUT_DIR="$BLOG/images/$DATE"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DAILY_DIR="$BLOG/daily/$DATE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📅  ${DATE} 블로그 후처리 (Claude 17:30 인계)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 0) git lock 정리
rm -f "$BLOG"/.git/HEAD.lock "$BLOG"/.git/index.lock 2>/dev/null || true

# 1) HTML → PNG 변환
echo ""
echo "🎨 [1/4] 인포그래픽 PNG 변환..."
if [ ! -d "$HTML_DIR" ]; then
  echo "  ❌ HTML 폴더 없음: $HTML_DIR"
  exit 1
fi
for HTML in "$HTML_DIR"/${DATE}-*.html; do
  [ -f "$HTML" ] || continue
  BASE=$(basename "$HTML" .html)
  PNG="$OUT_DIR/$BASE.png"
  echo "   ▶ $BASE.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size=1080,1080 --screenshot="$PNG" "file://$HTML" 2>&1 | tail -1 || true
done
ls -lh "$OUT_DIR"/*.png 2>/dev/null | tail -5
echo ""

# 2) copy_tool 재생성 (PNG 포함)
echo "📄 [2/4] HTML 복붙 도구 재생성..."
python3 scripts/generate_copy_tool.py "$DATE" 2>&1 | tail -5
echo ""

# 3) daily/ 폴더에 PNG 복사
echo "📁 [3/4] daily/$DATE/images 동기화..."
mkdir -p "$DAILY_DIR/images"
cp "$OUT_DIR"/${DATE}-*.png "$DAILY_DIR/images/" 2>/dev/null || true
cp "$BLOG/output/${DATE}_copy_tool.html" "$DAILY_DIR/copy_tool.html"
ls "$DAILY_DIR/images/"
echo ""

# 4) git add + commit + push
echo "🚀 [4/4] GitHub 푸시..."
git add "${DATE}_blog.md" "${DATE}_seo.md" "${DATE}_sections.json" \
        "daily/$DATE" "images/$DATE" "output/${DATE}_copy_tool.html" 2>&1 | tail -5
git commit -m "feat: ${DATE} 블로그 자동 생성 (v2 — Claude 17:30 인계)" 2>&1 | tail -3 || echo "  (변경 없음)"
git push origin main 2>&1 | tail -5
echo ""

# 5) 알림
if [ -f "$BLOG/.telegram_config" ] && [ -f "$BLOG/notify.py" ]; then
  python3 "$BLOG/notify.py" "<b>✅ ${DATE} 블로그 후처리 완료</b>
PNG · copy_tool · GitHub 푸시 모두 완료
copy_tool: <code>output/${DATE}_copy_tool.html</code>" 2>&1 | tail -3 || true
fi
osascript -e "display notification \"copy_tool 열어서 네이버 발행하세요\" with title \"${DATE} 블로그 후처리 완료\" sound name \"Glass\"" 2>/dev/null || true

# 6) copy_tool 자동 열기
open "$BLOG/output/${DATE}_copy_tool.html" 2>/dev/null || true

echo "✅ 완료 — daily/${DATE}/ · output/${DATE}_copy_tool.html 푸시됨"
echo "(60초 후 자동 닫힘)"
read -t 60 || true
