#!/bin/bash
# 2026-05-18 블로그 인포그래픽 PNG 변환 + 복붙 도구 재생성 + GitHub 푸시
# 샌드박스에서 PNG/git push가 불가능해 Mac 환경에서 일괄 처리

set -e
cd "$(dirname "$0")"
TODAY="2026-05-18"
HTML_DIR="$PWD/images/$TODAY/html"
OUT_DIR="$PWD/images/$TODAY"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -d "$HTML_DIR" ]; then
  echo "❌ HTML 폴더 없음: $HTML_DIR"
  read -t 30 || true; exit 1
fi

echo "🗓️  ${TODAY} 블로그 후처리 시작"
echo "================================"
echo ""

# 1) HTML → PNG 변환 (Chrome --headless=new)
echo "🎨 [1/3] 인포그래픽 HTML → PNG 변환..."
for HTML in "$HTML_DIR"/*.html; do
  BASE=$(basename "$HTML" .html)
  PNG="$OUT_DIR/$BASE.png"
  echo "   ▶ $BASE.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size=1080,1080 --screenshot="$PNG" "file://$HTML" 2>&1 | tail -1 || true
done
ls -lh "$OUT_DIR"/*.png 2>/dev/null | tail -5
echo ""

# 2) PNG 포함하여 복붙 도구 재생성
echo "📄 [2/3] HTML 복붙 도구 재생성 (이미지 포함)..."
python3 scripts/generate_copy_tool.py "$TODAY" 2>&1 | tail -5
echo ""

# 3) git push
echo "🚀 [3/3] GitHub 푸시..."
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
bash scripts/git_push_daily.sh "$TODAY" 2>&1 | tail -10
echo ""

echo "✅ 완료 — daily/${TODAY}/ 및 output/${TODAY}_copy_tool.html 푸시됨"
echo "(60초 후 자동 닫힘)"
read -t 60 || true
