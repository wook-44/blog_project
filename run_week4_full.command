#!/bin/bash
# 4월 4주차 전체 처리: HTML → PNG → copy_tool.html
cd "$(dirname "$0")"
BLOG="$(pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4월 4주차 (4/27~4/30) 전체 처리"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: HTML → PNG
echo "🖼️  [1/2] HTML → PNG 변환..."
echo ""
TOTAL=0; OK=0
for d in 2026-04-27 2026-04-28 2026-04-29 2026-04-30; do
  HTML_DIR="$BLOG/images/$d/html"
  OUT_DIR="$BLOG/images/$d"
  [ ! -d "$HTML_DIR" ] && { echo "  ⚠️ $d 없음"; continue; }
  for H in "$HTML_DIR"/${d}-*.html; do
    [ -f "$H" ] || continue
    name=$(basename "$H" .html)
    P="$OUT_DIR/${name}.png"
    TOTAL=$((TOTAL+1))
    "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
      --window-size=1080,1080 --screenshot="$P" "file://$H" 2>/dev/null
    if [ -f "$P" ] && [ "$(stat -f%z "$P" 2>/dev/null)" -gt 5000 ]; then
      echo "  ✅ ${name}.png"
      OK=$((OK+1))
    else
      echo "  ❌ ${name}.png 실패"
    fi
  done
done
echo ""
echo "  PNG: $OK / $TOTAL"
echo ""

# Step 2: copy_tool
echo "📋 [2/2] copy_tool.html 생성..."
echo ""
mkdir -p "$BLOG/output"
for d in 2026-04-27 2026-04-28 2026-04-29 2026-04-30; do
  python3 "$BLOG/scripts/generate_copy_tool.py" "$d" 2>&1 | grep -E "🏷️|저장"
done
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 완료"
ls -1 "$BLOG/output/"2026-04-{27,28,29,30}_copy_tool.html 2>/dev/null
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "엔터로 닫기..." _
