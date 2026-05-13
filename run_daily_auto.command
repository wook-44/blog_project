#!/bin/bash
# run_daily_auto.command — 매일 자동 실행되는 무인 데일리 entrypoint
#  발행(네이버/티스토리/브런치)은 건너뜀. copy_tool.html까지 만들고 정지.
#  ① 새 영상 감지  ② 자막 추출  ③ 본문 작성  ④ PNG 15장  ⑤ 린터/게이트
#  ⑥ copy_tool.html  ⑦ Git push  ⑧ macOS 알림
#
# launchd에서 호출됨. 출력 로그는 logs/daily_auto_{YYYY-MM-DD}.log

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
echo "  데일리 무인 실행: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "════════════════════════════════════════════════════════════════"

# API 키 로드 (.env 우선)
if [ -f "$BLOG/.env" ]; then
  set -a
  source "$BLOG/.env"
  set +a
fi

PYTHON="${PYTHON:-/usr/local/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="/opt/homebrew/bin/python3"
[ -x "$PYTHON" ] || PYTHON="$(which python3)"

notify() {
  /usr/bin/osascript -e "display notification \"$2\" with title \"$1\" sound name \"Glass\"" 2>/dev/null
}

# ── ① 새 영상 감지 ───────────────────────────────────
echo ""
echo "🎬 [1/7] 새 영상 체크..."
NEW_VIDEO_JSON=""
if [ -f "$BLOG/scripts/check_playlist.py" ] && [ -n "$YOUTUBE_API_KEY" ]; then
  "$PYTHON" "$BLOG/scripts/check_playlist.py" --output "$BLOG/data/new_videos.csv" 2>&1
  if [ -s "$BLOG/data/new_videos.csv" ]; then
    NEW_VIDEO_URL=$(tail -1 "$BLOG/data/new_videos.csv" | awk -F',' '{print $3}')
    echo "  ✅ 새 영상: $NEW_VIDEO_URL"
  else
    echo "  ℹ️  새 영상 없음 — 종료"
    notify "12시에 만나요 데일리" "오늘은 새 영상 없음 ($DATE)"
    exit 0
  fi
else
  echo "  ⚠️  YOUTUBE_API_KEY 미설정 또는 check_playlist.py 없음 — 종료"
  notify "데일리 자동화" "YOUTUBE_API_KEY 미설정. .env 확인 필요"
  exit 1
fi

# ── ② 자막 추출 ──────────────────────────────────────
echo ""
echo "📝 [2/7] 자막 추출..."
"$PYTHON" "$BLOG/scripts/get_youtube_transcript.py" "$NEW_VIDEO_URL" "$DATE" || {
  echo "  ❌ 자막 추출 실패"
  notify "데일리 자동화 실패" "자막 추출 실패 — 영상 비공개/자막 없음 가능"
  exit 1
}

# ── ③ 본문 작성 (Agent 03) ───────────────────────────
echo ""
echo "✍️  [3/7] 블로그 본문 작성..."
TRANSCRIPT="$BLOG/data/transcripts/${DATE}_transcript.txt"
if [ -f "$BLOG/scripts/agents/03_blog_writer.py" ] && [ -n "$GEMINI_API_KEY" ]; then
  "$PYTHON" "$BLOG/scripts/agents/03_blog_writer.py" --transcript "$TRANSCRIPT" --date "$DATE" --tone-book "$BLOG/stock-youtube-blog-writer/references/tone-book.md" || {
    echo "  ❌ 본문 작성 실패"
    notify "데일리 자동화 실패" "Agent 03 본문 작성 실패"
    exit 1
  }
else
  echo "  ⚠️  03_blog_writer.py 또는 GEMINI_API_KEY 부재"
  notify "데일리 자동화 실패" "본문 작성 에이전트/API 키 부재"
  exit 1
fi

# ── ④ 인포그래픽 PNG 15장 (3종) ──────────────────────
echo ""
echo "🎨 [4/7] 인포그래픽 생성..."
"$PYTHON" "$BLOG/scripts/regen_week_infographics.py" "$DATE" "$DATE" 2>&1
# Chrome으로 PNG 변환 — html 폴더의 모든 HTML 가변 처리
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
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

# ── ⑤ 린터 + 시리즈 링커 + 품질 게이트 ───────────────
echo ""
echo "🔍 [5/7] 린터/게이트 통과 검증..."
POST=$(ls -t "$BLOG"/${DATE}-*.md 2>/dev/null | grep -v bak | head -1)
"$PYTHON" "$BLOG/scripts/agents/00_title_tag_linter.py" "$POST" --strict || {
  echo "  ❌ 린터 미통과 — copy_tool은 만들지만 알림으로 수동 검토 권고"
  notify "데일리 자동화 경고" "린터 미통과. $DATE 본문 검토 필요"
}
"$PYTHON" "$BLOG/scripts/agents/09_series_linker.py" "$POST" --apply 2>/dev/null || true

# ── ⑥ copy_tool.html 생성 ────────────────────────────
echo ""
echo "📋 [6/7] copy_tool.html 생성..."
"$PYTHON" "$BLOG/scripts/generate_copy_tool.py" "$DATE" || {
  echo "  ❌ copy_tool 생성 실패"
  notify "데일리 자동화 실패" "copy_tool 생성 실패"
  exit 1
}
COPY_TOOL="$BLOG/output/${DATE}_copy_tool.html"

# ── ⑦ 자동 배포 (Git + Google Drive) ─────────────────
echo ""
echo "🚀 [7/7] 자동 배포 (Git push + Google Drive 미러링)..."
bash "$BLOG/scripts/auto_publish.sh" "$DATE" "데일리 자동 생성"

# ── 완료 알림 ────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ 데일리 자동화 완료: $(date '+%H:%M:%S')"
echo "  copy_tool: $COPY_TOOL"
echo "════════════════════════════════════════════════════════════════"

notify "12시에 만나요 ${DATE} 준비 완료" "copy_tool 열어서 네이버 발행하세요 (2분)"

# copy_tool 자동으로 열어서 바로 발행 시작할 수 있게
[ -f "$COPY_TOOL" ] && /usr/bin/open "$COPY_TOOL"
