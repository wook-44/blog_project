#!/bin/bash
# 4월 3주차(4/20~4/24) 인포그래픽 PNG 일괄 변환
# Chrome headless로 images/{date}/html/*.html → images/{date}/{date}-*.png

set -e
cd "$(dirname "$0")"

BLOG="$(pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -x "$CHROME" ]; then
  echo "❌ Chrome 없음: $CHROME"
  read -p "엔터로 닫기..." _
  exit 1
fi

echo "🖼️  4월 3주차 인포그래픽 PNG 변환 시작..."
echo ""

TOTAL=0
SUCCESS=0
for d in 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24; do
  HTML_DIR="$BLOG/images/$d/html"
  OUT_DIR="$BLOG/images/$d"
  [ ! -d "$HTML_DIR" ] && { echo "  ⚠️  $d 폴더 없음 — 스킵"; continue; }

  for kind in market psychology summary; do
    HTML="$HTML_DIR/${d}-${kind}.html"
    PNG="$OUT_DIR/${d}-${kind}.png"
    [ ! -f "$HTML" ] && continue
    TOTAL=$((TOTAL+1))
    "$CHROME" \
      --headless=new \
      --disable-gpu \
      --hide-scrollbars \
      --window-size=900,900 \
      --screenshot="$PNG" \
      "file://$HTML" 2>/dev/null
    if [ -f "$PNG" ] && [ "$(stat -f%z "$PNG" 2>/dev/null || stat -c%s "$PNG")" -gt 5000 ]; then
      echo "  ✅ $(basename $PNG)"
      SUCCESS=$((SUCCESS+1))
    else
      echo "  ❌ $(basename $PNG) 실패"
    fi
  done
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  완료: $SUCCESS / $TOTAL"
echo "  저장 위치: $BLOG/images/2026-04-{20..24}/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "엔터로 닫기..." _
