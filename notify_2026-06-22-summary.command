#!/bin/bash
# 2026-06-22 15:30 시황 요약 — 텔레그램 알림 위임 (샌드박스 프록시 403으로 자동 전송 불가)
# 더블클릭 또는 `bash notify_2026-06-22-summary.command` 로 실행
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"
python3 "$BASE/notify.py" "✅ 15:30 시황 요약 발행 완료: 코스피 9,114 또 사상최고 — SK하이닉스 26년 만에 시총 1위 등극 (외국인 2.5조 매도에도 신고가)"
echo "done"
