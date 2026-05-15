#!/bin/bash
# 권한·xattr 복구 + run_daily_auto.command 즉시 수동 실행
cd "$(dirname "$0")"
BLOG="$(pwd)"

echo "🔧 권한 복구..."
chmod +x "$BLOG"/*.command 2>/dev/null
chmod +x "$BLOG"/scripts/*.sh 2>/dev/null

# macOS quarantine 비트 제거 (외부 다운로드/편집 시 붙어서 실행 차단 가능)
xattr -d com.apple.quarantine "$BLOG/run_daily_auto.command" 2>/dev/null
xattr -d com.apple.quarantine "$BLOG"/*.command 2>/dev/null
ls -l "$BLOG/run_daily_auto.command"
echo ""

echo "🚀 run_daily_auto.command 수동 실행..."
echo "(보고가 텔레그램으로 자동 전송됩니다)"
echo ""

# 백그라운드 실행 — 이 창은 즉시 종료 가능
nohup bash "$BLOG/run_daily_auto.command" >/dev/null 2>&1 &
PID=$!
echo "✅ PID=$PID로 시작됨"

# 1~2분 후 로그 첫 줄 확인
sleep 30
LOG="$BLOG/logs/daily_auto_$(date +%Y-%m-%d).log"
if [ -f "$LOG" ]; then
  echo ""
  echo "── 로그 시작 (첫 10줄) ──"
  head -10 "$LOG"
fi

echo ""
echo "엔터로 창 닫기 (백그라운드 자동화는 계속 실행)..."
read
