#!/bin/bash
# push_daily.command
# 오늘 날짜 기준으로 블로그 산출물을 GitHub에 푸시

TODAY=$(date +%Y-%m-%d)
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "🗓️  오늘 날짜: $TODAY"
echo ""

bash scripts/git_push_daily.sh "$TODAY"

read -p "엔터를 눌러 닫기..."
