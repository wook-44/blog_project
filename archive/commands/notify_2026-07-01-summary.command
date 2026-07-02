#!/bin/bash
# 2026-07-01 15:30 시황 요약 — 텔레그램 알림 위임 (샌드박스 프록시 403으로 자동 전송 불가)
# 더블클릭 또는 `bash notify_2026-07-01-summary.command` 로 실행
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"
if [ -f "$BASE/notify.py" ] && [ -f "$BASE/.telegram_config" ]; then
  python3 "$BASE/notify.py" "✅ 15:30 시황 요약 발행 완료: 코스피 8,303 -2.04% 하락·코스닥 929 반등 — 외국인 1.7조 매도, 자금은 전력·방산·건설로" && echo "✅ 텔레그램 전송 완료"
else
  echo "⚠️ notify.py 또는 .telegram_config 없음"
fi
