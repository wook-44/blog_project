#!/bin/bash
# notify_telegram.sh — 텔레그램 봇으로 알림 전송
#
# 사용:
#   bash scripts/notify_telegram.sh "메시지 내용"
#
# 환경변수 (.env에 저장 권장):
#   TELEGRAM_BOT_TOKEN  — BotFather에서 발급
#   TELEGRAM_CHAT_ID    — 자기 채팅 ID (아래 'setup' 섹션 참조)
#
# 1회 셋업 (5분):
#   ① Telegram 앱 → @BotFather 검색 → /newbot → 봇 이름 정하기
#   ② BotFather가 주는 토큰을 .env에 TELEGRAM_BOT_TOKEN=xxx 저장
#   ③ 새로 만든 봇에게 아무 메시지 보내기 (대화 시작)
#   ④ 브라우저 → https://api.telegram.org/bot<TOKEN>/getUpdates
#       → "chat":{"id":12345678} 숫자가 chat_id
#   ⑤ .env에 TELEGRAM_CHAT_ID=12345678 저장

set -u
MSG="${1:-알림 없음}"
BLOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# .env 로드 (우선순위 1)
if [ -f "$BLOG_DIR/.env" ]; then
  set -a; source "$BLOG_DIR/.env"; set +a
fi

# .telegram_config 폴백 (우선순위 2) — BOT_TOKEN/CHAT_ID → TELEGRAM_* 매핑
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  if [ -f "$BLOG_DIR/.telegram_config" ]; then
    _BT=$(grep '^BOT_TOKEN=' "$BLOG_DIR/.telegram_config" | cut -d= -f2-)
    _CI=$(grep '^CHAT_ID=' "$BLOG_DIR/.telegram_config" | cut -d= -f2-)
    TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$_BT}"
    TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-$_CI}"
  fi
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "  ℹ️  텔레그램 알림 스킵 — TELEGRAM_BOT_TOKEN/CHAT_ID 미설정 (.env 또는 .telegram_config)"
  exit 0
fi

# 메시지 길이 제한 (텔레그램 4,096자)
if [ ${#MSG} -gt 4000 ]; then
  MSG="${MSG:0:4000}...(생략)"
fi

# 전송
RESP=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "parse_mode=Markdown" \
  --data-urlencode "disable_web_page_preview=true")

if echo "$RESP" | grep -q '"ok":true'; then
  echo "  ✅ 텔레그램 알림 전송 완료"
else
  echo "  ❌ 텔레그램 전송 실패: $(echo "$RESP" | head -c 200)"
fi
