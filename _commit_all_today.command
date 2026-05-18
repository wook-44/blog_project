#!/bin/bash
# 오늘 변경된 파일 일괄 커밋·푸시 — 자동화 완료 후 실행 권장
set -u
cd "$(dirname "$0")"
BLOG="$(pwd)"

# 자동화 종료 마커 — "완료", "copy_tool:" (정상 6단계), "오늘 본문 없음" (조기 정상 종료)
LOG="$BLOG/logs/daily_auto_$(date +%Y-%m-%d).log"
if [ -f "$LOG" ]; then
  if ! grep -qE "데일리 자동화 완료|copy_tool:|오늘 본문 없음" "$LOG"; then
    echo "⚠️ 자동화가 아직 실행 중일 수 있습니다 (로그 마지막):"
    tail -3 "$LOG"
    echo "→ 그래도 계속 진행 (read 프롬프트 제거됨)"
    echo ""
  else
    echo "✅ 자동화 종료 확인됨"
  fi
fi

echo "🔄 git pull (rebase autostash)..."
git pull --rebase --autostash origin main 2>&1 | tail -5
echo ""

# 백업/일회용 파일은 제외, 의도된 변경만 add
echo "📦 add..."
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
# 5/14 콘텐츠 (5장 가변 룰 검증용 샘플)
git add 2026-05-14-trump-xi-beijing-30man-target.md
git add images/2026-05-14/
# 일회 스크립트
git add sample_5img_2026-05-14.command
git add _catchup_notify.command _diagnose_launchd.command _fix_perms_and_run.command
# 자동화가 만든 일일 파일은 자동화가 따로 처리하므로 여기선 제외

# .pre*.bak / .v1.bak / .misdated.bak 패턴 제외 확인
echo "📋 staged 파일:"
git diff --cached --name-only | head -30

echo ""
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
- 진단/복구용 .command 추가 (_diagnose_launchd, _fix_perms_and_run, _catchup_notify, sample_5img)" 2>&1 | tail -3

echo ""
echo "🚀 push..."
git push origin main 2>&1 | tail -5

echo ""
echo "✅ 완료. 텔레그램 보고도 함께 발송:"
python3 notify.py "📦 <b>오늘 변경 일괄 커밋·푸시</b>
텔레그램 통합 / 가변 룰 / fit_font / 5/14 5장 샘플
내일 17:30 자동화부터 적용"

echo ""
echo "(창은 60초 후 자동 닫힘 또는 엔터로 닫기)"
read -t 60 || true
