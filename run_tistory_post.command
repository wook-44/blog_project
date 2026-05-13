#!/bin/bash
cd "/Users/chanwook/Documents/Claude/Projects/블로그"

echo "📦 Playwright 설치 확인..."
pip3 install playwright --user --quiet 2>/dev/null || pip3 install playwright --break-system-packages --quiet 2>/dev/null

echo "🌐 Playwright 브라우저 설치 확인..."
python3 -m playwright install chromium 2>/dev/null

echo ""
echo "🚀 티스토리 자동 포스팅 시작..."
echo ""
python3 tistory_post.py

echo ""
read -p "엔터를 눌러 닫기..."
