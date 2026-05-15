#!/bin/bash
# notify.py 발송 테스트
cd "$(dirname "$0")"
python3 notify.py "🤖 <b>텔레그램 알림 테스트</b>
블로그 워크플로우 알림이 정상 작동합니다.
이 메시지가 보이면 연동 성공!"
echo ""
echo "엔터로 창 닫기..."
read
