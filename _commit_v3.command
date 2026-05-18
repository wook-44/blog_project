#!/bin/bash
# v3: 5/15 본문 + TCC 우회 + 5/18 시황요약 트랙 + 진단 스크립트들 일괄 commit·push
set -u
cd "$(dirname "$0")"
BLOG="$(pwd)"

[ -f .git/index.lock ] && { echo "🧹 index.lock 제거"; rm -f .git/index.lock; }
[ -f .git/HEAD.lock ] && rm -f .git/HEAD.lock

echo "── 현재 상태 ──"
git status --short | head -25
echo ""

# 1. 변경 stash (untracked 포함)
echo "📦 stash..."
git stash push -u -m "before commit_v3 $(date +%H%M)" 2>&1 | tail -2
echo ""

# 2. pull --rebase
echo "🔄 git pull --rebase origin main..."
git pull --rebase origin main 2>&1 | tail -5
echo ""

# 3. stash 복원
echo "📤 stash pop..."
git stash pop 2>&1 | tail -3
echo ""

# 4. add — 백업/캐시 제외
echo "📋 add..."
# 5/15 영상 분석 트랙
git add 2026-05-15-kospi-8000-bubble-debate.md
git add images/2026-05-15/
git add data/transcripts/
git add output/2026-05-15_copy_tool.html
# TCC 우회 + 진단
git add _fix_launchd_tcc.command
git add _diagnose_launchd.command 2>/dev/null
git add _fix_perms_and_run.command 2>/dev/null
git add _commit_v2.command _commit_v3.command _commit_all_today.command 2>/dev/null
git add _catchup_notify.command 2>/dev/null
git add _render_2026-05-15.command 2>/dev/null
git add _get_transcript_2026-05-15.command _get_transcript_v2.command _get_transcript_v3.command 2>/dev/null
# 5/18 시황 요약 트랙 (사용자가 새로 만든 v2)
git add 2026-05-18-summary-kospi-7516-foreign-sell.md 2>/dev/null
git add _render_2026-05-18-summary.command 2>/dev/null
git add _push_2026-05-18-summary.command 2>/dev/null
git add output/2026-05-18*.html 2>/dev/null
git add images/2026-05-18/ 2>/dev/null
git add daily/2026-05-18/ 2>/dev/null
# v2 톤북/SKILL 업데이트
git add stock-youtube-blog-writer/SKILL.md
git add stock-youtube-blog-writer/references/tone-book.md
git add stock-youtube-blog-writer/references/youtube-description-guide.md 2>/dev/null
# 누락 가능 기타
git add 2026-05-15_pipeline_status.md 2>/dev/null

# .bak 제외 보강
git reset HEAD '*.pre5img.bak' '*.v1.bak' '*.misdated.bak' 2>/dev/null

STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
echo "✅ staged: ${STAGED}개"
if [ "$STAGED" -eq 0 ]; then
  echo "⚠️ 반영할 변경 없음"
  python3 notify.py "ℹ️ <b>commit_v3: 변경 없음</b>"
  read -t 30 || true; exit 0
fi
git diff --cached --name-only | head -25
echo ""

# 5. commit
echo "── commit ──"
git commit -m "feat: 5/15 영상 분석 + TCC 우회 launcher + v2 시황 요약 트랙

5/15 영상 분석 (코스피 8000 후 -3%, 버블 vs 펀더멘털)
- 본문 .md (린터 통과, 5567자, 32 태그, 30자 제목)
- 인포그래픽 5장 (market/psychology/summary/outlook/sector — sector는 엄경아 조선 분석)
- copy_tool.html (4.6MB, 본문 헤더 순서 정렬)
- 영상 자막 yt-dlp v3로 추출 (data/transcripts/2026-05-15_transcript_v3.txt)

launchd TCC 우회 (5/16~5/17 자동화 실패 원인 해결)
- ~/Library/Application Support/blog-runner/runner.sh 비보호 위치 launcher
- plist를 runner.sh 호출로 수정 — Terminal GUI 컨텍스트로 .command 실행
- 5/18 15:55 즉시 테스트 트리거로 작동 확인

진단/일회 .command
- _diagnose_launchd / _fix_perms_and_run / _fix_launchd_tcc
- _commit_v2 / v3 / all_today / catchup_notify
- _get_transcript_v2 / v3 (yt-dlp Korean auto-sub)
- _render_2026-05-15

v2 톤북/SKILL 업데이트 (사용자 직접 갱신)
- 트래픽 성장 위주: 종목명/지수 키워드 앞 12자, 브랜드 키워드 제목 금지
- 📍 이 글에서 다루는 것, 🔗 관련 종목 한눈에 신설
- 본문 최저 2500자, market 첫 카드 = 종목 스냅샷
- 발행 분산: daily-market-summary(15:30) + 본편(17:30)" 2>&1 | tail -3
echo ""

# 6. push
echo "🚀 push..."
PUSH_OUT=$(git push origin main 2>&1)
echo "$PUSH_OUT" | tail -5
echo ""

if echo "$PUSH_OUT" | grep -qE "rejected|error:"; then
  python3 notify.py "❌ <b>push 실패</b>
<pre>$(echo "$PUSH_OUT" | tail -5)</pre>"
else
  python3 notify.py "✅ <b>commit_v3 완료</b>
${STAGED}개 파일 main에 반영
TCC 우회 작동, 5/15 트랙·v2 룰 동기화"
fi

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
