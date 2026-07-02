#!/bin/bash
# 2026-06-24 15:30 시황 요약 — 텔레그램 알림 위임 (샌드박스 프록시 403으로 자동 전송 불가)
# 더블클릭 또는 `bash notify_2026-06-24-summary.command` 로 실행
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"
python3 "$BASE/notify.py" "✅ 15:30 시황 요약 발행 완료: 코스피 8,471 반등 마감 — 6월 24일 삼성전자 9% 급반등 (외국인 4.6조 매도에도 폭락 하루 만에 반등)"
echo "done"
