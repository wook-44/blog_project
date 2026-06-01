#!/bin/bash
# 원격 선행분과 정합: stash(-u) → pull --rebase → push → stash pop
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
LOG="logs/push_rebase_2026-05-29.log"
mkdir -p logs
{
  echo "=== START $(date) ==="
  rm -f .git/HEAD.lock .git/index.lock .git/refs/heads/main.lock 2>&1

  echo "--- 1) 미스테이징/untracked stash ---"
  git stash push -u -m "autofix_2026-05-29 $(date +%H%M)" 2>&1 | tail -3

  echo "--- 2) pull --rebase ---"
  git pull --rebase origin main 2>&1 | tail -8

  echo "--- 3) push ---"
  git push origin main 2>&1 | tail -8

  echo "--- 4) stash 복원 ---"
  git stash pop 2>&1 | tail -5 || echo "(stash 없음 또는 pop 충돌 — 수동 확인)"

  echo "=== git log -3 ==="
  git log --oneline -3 2>&1
  echo "=== DONE $(date) ==="
} > "$LOG" 2>&1
echo "완료 — 로그: $LOG"
