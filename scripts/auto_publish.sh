#!/bin/bash
# auto_publish.sh — 산출물 자동 배포 헬퍼
#   ① Git add → commit → push
#   ② Google Drive 자동 미러링 (감지된 경우)
#
# 사용:
#   bash scripts/auto_publish.sh [날짜] [메시지_접두어]
#   예: bash scripts/auto_publish.sh 2026-05-13 "데일리 자동 생성"
#
# 환경변수:
#   GDRIVE_TARGET — 강제 지정할 Google Drive 경로 (선택)
#   SKIP_GIT=1    — git 단계 건너뛰기
#   SKIP_GDRIVE=1 — Google Drive 단계 건너뛰기

set -u
BLOG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BLOG"

DATE="${1:-$(date +%Y-%m-%d)}"
PREFIX="${2:-자동 배포}"

echo ""
echo "──────────────────────────────────────────────"
echo " 📤 자동 배포  ($DATE)"
echo "──────────────────────────────────────────────"

# ── ① Git 자동 푸시 ─────────────────────────────────
if [ "${SKIP_GIT:-0}" != "1" ]; then
  echo ""
  echo "🔧 [1/2] Git 자동 푸시"

  rm -f .git/index.lock .git/HEAD.lock 2>/dev/null

  # 변경 상태 분석
  CHANGED=$(git status --short | wc -l | tr -d ' ')
  if [ "$CHANGED" -eq 0 ]; then
    echo "  ℹ️  변경 없음 — 푸시 스킵"
  else
    git add -A

    # 변경 파일 요약
    NEW_MD=$(git diff --cached --name-only --diff-filter=A | grep -E "^${DATE}.*\.md$" | head -1)
    NEW_PNG=$(git diff --cached --name-only | grep -E "images/${DATE}/.*\.png$" | wc -l | tr -d ' ')
    NEW_HTML=$(git diff --cached --name-only | grep -E "output/${DATE}.*\.html$" | wc -l | tr -d ' ')

    MSG="${PREFIX}: ${DATE}"
    [ -n "$NEW_MD" ] && MSG="${MSG} 본문"
    [ "$NEW_PNG" -gt 0 ] && MSG="${MSG} +PNG ${NEW_PNG}장"
    [ "$NEW_HTML" -gt 0 ] && MSG="${MSG} +copy_tool"

    git commit -m "$MSG" 2>&1 | tail -1

    echo "  🚀 push 중..."
    if git push origin main 2>&1 | tail -3; then
      echo "  ✅ Git 푸시 완료"
    else
      echo "  ⚠️  Git 푸시 실패 (네트워크 또는 충돌)"
    fi
  fi
fi

# ── ② Google Drive 미러링 ──────────────────────────
if [ "${SKIP_GDRIVE:-0}" != "1" ]; then
  echo ""
  echo "☁️  [2/2] Google Drive 미러링"

  # GDrive 경로 자동 감지 (쓰기 가능 우선)
  GDRIVE=""
  if [ -n "${GDRIVE_TARGET:-}" ] && [ -d "$GDRIVE_TARGET" ]; then
    GDRIVE="$GDRIVE_TARGET"
  else
    shopt -s nullglob 2>/dev/null
    for gd in "$HOME"/Library/CloudStorage/GoogleDrive-*; do
      [ -d "$gd" ] || continue
      for sub in "$gd/My Drive" "$gd/내 드라이브" "$gd"; do
        [ -d "$sub" ] || continue
        PROBE="$sub/.write_test_$$"
        if (touch "$PROBE" 2>/dev/null && rm -f "$PROBE"); then
          GDRIVE="$sub"
          break 2
        fi
      done
    done
    if [ -z "$GDRIVE" ]; then
      for p in "$HOME/Google Drive/My Drive" "/Volumes/GoogleDrive/My Drive" "$HOME/Google Drive"; do
        [ -d "$p" ] || continue
        PROBE="$p/.write_test_$$"
        if (touch "$PROBE" 2>/dev/null && rm -f "$PROBE"); then
          GDRIVE="$p"
          break
        fi
      done
    fi
  fi

  if [ -z "$GDRIVE" ]; then
    echo "  ⚠️  Google Drive 폴더를 못 찾음 — 스킵"
    echo "     수동 지정: GDRIVE_TARGET='~/...경로...' bash $0"
  else
    TARGET="$GDRIVE/blog/12시에만나요/$DATE"
    mkdir -p "$TARGET"
    echo "  📂 대상: $TARGET"

    # 본문 .md (해당 날짜) — set -u 환경에서 안전하게 처리
    COUNT_MD=0
    shopt -s nullglob
    for f in "$BLOG"/${DATE}*.md; do
      if [ -f "$f" ] && [[ "$f" != *.bak ]]; then
        cp "$f" "$TARGET/" && COUNT_MD=$((COUNT_MD + 1))
      fi
    done
    shopt -u nullglob
    if [ "${COUNT_MD:-0}" -gt 0 ]; then
      echo "  · 본문 .md ${COUNT_MD}개"
    fi

    # 인포그래픽 PNG
    if [ -d "$BLOG/images/$DATE" ]; then
      PNG_DIR="$TARGET/images"
      mkdir -p "$PNG_DIR"
      cp "$BLOG/images/$DATE"/*.png "$PNG_DIR/" 2>/dev/null
      COUNT_PNG=$(ls "$PNG_DIR"/*.png 2>/dev/null | wc -l | tr -d ' ')
      echo "  · PNG $COUNT_PNG장"
    fi

    # copy_tool.html
    COPY_TOOL="$BLOG/output/${DATE}_copy_tool.html"
    if [ -f "$COPY_TOOL" ]; then
      cp "$COPY_TOOL" "$TARGET/"
      echo "  · copy_tool.html"
    fi

    echo "  ✅ 미러링 완료 (구글 드라이브 앱이 자동 업로드)"
  fi
fi

# ── ③ 텔레그램 알림 (옵션) ─────────────────────────
if [ -f "$BLOG/scripts/notify_telegram.sh" ]; then
  echo ""
  echo "📲 [3/3] 텔레그램 알림..."
  TG_MSG="✅ *${PREFIX}* 완료 (${DATE})
📂 GDrive: ${GDRIVE:+미러링됨}${GDRIVE:-스킵}
🚀 Git: 푸시됨
📋 copy_tool: output/${DATE}_copy_tool.html"
  bash "$BLOG/scripts/notify_telegram.sh" "$TG_MSG" 2>/dev/null || true
fi

echo ""
echo "──────────────────────────────────────────────"
