#!/bin/bash
cd "$(dirname "$0")"
echo "==> git pull origin main"
git pull --rebase origin main 2>&1
echo ""
echo "==> 최근 영상 (data/new_videos.csv)"
head -5 data/new_videos.csv
echo ""
echo "엔터로 닫기 ..."
read
