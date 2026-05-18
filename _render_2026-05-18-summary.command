#!/bin/bash
# 2026-05-18 시황 요약 인포그래픽 PNG 재변환 (한글 폰트 정상 적용)
cd "$(dirname "$0")"
echo "[render] 2026-05-18-summary market PNG 재변환 시작"
python3 svg-to-png/references/svg_to_png.py \
  --input "images/2026-05-18-summary/html/2026-05-18-summary-market.html" \
  --output "images/2026-05-18-summary/2026-05-18-summary-market.png" \
  --width 1080 --height 1080 2>&1 || true

# Chrome headless 직접 실행 fallback
if [ ! -s "images/2026-05-18-summary/2026-05-18-summary-market.png" ] || [ $(stat -f%z "images/2026-05-18-summary/2026-05-18-summary-market.png" 2>/dev/null || echo 0) -lt 50000 ]; then
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --headless --disable-gpu \
    --window-size=1080,1080 \
    --screenshot="$PWD/images/2026-05-18-summary/2026-05-18-summary-market.png" \
    "file://$PWD/images/2026-05-18-summary/html/2026-05-18-summary-market.html"
fi
echo "[render] 완료 → images/2026-05-18-summary/"
read -p "Enter to close..."
