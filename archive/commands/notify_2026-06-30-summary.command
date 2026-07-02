#!/bin/bash
# 2026-06-30 15:30 시황 요약 — 텔레그램 알림 위임 (샌드박스 프록시 403으로 자동 전송 불가)
# 더블클릭 또는 `bash notify_2026-06-30-summary.command` 로 실행
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"
python3 "$BASE/notify.py" "✅ 15:30 시황 요약 발행 완료: 코스피 8,476 반등·코스닥 약세 — 6월 30일 반도체 사자 복귀 (외국인 8일째 3.8조 매도에도 기관 2.96조 매수로 코스피 +0.97%, 이차전지 차익실현에 코스닥 -0.48%)"
echo "done"
