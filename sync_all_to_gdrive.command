#!/bin/bash
# sync_all_to_gdrive.command — 지금까지 만든 4월 분 전체를 Google Drive로 미러링
#  이 스크립트는 push_now와 별개로 GDrive 미러링만 강제 실행

cd "$(dirname "$0")"
BLOG="$(pwd)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Google Drive 백필 동기화"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Google Drive 경로 자동 감지
echo "🔍 Google Drive 폴더 탐색 (쓰기 가능 우선)..."
echo ""
GDRIVE=""

# 1) Library/CloudStorage 안의 GoogleDrive-* 디렉터리 동적 탐색
shopt -s nullglob 2>/dev/null
for gd in "$HOME"/Library/CloudStorage/GoogleDrive-*; do
  [ -d "$gd" ] || continue
  for sub in "$gd/My Drive" "$gd/내 드라이브" "$gd"; do
    [ -d "$sub" ] || continue
    PROBE="$sub/.write_test_$$"
    if (touch "$PROBE" 2>/dev/null && rm -f "$PROBE"); then
      echo "  ✅ 사용: $sub (쓰기 가능)"
      GDRIVE="$sub"
      break 2
    else
      echo "  ✗ $sub (쓰기 불가)"
    fi
  done
done

# 2) Fallback 경로 (위에서 못 찾았을 때)
if [ -z "$GDRIVE" ]; then
  for p in "$HOME/Google Drive/My Drive" "/Volumes/GoogleDrive/My Drive" "$HOME/Google Drive"; do
    [ -d "$p" ] || continue
    PROBE="$p/.write_test_$$"
    if (touch "$PROBE" 2>/dev/null && rm -f "$PROBE"); then
      echo "  ✅ 사용: $p"
      GDRIVE="$p"
      break
    else
      echo "  ✗ $p (쓰기 불가)"
    fi
  done
fi

if [ -z "$GDRIVE" ]; then
  echo ""
  echo "❌ Google Drive 폴더를 찾지 못함."
  echo ""
  echo "직접 경로를 알려주려면 다음 명령으로 실행:"
  echo "   GDRIVE_TARGET='~/...실제경로...' bash $0"
  echo ""
  echo "참고용 후보 경로:"
  ls -la "$HOME/Library/CloudStorage/" 2>&1 | head -10
  read -p "엔터로 닫기..." _
  exit 1
fi

echo ""
BASE="$GDRIVE/blog/12시에만나요"
echo "📂 미러링 대상: $BASE"
echo ""

# 4월 3주차 + 4주차 일괄 미러링
TOTAL_DATES=0
TOTAL_FILES=0
for d in 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24 2026-04-27 2026-04-28 2026-04-29 2026-04-30; do
  echo "📅 $d"
  TARGET="$BASE/$d"
  mkdir -p "$TARGET"
  count=0
  # 본문 .md
  for f in "$BLOG"/${d}*.md; do
    [ -f "$f" ] && [[ "$f" != *.bak ]] && {
      cp "$f" "$TARGET/" && count=$((count+1))
    }
  done
  # PNG
  if [ -d "$BLOG/images/$d" ]; then
    mkdir -p "$TARGET/images"
    cp "$BLOG/images/$d"/*.png "$TARGET/images/" 2>/dev/null
    pcount=$(ls "$TARGET/images"/*.png 2>/dev/null | wc -l | tr -d ' ')
    count=$((count+pcount))
  fi
  # copy_tool
  CT="$BLOG/output/${d}_copy_tool.html"
  [ -f "$CT" ] && { cp "$CT" "$TARGET/" && count=$((count+1)); }

  echo "  · 파일 $count개 복사"
  [ "$count" -gt 0 ] && { TOTAL_DATES=$((TOTAL_DATES+1)); TOTAL_FILES=$((TOTAL_FILES+count)); }
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 완료 — $TOTAL_DATES일치, 총 $TOTAL_FILES개 파일"
echo ""
echo "  📂 위치: $BASE/"
echo "  ⏱  Google Drive 앱이 백그라운드에서 클라우드에 업로드 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "엔터로 닫기..." _
