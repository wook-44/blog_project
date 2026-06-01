#!/bin/bash
# _regen_2026-05-28.command
# 5/28 인포그래픽 PNG 3장 + copy_tool HTML 재생성 (한글 깨짐 수정용, git push 없음)

set -e
cd "$(dirname "$0")"
BLOG="$(pwd)"
DATE="2026-05-28"
HTML_DIR="$BLOG/images/$DATE/html"
OUT_DIR="$BLOG/images/$DATE"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📅  ${DATE} 인포 PNG + copy_tool 재생성"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1) HTML 폰트 보강 (모든 <text>에 font-family 직접 명시)
echo ""
echo "🔧 [1/3] HTML 폰트 보강..."
python3 scripts/fortify_html_fonts.py \
  "$HTML_DIR/${DATE}-market.html" \
  "$HTML_DIR/${DATE}-psychology.html" \
  "$HTML_DIR/${DATE}-summary.html"

# 2) Chrome headless로 PNG 변환
echo ""
echo "🎨 [2/3] Chrome headless PNG 변환..."
for HTML in "$HTML_DIR"/${DATE}-{market,psychology,summary}.html; do
  [ -f "$HTML" ] || continue
  BASE=$(basename "$HTML" .html)
  PNG="$OUT_DIR/$BASE.png"
  echo "   ▶ $BASE.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size=1080,1080 --screenshot="$PNG" "file://$HTML" 2>&1 | tail -1 || true
done
echo ""
ls -lh "$OUT_DIR"/${DATE}-{market,psychology,summary}.png 2>/dev/null

# 3) copy_tool HTML 재생성 (PNG base64 embed)
echo ""
echo "📄 [3/3] copy_tool HTML 재생성..."
python3 scripts/generate_copy_tool.py "$DATE" 2>&1 | tail -10
echo ""

# 4) 알림 + 자동 열기
if [ -f "$BLOG/.telegram_config" ] && [ -f "$BLOG/notify.py" ]; then
  python3 "$BLOG/notify.py" "<b>✅ ${DATE} 인포 PNG·copy_tool 재생성 완료</b>" 2>&1 | tail -3 || true
fi
osascript -e "display notification \"copy_tool 열기\" with title \"${DATE} 재생성 완료\" sound name \"Glass\"" 2>/dev/null || true
open "$BLOG/output/${DATE}_copy_tool.html" 2>/dev/null || true

echo "✅ 완료 — output/${DATE}_copy_tool.html"
echo "(60초 후 자동 닫힘)"
read -t 60 || true
