#!/bin/bash
# git_push_daily.sh
# 오늘의 블로그 산출물을 daily/YYYY-MM-DD/ 폴더에 정리 후 GitHub에 푸시
#
# 파일명 규칙:
#   루트 작업 파일  : YYYY-MM-DD_blog.md / YYYY-MM-DD_seo.md
#   HTML 복붙 도구  : output/YYYY-MM-DD_copy_tool.html
#   인포그래픽 PNG  : images/YYYY-MM-DD/YYYY-MM-DD-{section}.png
#   GitHub 아카이브 : daily/YYYY-MM-DD/{blog_post.md, seo.md, copy_tool.html, images/}
#
# 사용법:
#   bash scripts/git_push_daily.sh [YYYY-MM-DD]

set -e

BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
DATE="${1:-$(date +%Y-%m-%d)}"
DAILY_DIR="$BASE/daily/$DATE"

cd "$BASE"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "📁 daily/$DATE 폴더 생성 중..."
mkdir -p "$DAILY_DIR/images"

# ── 1. 블로그 md 파일 복사 (YYYY-MM-DD_blog.md 우선, 없으면 날짜 prefix 탐색)
MD_FILE=$(find "$BASE" -maxdepth 1 -name "${DATE}_blog.md" 2>/dev/null | head -1)
if [ -z "$MD_FILE" ]; then
  MD_FILE=$(find "$BASE" -maxdepth 1 -name "${DATE}*.md" | grep -v seo | grep -v README | grep -v SECRETS | head -1)
fi
if [ -n "$MD_FILE" ]; then
  cp "$MD_FILE" "$DAILY_DIR/blog_post.md"
  echo "   ✅ blog_post.md 복사 ($(basename $MD_FILE))"
else
  echo "   ⚠️  md 파일 없음 (스킵)"
fi

# ── 2. SEO md 파일 복사 (YYYY-MM-DD_seo.md)
SEO_FILE=$(find "$BASE" -maxdepth 1 -name "${DATE}_seo.md" 2>/dev/null | head -1)
if [ -z "$SEO_FILE" ]; then
  SEO_FILE=$(find "$BASE" -maxdepth 1 -name "${DATE}*seo*.md" | head -1)
fi
if [ -n "$SEO_FILE" ]; then
  cp "$SEO_FILE" "$DAILY_DIR/seo.md"
  echo "   ✅ seo.md 복사"
fi

# ── 3. 이미지 PNG 복사 (images/YYYY-MM-DD/*.png)
IMG_DIR="$BASE/images/$DATE"
if [ -d "$IMG_DIR" ]; then
  cp "$IMG_DIR"/*.png "$DAILY_DIR/images/" 2>/dev/null && echo "   ✅ 이미지 복사"
else
  echo "   ⚠️  images/$DATE 폴더 없음 (스킵)"
fi

# ── 4. HTML 복붙 도구 복사 (output/YYYY-MM-DD_copy_tool.html)
HTML_FILE="$BASE/output/${DATE}_copy_tool.html"
if [ -f "$HTML_FILE" ]; then
  cp "$HTML_FILE" "$DAILY_DIR/copy_tool.html"
  echo "   ✅ copy_tool.html 복사 (output/ → daily/$DATE/)"
else
  echo "   ⚠️  HTML 복사 도구 없음 (스킵): output/${DATE}_copy_tool.html"
fi

# ── 5. Git 커밋 & 푸시 ───────────────────────────────────
echo ""
echo "📤 GitHub 푸시 중..."
git add "daily/$DATE"
git add "output/" 2>/dev/null || true
git add "data/" 2>/dev/null || true

if git diff --cached --quiet; then
  echo "   변경사항 없음 — 이미 최신 상태"
else
  git commit -m "feat: $DATE 블로그 자동 생성 (블로그+이미지+HTML)"
  git pull origin main --rebase 2>&1 | tail -3
  git push origin HEAD
  echo "   ✅ GitHub 푸시 완료!"
fi

echo ""
echo "🎉 완료! daily/$DATE/ 폴더 구조:"
ls -la "$DAILY_DIR/" 2>/dev/null
ls -la "$DAILY_DIR/images/" 2>/dev/null
