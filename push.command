#!/bin/bash
# push.command — 범용 푸시 (일회성 _push_*.command 대체, 2026-06-10)
#
# 사용법:
#   더블클릭            → 오늘 날짜 산출물 daily/ 정리 + 푸시
#   bash push.command 2026-06-09            → 해당 날짜 정리 + 푸시
#   bash push.command 2026-06-09 "커밋 메시지"  → 메시지 지정
set -e
cd "$(dirname "$0")"
BASE="$(pwd)"
DATE="${1:-$(date +%Y-%m-%d)}"
MSG="${2:-feat: ${DATE} 블로그 산출물 정리/푸시}"

echo "🧹 stale git lock 정리..."
find .git -maxdepth 1 -name "*.lock" -delete 2>/dev/null || true
find .git -maxdepth 1 -name "*.lock.*" -delete 2>/dev/null || true

# 진행 중이던 머지/리베이스 마무리
if [ -f .git/MERGE_HEAD ]; then
  echo "🔀 진행 중 머지 마무리..."
  git commit --no-edit 2>&1 | tail -2 || true
fi
git rebase --abort 2>/dev/null || true

# daily/ 폴더 정리는 기존 표준 스크립트에 위임
if [ -f "scripts/git_push_daily.sh" ]; then
  bash scripts/git_push_daily.sh "$DATE"
else
  git add -A
  git diff --cached --quiet || git commit -m "$MSG"
  git pull --rebase origin main || true
  git push origin main
fi

echo "🎉 완료"
