#!/bin/bash
# 2026-05-14 daily 아카이브 푸시 헬퍼
# Cowork 샌드박스에서 .git/index.lock 제거가 안 되어 Mac에서 수동 실행 필요

set -e
cd "$(dirname "$0")"

echo "==> 1. 잔존 lock 제거"
rm -f .git/index.lock

echo "==> 2. 작업 파일 add"
git add -f daily/2026-05-14/ 2026-05-14_seo.md output/2026-05-14_copy_tool.html

echo "==> 3. 커밋"
git commit -m "feat: 2026-05-14 daily 아카이브 — blog/seo/copy_tool/PNG 5장" || echo "커밋 대상 없음 (이미 커밋됨)"

echo "==> 4. 푸시"
git pull --rebase origin main || true
git push origin main

echo ""
echo "✅ 완료 — GitHub daily/2026-05-14/ 확인 가능"
read -p "엔터로 닫기..."
