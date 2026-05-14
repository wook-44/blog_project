#!/bin/bash
# 2026-05-13 블로그 일괄 푸시 (Cowork 자동 생성)
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "🗓️  타깃 날짜: 2026-05-13"
bash scripts/git_push_daily.sh 2026-05-13

echo ""
echo "[엔터로 종료]"
read -t 5
