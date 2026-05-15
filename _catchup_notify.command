#!/bin/bash
cd "$(dirname "$0")"
python3 notify.py "📝 <b>Cowork 세션 작업 보고</b>
• 텔레그램 연동 + run_daily_auto 8단계 훅
• SKILL.md: 인포그래픽 3~5장 가변 룰
• generate_infographics.py: <code>fit_font()</code> 자동 폰트 축소
• generate_copy_tool.py: 본문 헤더 순서 PNG 정렬 + 동적 마커
• 5/14 샘플 5장 + copy_tool 생성 완료
• 개별 스크립트(copy_tool, regen_week)에 텔레그램 훅 추가

다음 17:30 자동화부터 단계별 보고 시작"
echo "엔터로 창 닫기..."
read
