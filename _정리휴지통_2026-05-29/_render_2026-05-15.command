#!/bin/bash
# 5/15 인포그래픽 PNG 변환 + copy_tool 생성
cd "$(dirname "$0")"
DATE="2026-05-15"
HTML_DIR="images/$DATE/html"
PNG_DIR="images/$DATE"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -x "$CHROME" ]; then
  echo "❌ Chrome 없음"
  read -t 60 || true
  exit 1
fi

echo "🎨 PNG 변환..."
OK=0; FAIL=0
for H in "$HTML_DIR"/${DATE}-*.html; do
  [ -f "$H" ] || continue
  name=$(basename "$H" .html)
  P="$PNG_DIR/${name}.png"
  if "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size=1080,1080 --screenshot="$P" "file://$(pwd)/$H" 2>/dev/null; then
    size=$(stat -f %z "$P" 2>/dev/null || stat -c %s "$P")
    echo "  ✅ ${name}.png  (${size} bytes)"
    OK=$((OK+1))
  else
    echo "  ❌ ${name}.png"
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "📋 copy_tool 생성..."
python3 scripts/generate_copy_tool.py $DATE 2>&1 | tail -15

echo ""
ls -lh output/${DATE}_copy_tool.html 2>/dev/null

python3 notify.py "📸 <b>5/15 PNG·copy_tool 완료</b>
PNG 성공 ${OK} / 실패 ${FAIL}
output/${DATE}_copy_tool.html"

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
