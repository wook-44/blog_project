#!/bin/bash
# 5월 1주차 + 2주차 (5/01 인덱스 + 5/06~5/12 5편) PNG·copy_tool·자동배포
cd "$(dirname "$0")"
BLOG="$(pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  5월 6편 (인덱스 + 5/06~5/12) 전체 처리"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: HTML → PNG
echo "🖼️  [1/2] HTML → PNG 변환..."
TOTAL=0; OK=0
for d in 2026-05-01 2026-05-04 2026-05-05 2026-05-06 2026-05-07 2026-05-08 2026-05-11 2026-05-12 2026-05-13; do
  HTML_DIR="$BLOG/images/$d/html"
  OUT_DIR="$BLOG/images/$d"
  [ ! -d "$HTML_DIR" ] && continue
  for H in "$HTML_DIR"/${d}-*.html; do
    [ -f "$H" ] || continue
    [[ "$H" == *insight* ]] && continue  # insight는 텍스트로만
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

# Step 2: copy_tool
echo ""
echo "📋 [2/2] copy_tool.html 생성..."
mkdir -p "$BLOG/output"
for d in 2026-05-01 2026-05-04 2026-05-05 2026-05-06 2026-05-07 2026-05-08 2026-05-11 2026-05-12 2026-05-13; do
  python3 "$BLOG/scripts/generate_copy_tool.py" "$d" 2>&1 | grep -E "📝|저장"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 처리 완료"
ls -1 "$BLOG/output/"2026-05-{01,04,05,06,07,08,11,12,13}_copy_tool.html 2>/dev/null
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 자동 배포 (Git + Google Drive)
for d in 2026-05-01 2026-05-04 2026-05-05 2026-05-06 2026-05-07 2026-05-08 2026-05-11 2026-05-12 2026-05-13; do
  SKIP_GIT=1 bash "$BLOG/scripts/auto_publish.sh" "$d" "5월 1·2주차 배치" >/dev/null 2>&1
done
bash "$BLOG/scripts/auto_publish.sh" "$(date +%Y-%m-%d)" "5월 1·2주차 배치"

read -p "엔터로 닫기..." _
