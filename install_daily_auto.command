#!/bin/bash
# install_daily_auto.command — launchd에 매일 12:30 KST 자동 실행 등록
# 한 번만 더블클릭하면 끝. 이후 매일 자동.

cd "$(dirname "$0")"
BLOG="$(pwd)"
PLIST_SRC="$BLOG/com.user.blog-daily.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.user.blog-daily.plist"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  데일리 자동 발행 설치"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 기존 등록 있으면 해제
launchctl unload "$PLIST_DST" 2>/dev/null

# 2. plist 복사
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"
echo "✅ plist 설치: $PLIST_DST"

# 3. 등록
launchctl load "$PLIST_DST"
echo "✅ launchd 등록 완료"

# 4. 검증
echo ""
echo "📋 현재 등록 상태:"
launchctl list | grep blog-daily || echo "  (목록에 없음 — 등록 실패 가능)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📅 매일 KST 12:30 자동 실행"
echo ""
echo "  📁 작업 폴더: $BLOG"
echo "  📜 실행 스크립트: run_daily_auto.command"
echo "  📋 로그: logs/daily_auto_{날짜}.log"
echo ""
echo "  중단하려면: launchctl unload $PLIST_DST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "엔터로 닫기..." _
