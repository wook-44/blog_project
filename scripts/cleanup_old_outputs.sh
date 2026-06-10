#!/bin/bash
# cleanup_old_outputs.sh — 오래된 재생성 가능 산출물 정리 (2026-06-10 신설)
# 대상 (모두 daily/ 에 정본이 보관된 재생성 가능 파일):
#   - output/   : 30일 지난 copy_tool HTML
#   - images/   : 30일 지난 날짜 폴더 (PNG/HTML 작업본)
#   - logs/     : 60일 지난 로그
# 삭제하지 않고 _정리휴지통_YYYY-MM-DD/ 로 이동 (확인 후 직접 비우면 됨)
#
# 사용법: bash scripts/cleanup_old_outputs.sh [보관일수, 기본 30]
set -e
BASE="$(cd "$(dirname "$0")/.." && pwd)"
DAYS="${1:-30}"
TRASH="$BASE/_정리휴지통_$(date +%Y-%m-%d)"
mkdir -p "$TRASH/output" "$TRASH/images" "$TRASH/logs"

echo "🧹 ${DAYS}일 지난 산출물 → $(basename "$TRASH")/"

# mtime은 일괄 재생성 시 갱신되어 부정확 → 파일명의 YYYY-MM-DD 날짜로 판단
if date -v-1d >/dev/null 2>&1; then
  CUTOFF=$(date -v-${DAYS}d +%Y-%m-%d)   # macOS
  LOG_CUTOFF=$(date -v-60d +%Y-%m-%d)
else
  CUTOFF=$(date -d "-${DAYS} days" +%Y-%m-%d)  # Linux
  LOG_CUTOFF=$(date -d "-60 days" +%Y-%m-%d)
fi
echo "  기준일: $CUTOFF 이전 (로그는 $LOG_CUTOFF 이전)"

move_old() {  # $1=검색폴더 $2=휴지통하위 $3=기준일
  local item d
  for item in "$1"/20*; do
    [ -e "$item" ] || continue
    d=$(basename "$item" | grep -oE '^20[0-9]{2}-[0-9]{2}-[0-9]{2}') || continue
    if [ -n "$d" ] && [ "$d" \< "$3" ]; then
      mv "$item" "$2/" && echo "  → $(basename "$item")"
    fi
  done
  return 0
}
move_old "$BASE/output" "$TRASH/output" "$CUTOFF"
move_old "$BASE/images" "$TRASH/images" "$CUTOFF"
move_old "$BASE/images/html" "$TRASH/images" "$CUTOFF" 2>/dev/null || true
move_old "$BASE/logs" "$TRASH/logs" "$LOG_CUTOFF"
for f in "$BASE/logs"/daily_auto_20*.log; do
  [ -e "$f" ] || continue
  d=$(basename "$f" | grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}')
  [ -n "$d" ] && [ "$d" \< "$LOG_CUTOFF" ] && mv "$f" "$TRASH/logs/"
done

# 빈 휴지통 하위 폴더 정리
rmdir "$TRASH/output" "$TRASH/images" "$TRASH/logs" "$TRASH" 2>/dev/null || true

echo "✅ 완료. 현재 용량:"
du -sh "$BASE/output" "$BASE/images" "$BASE/logs" 2>/dev/null
