#!/bin/bash
# 2026-06-29 15:30 시황 요약 — 텔레그램 알림 위임 (샌드박스 프록시 403으로 자동 전송 불가)
# 더블클릭 또는 `bash notify_2026-06-29-summary.command` 로 실행
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"
python3 "$BASE/notify.py" "✅ 15:30 시황 요약 발행 완료: 코스피 8,394 보합·코스닥 8% 폭등 — 6월 29일 증시 양극화 (외국인 7.7조 매도에도 코스피 보합, 이차전지·바이오 순환매로 코스닥 8.13% 급등)"
echo "done"
