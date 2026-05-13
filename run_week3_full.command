#!/bin/bash
# 4월 3주차 전체 처리: HTML → PNG → copy_tool.html
# 개별 단계 실패해도 끝까지 진행 (set -e 제거)
cd "$(dirname "$0")"
BLOG="$(pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4월 3주차 (4/20~4/24) 전체 처리"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: HTML → PNG (Chrome headless)
echo "🖼️  [1/2] HTML → PNG 변환 중..."
echo ""
TOTAL=0; OK=0
for d in 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24; do
  HTML_DIR="$BLOG/images/$d/html"
  OUT_DIR="$BLOG/images/$d"
  [ ! -d "$HTML_DIR" ] && { echo "  ⚠️  $d 폴더 없음"; continue; }
  for kind in market psychology summary; do
    H="$HTML_DIR/${d}-${kind}.html"
    P="$OUT_DIR/${d}-${kind}.png"
    [ ! -f "$H" ] && continue
    TOTAL=$((TOTAL+1))
    "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
      --window-size=1080,1080 --screenshot="$P" "file://$H" 2>/dev/null
    if [ -f "$P" ] && [ "$(stat -f%z "$P" 2>/dev/null)" -gt 5000 ]; then
      echo "  ✅ ${d}-${kind}.png"
      OK=$((OK+1))
    else
      echo "  ❌ ${d}-${kind}.png 실패"
    fi
  done
done
echo ""
echo "  PNG 결과: $OK / $TOTAL"
echo ""

# Step 2: copy_tool.html 생성
echo "📋 [2/2] 복붙용 copy_tool.html 생성 중..."
echo ""
mkdir -p "$BLOG/output"
GEN_OK=0
for d in 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24; do
  if python3 "$BLOG/scripts/generate_copy_tool.py" "$d" 2>&1 | tail -3; then
    GEN_OK=$((GEN_OK+1))
  fi
done
echo ""
echo "  copy_tool 결과: $GEN_OK / 5"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 처리 완료. 결과물:"
echo ""
ls -1 "$BLOG/output/"2026-04-{20,21,22,23,24}*_copy_tool.html 2>/dev/null | while read f; do
  echo "    📄 $f"
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 자동 배포 (Git + Google Drive) — 4주차분 일괄
for d in 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24; do
  SKIP_GIT=1 bash "$BLOG/scripts/auto_publish.sh" "$d" "4월 3주차 배치" >/dev/null 2>&1
done
bash "$BLOG/scripts/auto_publish.sh" "$(date +%Y-%m-%d)" "4월 3주차 배치"

read -p "엔터로 닫기..." _
