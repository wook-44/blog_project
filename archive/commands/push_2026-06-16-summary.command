#!/bin/bash
# 2026-06-16 15:30 시황 요약 — GitHub 푸시 위임 (샌드박스 fuse 잠금으로 자동 푸시 불가)
# 더블클릭 또는 `bash push_2026-06-16-summary.command` 로 실행
set -e
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"

echo "🔓 stale lock 정리..."
rm -f .git/*.lock .git/refs/heads/*.lock .git/refs/remotes/origin/*.lock 2>/dev/null || true

echo "📤 2026-06-16 시황 요약 푸시..."
git add daily/2026-06-16-summary \
        2026-06-16_summary_blog.md \
        2026-06-16_summary_sections.json \
        output/2026-06-16_summary_copy_tool.html \
        images/2026-06-16-summary \
        scripts/agents/00_title_tag_linter.py 2>/dev/null || true

if git diff --cached --quiet; then
  echo "   변경사항 없음 — 이미 최신 상태"
else
  git commit -m "feat: 2026-06-16 15:30 시황 요약 (코스피 8,726 +2.11%, 외국인 1.5조 4일째 매수)"
  git pull origin main --rebase 2>&1 | tail -3 || true
  git push origin HEAD
  echo "   ✅ GitHub 푸시 완료!"
fi

# 텔레그램 완료 알림
if [ -f "$BASE/notify.py" ] && [ -f "$BASE/.telegram_config" ]; then
  python3 "$BASE/notify.py" "✅ 15:30 시황 요약 발행 완료: 코스피 8,726 상승 — 외국인 1.5조 4일째 순매수" || true
fi
echo "🎉 done"
