#!/bin/bash
# v2: index.lock 정리 + pull --rebase 안전하게 + commit + push
set -u
cd "$(dirname "$0")"
BLOG="$(pwd)"

# 1. 혹시 남아있을 lock 정리
[ -f .git/index.lock ] && { echo "🧹 index.lock 제거"; rm -f .git/index.lock; }
[ -f .git/HEAD.lock ] && rm -f .git/HEAD.lock

echo "── 현재 상태 ──"
git status --short | head -15
echo ""

# 2. 현재 변경 일단 stash (untracked 포함) — pull 충돌 회피
echo "📦 변경 stash..."
git stash push -u -m "before commit_v2 $(date +%H%M)" 2>&1 | tail -2
echo ""

# 3. remote 최신 받아오기
echo "🔄 git pull --rebase origin main..."
git pull --rebase origin main 2>&1 | tail -5
echo ""

# 4. stash 복원
echo "📤 stash 복원..."
git stash pop 2>&1 | tail -3
echo ""

# 5. 의도된 파일들 add (백업 제외)
echo "📋 add..."
git add .gitignore
git add run_daily_auto.command
git add scripts/generate_copy_tool.py
git add scripts/git_push_daily.sh 2>/dev/null
git add scripts/notify_telegram.sh
git add scripts/regen_week_infographics.py
git add stock-youtube-blog-writer/SKILL.md
git add stock-youtube-blog-writer/references/generate_infographics.py
git add stock-youtube-blog-writer/references/tone-book.md
git add notify.py
git add setup_chat_id.command
git add test_notify.command
git add 2026-05-14-trump-xi-beijing-30man-target.md
git add 2026-05-14_seo.md
git add daily/2026-05-14/
git add images/2026-05-14/
git add sample_5img_2026-05-14.command
git add _catchup_notify.command _diagnose_launchd.command _fix_perms_and_run.command _commit_v2.command
git add 2026-05-15_pipeline_status.md push_2026-05-14.command 2>/dev/null

# pre*.bak / .v1.bak / .misdated.bak 제외 확인
git reset HEAD '*.pre5img.bak' '*.v1.bak' '*.misdated.bak' 2>/dev/null

# 6. 무엇이 staged 됐는지 보고
STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
echo "✅ staged: ${STAGED}개"

if [ "$STAGED" -eq 0 ]; then
  echo "⚠️ staged 파일 없음. 이미 push된 상태일 수 있음."
  python3 notify.py "ℹ️ <b>커밋할 변경 없음</b>
이미 반영된 상태"
  echo ""
  echo "(60초 후 자동 닫힘)"
  read -t 60 || true
  exit 0
fi

git diff --cached --name-only | head -20
echo ""

# 7. commit
echo "── commit ──"
git commit -m "feat: 텔레그램 알림 통합 + 인포그래픽 3~5장 가변 룰 + 자동 폰트 축소

- 텔레그램 .telegram_config 기반 outbound 알림 (BOT_TOKEN/CHAT_ID)
- run_daily_auto.command 8단계 보고 + EXIT trap + report_error
- generate_infographics.py: fit_font() 자동 축소, 긴 stat 값 카드 잘림 해결
- generate_copy_tool.py: 본문 헤더 순서로 PNG 정렬 + 동적 마커 (3~5장 가변)
- regen_week_infographics.py: 텔레그램 보고 훅
- notify_telegram.sh: .telegram_config 폴백 지원
- SKILL.md / tone-book.md: 필수 3종 + 선택 0~2종 가변 룰 명문화
- 5/14 본문에 outlook + checklist 섹션 추가, PNG 5장 재생성 (샘플 검증)
- 진단/복구용 .command 추가" 2>&1 | tail -3
echo ""

# 8. push
echo "🚀 push..."
PUSH_OUT=$(git push origin main 2>&1)
echo "$PUSH_OUT" | tail -5
echo ""

if echo "$PUSH_OUT" | grep -q "rejected\|error:"; then
  python3 notify.py "❌ <b>git push 실패</b>
<pre>$(echo "$PUSH_OUT" | tail -5)</pre>"
else
  python3 notify.py "✅ <b>일괄 커밋·푸시 완료</b>
${STAGED}개 파일 반영
내일 17:30 자동화부터 적용"
fi

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
