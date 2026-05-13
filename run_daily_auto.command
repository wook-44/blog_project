#!/bin/bash
# run_daily_auto.command — 17:30 KST 무인 인계 실행
#   GitHub Actions(17:00)가 영상 체크 + 본문 작성 후 push 완료한 직후 실행됨.
#   Mac은 git pull로 결과물 받아 PNG + copy_tool 만들고 Git/GDrive 미러링.
#
#  ① git pull  ② 본문 .md 확인  ③ 인포그래픽 PNG  ④ 린터·시리즈링커
#  ⑤ copy_tool  ⑥ auto_publish (Git push + GDrive 미러링)  ⑦ macOS 알림

cd "$(dirname "$0")"
BLOG="$(pwd)"
DATE="$(date +%Y-%m-%d)"
LOG_DIR="$BLOG/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily_auto_${DATE}.log"

# 모든 출력을 로그로
exec >> "$LOG" 2>&1

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  데일리 무인 인계: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "════════════════════════════════════════════════════════════════"

# API 키 로드 (.env 우선)
if [ -f "$BLOG/.env" ]; then set -a; source "$BLOG/.env"; set +a; fi

PYTHON="${PYTHON:-/usr/local/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="/opt/homebrew/bin/python3"
[ -x "$PYTHON" ] || PYTHON="$(which python3)"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

notify() {
  /usr/bin/osascript -e "display notification \"$2\" with title \"$1\" sound name \"Glass\"" 2>/dev/null
}

# ── ① Git pull (GitHub Actions 결과물 인계) ──────────
echo ""
echo "📥 [1/6] Git pull (GitHub Actions 결과 인계)..."
git -C "$BLOG" pull --rebase origin main 2>&1 || echo "  ⚠️ pull 충돌/실패 — 로컬 상태로 계속"

# ── ② 오늘 본문 확인 ─────────────────────────────────
echo ""
echo "📝 [2/6] 오늘 본문 확인..."
POST=$(ls -t "$BLOG"/${DATE}-*.md 2>/dev/null | grep -v bak | head -1)
if [ -z "$POST" ]; then
  echo "  ℹ️  오늘 본문 없음. GitHub Actions가 새 영상을 못 찾았거나 아직 미완료."
  notify "12시에 만나요 ${DATE}" "오늘은 새 영상 없음 또는 GitHub Actions 미완료"
  exit 0
fi
echo "  ✅ 본문: $(basename "$POST")"

# ── ③ 인포그래픽 HTML/PNG ────────────────────────────
echo ""
echo "🎨 [3/6] 인포그래픽 생성..."
"$PYTHON" "$BLOG/scripts/regen_week_infographics.py" "$DATE" "$DATE" 2>&1 || echo "  ⚠️ HTML 생성 일부 실패"

if [ -x "$CHROME" ]; then
  HTML_DIR="$BLOG/images/$DATE/html"
  if [ -d "$HTML_DIR" ]; then
    for H in "$HTML_DIR"/${DATE}-*.html; do
      [ -f "$H" ] || continue
      name=$(basename "$H" .html)
      P="$BLOG/images/$DATE/${name}.png"
      "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
        --window-size=1080,1080 --screenshot="$P" "file://$H" 2>/dev/null
      echo "  · ${name}.png"
    done
  fi
else
  echo "  ⚠️ Chrome 없음 — PNG fallback 사용"
fi

# ── ④ 린터 + 시리즈 링커 ─────────────────────────────
echo ""
echo "🔍 [4/6] 린터·시리즈 링커..."
"$PYTHON" "$BLOG/scripts/agents/00_title_tag_linter.py" "$POST" || {
  echo "  ⚠️ 린터 미통과 — copy_tool은 만들지만 사용자 검토 권고"
  notify "데일리 자동화 경고" "린터 미통과. $DATE 본문 검토 필요"
}
"$PYTHON" "$BLOG/scripts/agents/09_series_linker.py" "$POST" --apply 2>/dev/null || true

# ── ⑤ copy_tool.html 생성 ────────────────────────────
echo ""
echo "📋 [5/6] copy_tool.html 생성..."
"$PYTHON" "$BLOG/scripts/generate_copy_tool.py" "$DATE" || {
  echo "  ❌ copy_tool 생성 실패"
  notify "데일리 자동화 실패" "copy_tool 생성 실패"
  exit 1
}
COPY_TOOL="$BLOG/output/${DATE}_copy_tool.html"

# ── ⑥ 자동 배포 (Git push + Google Drive 미러링) ─────
echo ""
echo "🚀 [6/6] 자동 배포..."
bash "$BLOG/scripts/auto_publish.sh" "$DATE" "데일리 인계 완료"

# ── 완료 알림 + copy_tool 자동 열기 ──────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ 데일리 자동화 완료: $(date '+%H:%M:%S')"
echo "  copy_tool: $COPY_TOOL"
echo "════════════════════════════════════════════════════════════════"

notify "12시에 만나요 ${DATE} 준비 완료" "copy_tool 열어서 네이버 발행하세요 (2분)"
[ -f "$COPY_TOOL" ] && /usr/bin/open "$COPY_TOOL"
