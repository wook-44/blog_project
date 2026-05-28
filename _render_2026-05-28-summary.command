#!/bin/bash
# 2026-05-28 시황 요약 인포그래픽 PNG 변환
# Chrome --headless=new 직접 사용 (한글 폰트 정상)
cd "$(dirname "$0")"
HTML="$PWD/images/2026-05-28-summary/html/2026-05-28-summary-market.html"
PNG="$PWD/images/2026-05-28-summary/2026-05-28-summary-market.png"

echo "[render] 2026-05-28-summary market PNG 변환 — --headless=new"
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1080,1080 \
  --screenshot="$PNG" "file://$HTML" 2>&1 | tail -3

SIZE=$(stat -f %z "$PNG" 2>/dev/null || stat -c %s "$PNG")
DIM=$(python3 -c "from PIL import Image; img = Image.open('$PNG'); print(f'{img.size[0]}x{img.size[1]}')" 2>/dev/null)
echo "[render] 완료 → ${PNG} (${SIZE}B, ${DIM})"

if [ -f .telegram_config ] && [ -f notify.py ]; then
  python3 notify.py "🔧 5/28 시황 PNG 변환 완료: ${SIZE}B ${DIM}" 2>/dev/null || true
fi
