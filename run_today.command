#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# run_today.command — 12시에 만나요 블로그 자동 발행 단일 entrypoint
#  1) 영상 자막 수집      (수동 또는 transcript 캐시)
#  2) 본문 .md 생성       (Claude/외부 — 이 스크립트는 점검만)
#  3) 인포그래픽 PNG 생성 (generate_infographics.py)
#  4) 제목·태그 린터       (00_title_tag_linter.py --strict)
#  5) 시리즈 내부 링크     (09_series_linker.py --apply)
#  6) 품질 게이트          (08_quality_checker.py — 70점 미만 차단)
#  7) 이미지 복사 도구      (generate_copy_tool.py)
#  실패 단계에서 즉시 정지.
# ─────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

DATE="${1:-$(date +%Y-%m-%d)}"
SLUG="${2:-}"
BLOG_DIR="$(pwd)"
PYTHON="${PYTHON:-python3}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📅  날짜: $DATE"
echo "  📁  작업 폴더: $BLOG_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 본문 .md 자동 탐색 ────────────────────────────────
POST_PATH=$(ls -t "$BLOG_DIR"/${DATE}*.md 2>/dev/null | head -1)
if [ -z "$POST_PATH" ]; then
  echo ""
  echo "❌  본문 파일을 찾을 수 없습니다: ${DATE}*.md"
  echo "    Claude에게 '오늘 블로그 써줘' 요청 후 다시 실행하세요."
  exit 1
fi
echo ""
echo "📝 본문 파일: $(basename "$POST_PATH")"

# ── 1. 인포그래픽 (있으면 스킵) ───────────────────────
IMG_DIR="$BLOG_DIR/images/$DATE"
if [ ! -f "$IMG_DIR/${DATE}-market.png" ]; then
  echo ""
  echo "🎨 [Step 1] 인포그래픽 생성 중..."
  if [ -f "$BLOG_DIR/stock-youtube-blog-writer/references/generate_infographics.py" ]; then
    # 호출 측에서 --data JSON 을 미리 준비했어야 함
    echo "   ⚠️  인포그래픽 데이터(JSON)는 본문 생성 단계에서 미리 만들어두세요."
    echo "       images/$DATE/ 폴더에 PNG 3종 직접 배치도 가능."
  fi
else
  echo ""
  echo "🎨 [Step 1] 인포그래픽 이미 존재 — 스킵"
fi

# ── 2. 제목·태그 린터 ─────────────────────────────────
echo ""
echo "🔍 [Step 2] 제목·태그·후킹 린터..."
$PYTHON "$BLOG_DIR/scripts/agents/00_title_tag_linter.py" "$POST_PATH" --strict || {
  echo ""
  echo "❌ 린터 실패 — 톤북 룰 위반. 본문 수정 후 다시 실행."
  exit 1
}

# ── 3. 시리즈 내부 링크 ────────────────────────────────
echo ""
echo "🔗 [Step 3] 시리즈 내부 링크 점검..."
$PYTHON "$BLOG_DIR/scripts/agents/09_series_linker.py" "$POST_PATH" --apply || true

# ── 4. 품질 게이트 ────────────────────────────────────
echo ""
echo "🛡️  [Step 4] 품질 게이트 (08_quality_checker)..."
# 08은 meta JSON을 받는 구조 → 간이 메타 생성
META_TMP=$(mktemp /tmp/quality_meta.XXXXXX.json)
TITLE=$(grep -m1 "^# " "$POST_PATH" | sed 's/^# *//')
cat > "$META_TMP" <<EOF
{
  "video_id": "$DATE",
  "title": "$TITLE",
  "focus_keyword": "코스피",
  "meta_description": "$(grep -m1 -A1 "^# " "$POST_PATH" | tail -1 | head -c 160)",
  "tags": $(grep -oE '#[가-힣A-Za-z0-9]+' "$POST_PATH" | sed 's/#//' | jq -R . | jq -s . 2>/dev/null || echo '[]'),
  "content_path": "$POST_PATH"
}
EOF
if [ -n "$GEMINI_API_KEY" ]; then
  $PYTHON "$BLOG_DIR/scripts/agents/08_quality_checker.py" "$META_TMP" naver || {
    echo "❌ 품질 게이트 미달. 본문/메타 수정 후 다시 실행."
    rm -f "$META_TMP"
    exit 1
  }
else
  echo "   ⚠️  GEMINI_API_KEY 미설정 — 품질 게이트 스킵 (린터만 통과)"
fi
rm -f "$META_TMP"

# ── 5. 이미지 복사 도구 생성 ──────────────────────────
echo ""
echo "📋 [Step 5] 이미지 복사 도구 생성..."
if [ -f "$BLOG_DIR/scripts/generate_copy_tool.py" ]; then
  $PYTHON "$BLOG_DIR/scripts/generate_copy_tool.py" --date "$DATE" || {
    echo "⚠️  copy_tool 생성 실패"
  }
else
  echo "   ⚠️  generate_copy_tool.py 없음 — 스킵"
fi

# ── 완료 ──────────────────────────────────────────────
COPY_TOOL=$(ls -t "$BLOG_DIR"/output/*${DATE}*copy_tool.html 2>/dev/null | head -1)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 완료!"
echo ""
echo "  📝 본문:        $(basename "$POST_PATH")"
echo "  🎨 이미지:      images/$DATE/"
[ -n "$COPY_TOOL" ] && echo "  📋 복사도구:    $(basename "$COPY_TOOL")"
echo ""
echo "  다음 단계: 복사도구 HTML을 브라우저로 열어 네이버에 순서대로 붙여넣기"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Finder/터미널 자동 종료 안 함 — 결과 확인용 대기
read -p "Enter 키를 누르면 종료... " _
