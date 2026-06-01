#!/bin/bash
# 2026-05-14 5장 인포그래픽 샘플 — 3~5 가변 룰 검증용
# 이미 HTML 5개는 sandbox에서 생성됨. 여기선 Chrome headless로 PNG만 변환.

cd "$(dirname "$0")"
DATE="2026-05-14"
HTML_DIR="images/$DATE/html"
PNG_DIR="images/$DATE"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -x "$CHROME" ]; then
  echo "❌ Chrome 실행 파일 없음: $CHROME"
  echo "엔터로 창 닫기..."
  read
  exit 1
fi

echo "🎨 2026-05-14 인포그래픽 PNG 변환 시작..."
echo ""

OK=0; FAIL=0
for H in "$HTML_DIR"/${DATE}-*.html; do
  [ -f "$H" ] || continue
  name=$(basename "$H" .html)
  P="$PNG_DIR/${name}.png"
  if "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size=1080,1080 --screenshot="$P" "file://$(pwd)/$H" 2>/dev/null; then
    size=$(stat -f %z "$P" 2>/dev/null || stat -c %s "$P")
    echo "  ✅ ${name}.png  (${size} bytes)"
    OK=$((OK+1))
  else
    echo "  ❌ ${name}.png  변환 실패"
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "════════════════════════════════════"
echo "  성공 $OK / 실패 $FAIL"
echo "════════════════════════════════════"
echo ""
ls -lh "$PNG_DIR"/${DATE}-*.png

# 텔레그램 보고 (있을 때만)
if [ -f .telegram_config ] && [ -f notify.py ]; then
  python3 notify.py "📸 <b>5/14 5장 샘플 변환 완료</b>
성공 $OK / 실패 $FAIL
images/$DATE/ 폴더 확인"
fi

echo ""
echo "엔터로 창 닫기..."
read
