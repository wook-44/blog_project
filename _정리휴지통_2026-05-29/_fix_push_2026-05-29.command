#!/bin/bash
# 제목 원제 교체 반영: 락 제거 → copy_tool 재생성(PNG는 이미 있음) → 재푸시
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
LOG="logs/fix_push_2026-05-29.log"
mkdir -p logs
{
  echo "=== START $(date) ==="
  echo "--- stale lock 제거 ---"
  rm -f .git/HEAD.lock .git/index.lock .git/refs/heads/main.lock 2>&1
  ls -la .git/refs/heads/*.lock 2>&1 || echo "lock 없음(정상)"
  echo "--- copy_tool 재생성 (새 제목 반영) ---"
  python3 scripts/generate_copy_tool.py 2026-05-29 2>&1
  echo "--- git_push_daily 재실행 ---"
  bash scripts/git_push_daily.sh 2026-05-29 2>&1
  echo "=== git log -2 ==="
  git log --oneline -2 2>&1
  echo "=== DONE $(date) ==="
} > "$LOG" 2>&1
echo "완료 — 로그: $LOG"
