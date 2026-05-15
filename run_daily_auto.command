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

START_TS=$(date +%s)

PYTHON="${PYTHON:-/usr/local/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="/opt/homebrew/bin/python3"
[ -x "$PYTHON" ] || PYTHON="$(which python3)"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

notify() {
  # macOS 데스크탑 알림
  /usr/bin/osascript -e "display notification \"$2\" with title \"$1\" sound name \"Glass\"" 2>/dev/null
  # 텔레그램 DM (실패해도 워크플로우 중단 X)
  if [ -f "$BLOG/.telegram_config" ] && [ -f "$BLOG/notify.py" ]; then
    "$PYTHON" "$BLOG/notify.py" "<b>$1</b>
$2" 2>>"$LOG" || true
  fi
}

# 단계 보고용 짧은 텔레그램 메시지 (macOS 알림은 사용 안 함)
tg() {
  if [ -f "$BLOG/.telegram_config" ] && [ -f "$BLOG/notify.py" ]; then
    "$PYTHON" "$BLOG/notify.py" "$1" 2>>"$LOG" || true
  fi
}

# 에러 보고 — 명시적으로 호출 (단계 안에서 실패 감지 시)
report_error() {
  local where="$1"
  local detail="$2"
  local tail_log
  tail_log=$(tail -15 "$LOG" 2>/dev/null | sed -e 's/</\&lt;/g' -e 's/>/\&gt;/g' | tail -c 700)
  tg "❌ <b>오류</b> — ${where}
${detail}
<pre>${tail_log}</pre>"
}

# 비정상 종료 시 자동 보고 (이미 보고된 케이스 중복 방지용 플래그 사용)
EXIT_REPORTED=0
on_exit() {
  local code=$?
  if [ "$code" -ne 0 ] && [ "$EXIT_REPORTED" -eq 0 ]; then
    local tail_log
    tail_log=$(tail -20 "$LOG" 2>/dev/null | sed -e 's/</\&lt;/g' -e 's/>/\&gt;/g' | tail -c 800)
    tg "❌ <b>데일리 자동화 비정상 종료</b> (exit ${code})
<pre>${tail_log}</pre>
로그: <code>${LOG}</code>"
  fi
}
trap on_exit EXIT

tg "🚀 <b>데일리 자동화 시작</b>
${DATE} $(date '+%H:%M:%S')"

# ── ① Git pull (GitHub Actions 결과물 인계) ──────────
echo ""
echo "📥 [1/6] Git pull (GitHub Actions 결과 인계)..."
git -C "$BLOG" pull --rebase origin main 2>&1 || echo "  ⚠️ pull 충돌/실패 — 로컬 상태로 계속"
tg "✅ [1/6] Git pull 완료"

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
tg "✅ [2/6] 본문 확인
<code>$(basename "$POST")</code>"

# ── ③ 인포그래픽 HTML/PNG ────────────────────────────
echo ""
echo "🎨 [3/6] 인포그래픽 생성..."
if ! "$PYTHON" "$BLOG/scripts/regen_week_infographics.py" "$DATE" "$DATE" 2>&1; then
  echo "  ⚠️ HTML 생성 일부 실패"
  report_error "[3/6] 인포그래픽 HTML 생성" "regen_week_infographics.py 실패 — PNG 일부 누락 가능"
fi

PNG_FAIL=0
if [ -x "$CHROME" ]; then
  HTML_DIR="$BLOG/images/$DATE/html"
  if [ -d "$HTML_DIR" ]; then
    for H in "$HTML_DIR"/${DATE}-*.html; do
      [ -f "$H" ] || continue
      name=$(basename "$H" .html)
      P="$BLOG/images/$DATE/${name}.png"
      if ! "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
        --window-size=1080,1080 --screenshot="$P" "file://$H" 2>&1; then
        echo "  ❌ Chrome screenshot 실패: ${name}"
        PNG_FAIL=$((PNG_FAIL + 1))
      else
        echo "  · ${name}.png"
      fi
    done
  fi
else
  echo "  ⚠️ Chrome 없음 — PNG fallback 사용"
  report_error "[3/6] PNG 변환" "Chrome 실행 파일 없음: $CHROME"
fi
PNG_COUNT=$(ls "$BLOG/images/$DATE/"*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$PNG_FAIL" -gt 0 ]; then
  tg "⚠️ [3/6] PNG 생성 ${PNG_COUNT}개 (${PNG_FAIL}개 실패)"
elif [ "$PNG_COUNT" -eq 0 ]; then
  tg "❌ [3/6] PNG 0개 생성됨 — 본문 확인 필요"
else
  tg "✅ [3/6] 인포그래픽 PNG 생성
${PNG_COUNT}개"
fi

# ── ④ 린터 + 시리즈 링커 ─────────────────────────────
echo ""
echo "🔍 [4/6] 린터·시리즈 링커..."
if "$PYTHON" "$BLOG/scripts/agents/00_title_tag_linter.py" "$POST"; then
  tg "✅ [4/6] 린터 통과"
else
  echo "  ⚠️ 린터 미통과 — copy_tool은 만들지만 사용자 검토 권고"
  notify "데일리 자동화 경고" "린터 미통과. $DATE 본문 검토 필요"
  tg "⚠️ [4/6] 린터 미통과 — 본문 검토 권고"
fi
# 시리즈 링커 비활성화 — 네이버에서 마크다운 링크가 깨져 보임
# "$PYTHON" "$BLOG/scripts/agents/09_series_linker.py" "$POST" --apply 2>/dev/null || true

# ── ⑤ copy_tool.html 생성 ────────────────────────────
echo ""
echo "📋 [5/6] copy_tool.html 생성..."
"$PYTHON" "$BLOG/scripts/generate_copy_tool.py" "$DATE" || {
  echo "  ❌ copy_tool 생성 실패"
  notify "데일리 자동화 실패" "copy_tool 생성 실패"
  report_error "[5/6] copy_tool 생성" "generate_copy_tool.py 비정상 종료"
  EXIT_REPORTED=1
  exit 1
}
COPY_TOOL="$BLOG/output/${DATE}_copy_tool.html"
tg "✅ [5/6] copy_tool 생성 완료"

# ── ⑥ 자동 배포 (Git push + Google Drive 미러링) ─────
echo ""
echo "🚀 [6/6] 자동 배포..."
if bash "$BLOG/scripts/auto_publish.sh" "$DATE" "데일리 인계 완료"; then
  tg "✅ [6/6] 자동 배포 완료 (Git + GDrive)"
else
  tg "⚠️ [6/6] 자동 배포 일부 실패 — 로그 확인"
fi

# ── 완료 알림 + copy_tool 자동 열기 ──────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ 데일리 자동화 완료: $(date '+%H:%M:%S')"
echo "  copy_tool: $COPY_TOOL"
echo "════════════════════════════════════════════════════════════════"

notify "12시에 만나요 ${DATE} 준비 완료" "copy_tool 열어서 네이버 발행하세요 (2분)"
[ -f "$COPY_TOOL" ] && /usr/bin/open "$COPY_TOOL"

# 종합 보고 (소요 시간 포함)
END_TS=$(date +%s)
ELAPSED=$(( END_TS - START_TS ))
tg "🎉 <b>데일리 자동화 전체 완료</b>
${DATE} 소요 ${ELAPSED}초
copy_tool 열렸으니 네이버 발행만 남았습니다."
