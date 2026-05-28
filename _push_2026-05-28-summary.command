#!/bin/bash
# 2026-05-28 시황 요약 GitHub 푸시
# 15:30 자동 스케줄에서 sandbox 푸시 권한 이슈가 있으면 로컬에서 더블클릭 실행
cd "$(dirname "$0")"
echo "[push] 2026-05-28-summary 푸시 시작"

# stale index.lock 정리
rm -f .git/index.lock 2>/dev/null

# 인포그래픽 PNG가 없으면 먼저 렌더
PNG=images/2026-05-28-summary/2026-05-28-summary-market.png
if [ ! -f "$PNG" ]; then
  echo "[push] PNG 없음 — 먼저 렌더 명령 실행"
  bash _render_2026-05-28-summary.command || true
  cp "$PNG" daily/2026-05-28-summary/images/ 2>/dev/null || true
fi

# 산출물 add
git add 2026-05-28_summary_blog.md \
        daily/2026-05-28-summary/ \
        images/2026-05-28-summary/ \
        _render_2026-05-28-summary.command \
        _push_2026-05-28-summary.command 2>&1

git add -f output/2026-05-28_summary_copy_tool.html 2>/dev/null || true
git add -f 2026-05-28_summary_sections.json 2>/dev/null || true

git commit -m "feat: 2026-05-28 시황 요약 (15:30 자동) — 코스피 8,167 -0.74%, 외국인 2.9조 매도 14거래일째"
git pull origin main --rebase 2>&1 | tail -3
git push origin HEAD

if [ -f notify.py ]; then
  python3 notify.py "✅ 15:30 시황 요약 푸시 완료 — 코스피 8,167 -0.74%, 외국인 2.9조 매도 14거래일째" || true
fi

echo "[push] 완료"
