#!/bin/bash
# 2026-05-29 자동: PNG 렌더 → copy_tool → GitHub 푸시
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
DATE="2026-05-29"
LOG="logs/auto_${DATE}_render.log"
mkdir -p logs
{
  echo "=== START $(date) ==="
  echo "--- 1) HTML → PNG (Playwright) ---"
  python3 scripts/html_to_png.py "$DATE" 2>&1
  echo "--- PNG 결과 ---"
  ls -lh "images/$DATE/"*.png 2>&1

  echo "--- 2) copy_tool.html 생성 ---"
  python3 scripts/generate_copy_tool.py "$DATE" 2>&1
  ls -lh "output/${DATE}_copy_tool.html" 2>&1

  echo "--- 3) GitHub 푸시 ---"
  bash scripts/git_push_daily.sh "$DATE" 2>&1

  echo "=== DONE $(date) ==="
} > "$LOG" 2>&1
echo "완료 — 로그: $LOG"
