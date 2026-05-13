#!/bin/bash
# 로컬에 쌓인 커밋을 GitHub에 푸시
cd "$(dirname "$0")"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GitHub 푸시: wook-44/blog_project"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 로컬 커밋:"
git log origin/main..HEAD --oneline
echo ""
echo "🚀 push 중..."
git push origin main
EXIT=$?
echo ""
if [ $EXIT -eq 0 ]; then
  echo "✅ 푸시 완료"
else
  echo "❌ 푸시 실패 (exit $EXIT)"
fi
read -p "엔터로 닫기..." _
