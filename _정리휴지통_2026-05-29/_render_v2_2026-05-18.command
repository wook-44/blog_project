#!/bin/bash
# 2026-05-18-summary 한글 깨진 PNG를 --headless=new로 재변환
cd "$(dirname "$0")"
HTML="$PWD/images/2026-05-18-summary/html/2026-05-18-summary-market.html"
PNG="$PWD/images/2026-05-18-summary/2026-05-18-summary-market.png"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -f "$HTML" ]; then
  echo "❌ HTML 파일 없음: $HTML"
  read -t 30 || true; exit 1
fi

echo "🎨 --headless=new 모드로 재변환..."
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1080,1080 --screenshot="$PNG" "file://$HTML" 2>&1 | tail -5

SIZE=$(stat -f %z "$PNG" 2>/dev/null || stat -c %s "$PNG")
DIM=$(python3 -c "from PIL import Image; img = Image.open('$PNG'); print(f'{img.size[0]}x{img.size[1]}')")
echo ""
echo "✅ PNG: $PNG"
echo "   크기: ${SIZE} bytes, 해상도: ${DIM}"

python3 notify.py "🔧 <b>5/18 시황 PNG 재변환</b>
${SIZE} bytes, ${DIM}
--headless=new 모드 적용으로 한글 폰트 정상화"

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
