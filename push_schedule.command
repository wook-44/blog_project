#!/bin/bash
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "📝 변경사항 스테이징 중..."
git add -A

echo "📝 커밋 중..."
git commit -m "chore: change schedule to 17:00 KST (08:00 UTC)" 2>/dev/null || echo "(커밋할 새 내용 없음)"

echo "⬇️  원격 변경사항 병합 중..."
git pull origin main --rebase 2>&1 | tail -5

echo "📤 GitHub 푸시 중..."
git push origin HEAD

echo ""
if [ $? -eq 0 ]; then
  echo "✅ 완료! 매일 오후 5시 KST로 변경됐습니다."
else
  echo "❌ 푸시 실패"
fi
echo ""
read -p "엔터를 눌러 닫기..."
