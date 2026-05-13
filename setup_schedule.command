#!/bin/bash
# setup_schedule.command — 17:30 launchd 등록 + 17:25 자동 wake 설정
#   한 번만 더블클릭. 이후 Mac이 잠자기 상태여도 17:25에 자동 깨어남.
#   ※ pmset는 sudo 비밀번호 1회 입력 필요.

cd "$(dirname "$0")"
BLOG="$(pwd)"
PLIST_SRC="$BLOG/com.user.blog-daily.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.user.blog-daily.plist"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  데일리 스케줄 설정 (17:30 KST)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1) launchd 등록
launchctl unload "$PLIST_DST" 2>/dev/null
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"
echo "✅ launchd 17:30 매일 자동 실행 등록"
launchctl list | grep blog-daily || echo "  ⚠️ launchd 등록 확인 안 됨"

# 2) pmset 자동 wake (17:25)
echo ""
echo "🌅 pmset로 매일 17:25에 자동 wake 설정..."
echo "   (sudo 비밀번호 입력 필요 — Mac이 잠자기 상태여도 17:25에 깨어남)"
echo ""

# 기존 wakepoweron 스케줄 제거
sudo pmset repeat cancel 2>/dev/null
# 매일 17:25에 wake
sudo pmset repeat wakeorpoweron MTWRFSU 17:25:00
if [ $? -eq 0 ]; then
  echo "✅ pmset 자동 wake 17:25 설정 완료"
  echo ""
  echo "현재 스케줄:"
  pmset -g sched
else
  echo "⚠️ pmset 설정 실패 — Mac이 잠자기 상태면 launchd가 못 깨움"
  echo "   수동 설정: 시스템 설정 → 배터리 → 옵션 → 일정에 따라 컴퓨터 시작 또는 깨우기"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📋 흐름"
echo ""
echo "    17:00 (KST)  GitHub Actions가 영상 체크 + 본문 작성 + push"
echo "    17:25 (KST)  Mac 자동 wake (pmset)"
echo "    17:30 (KST)  launchd가 run_daily_auto.command 실행"
echo "                 ↓ git pull"
echo "                 ↓ PNG 생성 (Chrome headless)"
echo "                 ↓ 린터 + 시리즈 링커"
echo "                 ↓ copy_tool.html 생성"
echo "                 ↓ Git push + Google Drive 미러링"
echo "                 ↓ macOS 알림 + copy_tool 자동 열기"
echo ""
echo "  중단하려면:"
echo "    launchctl unload $PLIST_DST"
echo "    sudo pmset repeat cancel"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "엔터로 닫기..." _
