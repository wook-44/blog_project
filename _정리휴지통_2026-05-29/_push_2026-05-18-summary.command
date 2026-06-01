#!/bin/bash
# 2026-05-18 시황 요약 GitHub 푸시 (자동 스케줄 작업에서 sandbox lock 이슈로 미푸시된 산출물 처리)
cd "$(dirname "$0")"
echo "[push] 2026-05-18-summary 푸시 시작"

# stale index.lock 정리
rm -f .git/index.lock 2>/dev/null

# 산출물 add
git add 2026-05-18-summary-kospi-7516-foreign-sell.md \
        daily/2026-05-18-summary/ \
        images/2026-05-18-summary/ \
        _render_2026-05-18-summary.command \
        _push_2026-05-18-summary.command 2>&1

# output 폴더는 .gitignore에 있을 가능성 — daily에 이미 사본 있음
git add -f output/2026-05-18-summary_copy_tool.html 2>/dev/null || true

git commit -m "feat: 2026-05-18 시황 요약 (15:30 자동) — 코스피 7,516 +0.31%, 외국인 3.6조 순매도"

git push origin main

# 텔레그램 알림
if [ -f notify.py ]; then
  python3 notify.py "✅ 15:30 시황 요약 푸시 완료 — 코스피 7,516 +0.31%, 외국인 3.6조 순매도"
fi

echo "[push] 완료"
read -p "Enter to close..."
