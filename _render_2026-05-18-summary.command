#!/bin/bash
# 2026-05-18 시황 요약 인포그래픽 PNG 변환 (한글 폰트 정상)
# 2026-05-18 patch: svg_to_png.py 우회, Chrome --headless=new 직접 사용
#   - 옛 --headless 모드는 한글 글리프 빠지는 문제 있음 (1125×1125 + 한글 사라짐 사례)
#   - --headless=new는 시스템 폰트 정상 로드, 정확히 1080×1080
cd "$(dirname "$0")"
HTML="$PWD/images/2026-05-18-summary/html/2026-05-18-summary-market.html"
PNG="$PWD/images/2026-05-18-summary/2026-05-18-summary-market.png"

echo "[render] 2026-05-18-summary market PNG 변환 — --headless=new"
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1080,1080 \
  --screenshot="$PNG" "file://$HTML" 2>&1 | tail -3

SIZE=$(stat -f %z "$PNG" 2>/dev/null || stat -c %s "$PNG")
DIM=$(python3 -c "from PIL import Image; img = Image.open('$PNG'); print(f'{img.size[0]}x{img.size[1]}')" 2>/dev/null)
echo "[render] 완료 → ${PNG} (${SIZE}B, ${DIM})"

# 텔레그램 보고 (있을 때만)
if [ -f .telegram_config ] && [ -f notify.py ]; then
  python3 notify.py "🔧 <b>5/18 시황 PNG 재변환</b>
${SIZE}B, ${DIM}
--headless=new — 한글 폰트 정상화" 2>/dev/null || true
fi

read -p "Enter to close..."
