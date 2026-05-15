#!/bin/bash
# 5/15 자동화가 왜 안 돌았는지 진단 — launchd 상태 + plist 시간 + telegram config
cd "$(dirname "$0")"
BLOG="$(pwd)"
PLIST="$HOME/Library/LaunchAgents/com.user.blog-daily.plist"

REPORT=""
add() { REPORT="${REPORT}${1}
"; }

add "🔎 <b>데일리 자동화 진단</b>"
add "시각: $(date '+%Y-%m-%d %H:%M:%S %Z')"
add ""
add "── launchctl 등록 상태 ──"
if STATUS=$(launchctl list | grep blog-daily 2>/dev/null) && [ -n "$STATUS" ]; then
  add "✅ 등록됨"
  add "<code>$STATUS</code>"
else
  add "❌ 등록 없음 — install_daily_auto.command 더블클릭 필요"
fi
add ""

add "── plist 트리거 시간 ──"
if [ -f "$PLIST" ]; then
  HOUR=$(plutil -extract StartCalendarInterval.Hour raw "$PLIST" 2>/dev/null)
  MIN=$(plutil -extract StartCalendarInterval.Minute raw "$PLIST" 2>/dev/null)
  add "✅ 설치됨: ${HOUR}:${MIN} KST"
else
  add "❌ plist 파일 없음: $PLIST"
fi
add ""

add "── 오늘 로그 ──"
LOG="logs/daily_auto_$(date +%Y-%m-%d).log"
if [ -f "$LOG" ]; then
  LINES=$(wc -l < "$LOG" | tr -d ' ')
  add "✅ 로그 존재 (${LINES}줄)"
  LAST=$(tail -3 "$LOG" | sed 's/</\&lt;/g')
  add "<pre>${LAST}</pre>"
else
  add "⚠️ 오늘 로그 없음 — 자동화 미실행"
fi
add ""

add "── .telegram_config ──"
if [ -f .telegram_config ]; then
  CHAT=$(grep '^CHAT_ID=' .telegram_config | cut -d= -f2-)
  add "✅ CHAT_ID=${CHAT}"
else
  add "❌ .telegram_config 없음"
fi

# 보고 전송
python3 notify.py "$REPORT"

echo ""
echo "$REPORT" | sed 's/<[^>]*>//g'
echo ""
echo "엔터로 창 닫기..."
read
