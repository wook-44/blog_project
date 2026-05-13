#!/bin/bash
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "📦 4월 블로그 전체 GitHub 푸시 중... (9개, 파일명 규칙 통일본)"
echo ""

# 4월 생성된 모든 파일 스테이징
git add \
  2026-04-20*.md 2026-04-21*.md 2026-04-22*.md \
  2026-04-23*.md 2026-04-24*.md 2026-04-27*.md \
  2026-04-28*.md 2026-04-29*.md 2026-04-30*.md \
  output/2026-04-20_copy_tool.html \
  output/2026-04-21_copy_tool.html \
  output/2026-04-22_copy_tool.html \
  output/2026-04-23_copy_tool.html \
  output/2026-04-24_copy_tool.html \
  output/2026-04-27_copy_tool.html \
  output/2026-04-28_copy_tool.html \
  output/2026-04-29_copy_tool.html \
  output/2026-04-30_copy_tool.html \
  images/2026-04-20 images/2026-04-21 images/2026-04-22 \
  images/2026-04-23 images/2026-04-24 images/2026-04-27 \
  images/2026-04-28 images/2026-04-29 images/2026-04-30 \
  daily/2026-04-20 daily/2026-04-21 daily/2026-04-22 \
  daily/2026-04-23 daily/2026-04-24 daily/2026-04-27 \
  daily/2026-04-28 daily/2026-04-29 daily/2026-04-30 \
  scripts/generate_copy_tool.py \
  scripts/git_push_daily.sh \
  scripts/git_push_daily.sh \
  scripts/get_youtube_transcript.py \
  push_daily.command \
  2>/dev/null || true

if git diff --cached --quiet; then
  echo "⚠️  스테이징된 변경사항 없음 (이미 최신 상태)"
else
  git commit -m "feat: 2026년 4월 블로그 전체 (4/20~4/30, 9개) + 파일명 규칙 통일"
  echo "⬇️  원격 변경사항 병합 중..."
  git pull origin main --rebase 2>&1 | tail -5
  echo "📤 GitHub 푸시 중..."
  git push origin HEAD
  echo ""
  echo "✅ 완료! GitHub daily/ + output/ 폴더에 4월 블로그 9개 업로드됨"
fi

echo ""
read -p "엔터를 눌러 닫기..."
