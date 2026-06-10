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

# 1-a. stale lock 정리 (샌드박스 세션이 남긴 lock은 Mac에서만 삭제 가능)
#      - index.lock 등 진짜 lock: 5분 이상 지난 것만 stale로 간주하고 삭제
#      - *.lock.bak* / *.lock.stale* / *.lock.p* 등 park 잔해: 무조건 삭제
find "$BLOG/.git" -maxdepth 1 -name "*.lock" -mmin +5 -delete 2>/dev/null
find "$BLOG/.git" -maxdepth 1 -name "*.lock.*" -delete 2>/dev/null

# 1-b. pull (실패 시 lock 재정리 후 1회 재시도, 그래도 실패면 원인 보고)
PULL_OUT=$(git -C "$BLOG" pull --rebase origin main 2>&1)
PULL_RC=$?
echo "$PULL_OUT"
if [ $PULL_RC -ne 0 ]; then
  echo "  ⚠️ pull 실패 — lock 정리 후 재시도..."
  rm -f "$BLOG/.git/index.lock" "$BLOG/.git/HEAD.lock" 2>/dev/null
  git -C "$BLOG" rebase --abort 2>/dev/null
  PULL_OUT=$(git -C "$BLOG" pull --rebase origin main 2>&1)
  PULL_RC=$?
  echo "$PULL_OUT"
fi
if [ $PULL_RC -ne 0 ]; then
  report_error "[1/6] Git pull" "재시도 후에도 실패 — 로컬 상태로 계속 진행
원인: $(echo "$PULL_OUT" | head -3 | tr '\n' ' ' | head -c 300)"
else
  tg "✅ [1/6] Git pull 완료"
fi

# ── ② 오늘 본문 확인 ─────────────────────────────────
echo ""
echo "📝 [2/6] 오늘 본문 확인..."
# ${DATE}_blog.md (Actions v2 산출물) 우선, 없으면 구형 ${DATE}-슬러그.md 탐색
POST=$(ls -t "$BLOG"/${DATE}_blog.md "$BLOG"/${DATE}-*.md 2>/dev/null | grep -v bak | grep -v summary | head -1)
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

# PNG가 깨졌다고 판단하는 최소 크기(byte). 정상 인포그래픽은 280~550KB.
# 100KB 미만이면 한글 글리프 누락/Chrome 렌더 실패로 간주.
MIN_PNG_BYTES=100000

PNG_FAIL=0
HTML_DIR="$BLOG/images/$DATE/html"

if [ ! -x "$CHROME" ]; then
  echo "  ❌ Chrome 실행 파일 없음: $CHROME — PNG 변환 불가"
  report_error "[3/6] PNG 변환" "Chrome 실행 파일 없음: $CHROME"
  EXIT_REPORTED=1
  exit 1
fi

if [ ! -d "$HTML_DIR" ]; then
  echo "  ❌ HTML 디렉터리 없음: $HTML_DIR — 인포그래픽 HTML 미생성"
  report_error "[3/6] PNG 변환" "HTML 디렉터리 없음 ($HTML_DIR). regen_week_infographics.py 산출물 확인 필요"
  EXIT_REPORTED=1
  exit 1
fi

# ③-a 폰트 강제(fortify): Chrome headless 폰트 상속 실패로 인한 한글 깨짐 방지.
#   모든 <text>에 font-family 직접 명시. 렌더 직전 필수 단계.
echo "  🔤 폰트 강제(fortify) 적용..."
if ! "$PYTHON" "$BLOG/scripts/fortify_html_fonts.py" "$HTML_DIR"/${DATE}-*.html 2>&1; then
  echo "  ⚠️ fortify 실패 — 한글 깨짐 위험 있으나 렌더는 시도"
  report_error "[3/6] fortify" "fortify_html_fonts.py 실패 — 한글 깨짐 가능"
fi

# ③-b Chrome headless 렌더 + 크기 검증
for H in "$HTML_DIR"/${DATE}-*.html; do
  [ -f "$H" ] || continue
  name=$(basename "$H" .html)
  P="$BLOG/images/$DATE/${name}.png"
  rm -f "$P"
  if ! "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size=1080,1080 --screenshot="$P" "file://$H" 2>&1; then
    echo "  ❌ Chrome screenshot 실패: ${name}"
    PNG_FAIL=$((PNG_FAIL + 1))
    continue
  fi
  # 크기 검증 — 100KB 미만이면 깨짐 의심
  sz=$(stat -f%z "$P" 2>/dev/null || stat -c%s "$P" 2>/dev/null || echo 0)
  if [ ! -f "$P" ] || [ "$sz" -lt "$MIN_PNG_BYTES" ]; then
    echo "  ❌ ${name}.png 비정상 크기 ${sz}B (<${MIN_PNG_BYTES}B) — 깨짐 의심"
    PNG_FAIL=$((PNG_FAIL + 1))
  else
    echo "  · ${name}.png (${sz}B)"
  fi
done

PNG_COUNT=$(ls "$BLOG/images/$DATE/"${DATE}-*.png 2>/dev/null | wc -l | tr -d ' ')

# ③-c 배포 차단 게이트: 깨졌거나 0장이면 copy_tool·push로 넘어가지 않고 중단.
#   silent failure로 망가진 PNG가 GitHub 푸시까지 흘러가던 문제 차단.
if [ "$PNG_COUNT" -eq 0 ]; then
  echo "  🛑 PNG 0장 — 배포 중단"
  report_error "[3/6] PNG 게이트" "PNG 0장 생성됨. fortify/HTML/Chrome 환경 점검 필요. 배포 중단."
  EXIT_REPORTED=1
  exit 1
fi
if [ "$PNG_FAIL" -gt 0 ]; then
  echo "  🛑 깨진/누락 PNG ${PNG_FAIL}개 — 배포 중단"
  report_error "[3/6] PNG 게이트" "깨지거나 누락된 PNG ${PNG_FAIL}개 (정상 ${PNG_COUNT}개). 망가진 결과물 푸시 방지 위해 배포 중단. 수동 점검 후 재실행 필요."
  EXIT_REPORTED=1
  exit 1
fi
tg "✅ [3/6] 인포그래픽 PNG 생성
${PNG_COUNT}개 (크기 검증 통과)"

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
