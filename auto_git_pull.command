#!/bin/bash
# auto_git_pull.command — 매일 15:00 KST launchd(com.user.blog-autopull)가 실행
# GitHub → 로컬 동기화. Cowork 샌드박스는 github 차단이라 이 pull이 유일한 통로.
# (2026-06-10 재생성 — 원본이 삭제되어 5/27부터 launchd 잡이 실패하고 있었음)
set -o pipefail
cd "$(dirname "$0")"
BLOG="$(pwd)"
LOG="$BLOG/logs/auto_pull_$(date +%Y-%m-%d).log"
mkdir -p "$BLOG/logs"
exec >> "$LOG" 2>&1
echo "── auto pull: $(date '+%Y-%m-%d %H:%M:%S')"

notify() {
  [ -f "$BLOG/.telegram_config" ] && python3 "$BLOG/notify.py" "$1" 2>/dev/null || true
}

# stale lock 정리 (30분 이상) + 샌드박스가 남긴 park 잔해 제거
find "$BLOG/.git" -maxdepth 1 -name "*.lock" -mmin +30 -delete 2>/dev/null
find "$BLOG/.git" -maxdepth 1 -name "*.lock.*" -delete 2>/dev/null
rm -rf "$BLOG/.git/junk_locks" 2>/dev/null
find "$BLOG/.git/refs" -name "*.lock*" -delete 2>/dev/null
# MERGE_AUTOSTASH 잔존 ref 정리 (2026-07-01 pull 연쇄 실패 원인)
rm -f "$BLOG/.git/MERGE_AUTOSTASH" 2>/dev/null
# 샌드박스 세션이 park해 둔 lock 잔해 폴더 정리
rm -rf "$BLOG"/_정리휴지통_*/git_locks 2>/dev/null
if [ -f "$BLOG/.git/index.lock" ]; then
  echo "활성 lock(30분 미만) 존재 — 다른 작업 중으로 보고 종료"
  exit 2
fi

BEFORE=$(git rev-parse HEAD)
if OUT=$(git pull --ff-only origin main 2>&1); then
  echo "$OUT"
  AFTER=$(git rev-parse HEAD)
  if [ "$BEFORE" != "$AFTER" ]; then
    N=$(git diff --name-only "$BEFORE" "$AFTER" | wc -l | tr -d ' ')
    notify "📥 <b>[$(date '+%H:%M') auto-pull]</b> ${BEFORE:0:7}→${AFTER:0:7} (${N}개 파일)"
  fi
else
  echo "$OUT"
  notify "❌ <b>[$(date '+%H:%M') auto-pull 실패]</b>
<pre>$(echo "$OUT" | tail -3 | head -c 400)</pre>"
  exit 1
fi
