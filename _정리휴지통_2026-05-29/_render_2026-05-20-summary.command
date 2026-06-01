#!/bin/bash
# 2026-05-20 시황 요약 인포그래픽 PNG 변환 (한글 폰트 정상)
cd "$(dirname "$0")"
HTML="$PWD/images/html/2026-05-20-summary-market.html"
PNG="$PWD/images/2026-05-20-summary/2026-05-20-summary-market.png"

echo "[render] 2026-05-20-summary market PNG 변환 — --headless=new"
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1080,1080 \
  --screenshot="$PNG" "file://$HTML" 2>&1 | tail -3

SIZE=$(stat -f %z "$PNG" 2>/dev/null || stat -c %s "$PNG")
DIM=$(python3 -c "from PIL import Image; img = Image.open('$PNG'); print(f'{img.size[0]}x{img.size[1]}')" 2>/dev/null)
echo "[render] 완료 → ${PNG} (${SIZE}B, ${DIM})"

# 텔레그램 보고 (있을 때만)
if [ -f .telegram_config ] && [ -f notify.py ]; then
  python3 notify.py "🔧 <b>5/20 시황 PNG 재변환</b>
${SIZE}B, ${DIM}
--headless=new — 한글 폰트 정상화" 2>/dev/null || true
fi

read -p "Enter to close..."
