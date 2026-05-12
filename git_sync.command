#!/bin/bash
# 블로그 프로젝트 Git 동기화 스크립트
# 이 파일을 더블클릭하면 Terminal에서 자동 실행됩니다

BLOG_DIR="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BLOG_DIR"

echo "📁 경로: $BLOG_DIR"
echo "🔗 Remote: $(git remote get-url origin 2>/dev/null | sed 's/github_pat[^@]*@/[PAT]@/')"
echo ""

# 기본 브랜치 확인
DEFAULT_BRANCH=$(git ls-remote --symref origin HEAD 2>/dev/null | awk '/^ref:/{print $2}' | sed 's|refs/heads/||')
if [ -z "$DEFAULT_BRANCH" ]; then
  DEFAULT_BRANCH="main"
fi
echo "🌿 기본 브랜치: $DEFAULT_BRANCH"
echo ""

# fetch
echo "⬇️  Fetching from origin..."
git fetch origin

# 로컬 커밋이 없으면 checkout, 있으면 pull
LOCAL_COMMITS=$(git log --oneline 2>/dev/null | wc -l | tr -d ' ')
if [ "$LOCAL_COMMITS" -eq 0 ]; then
  echo "📥 초기 체크아웃 중..."
  git checkout -b "$DEFAULT_BRANCH" "origin/$DEFAULT_BRANCH" 2>/dev/null || \
  git checkout "$DEFAULT_BRANCH" 2>/dev/null
else
  echo "🔄 Pulling latest changes..."
  git pull origin "$DEFAULT_BRANCH" --allow-unrelated-histories
fi

echo ""
echo "✅ Git 연동 완료!"
echo ""
git log --oneline -5 2>/dev/null || echo "(커밋 내역 없음)"
echo ""
read -p "엔터를 눌러 닫기..."
