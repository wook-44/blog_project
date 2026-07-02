#!/bin/bash
# 2026-06-16 린터 통과 수정본을 구글 드라이브 미러 폴더로 다시 복사 + 텔레그램 알림
# (자동 파이프라인이 린터 실패본을 미러링했으므로 수정본으로 갱신)
set -e
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
MIRROR="/Users/chanwook/Library/CloudStorage/GoogleDrive-videokill.us@gmail.com/내 드라이브/blog/12시에만나요/2026-06-16"
cd "$BASE"

mkdir -p "$MIRROR/images"
cp "2026-06-16_blog.md" "$MIRROR/"
cp "2026-06-16_seo.md" "$MIRROR/" 2>/dev/null || true
cp "2026-06-16_sections.json" "$MIRROR/" 2>/dev/null || true
cp "output/2026-06-16_copy_tool.html" "$MIRROR/"
cp images/2026-06-16/*.png "$MIRROR/images/" 2>/dev/null || true
echo "✅ 드라이브 미러 갱신 완료 (구글 드라이브 앱이 자동 업로드)"

python3 notify.py "✅ 2026-06-16 영상 리뷰 블로그 린터 통과본 갱신 완료 (태그·후킹 수정 + copy_tool 재생성)" || echo "(텔레그램 전송 실패 — 무시 가능)"
echo "완료. 창을 닫아도 됩니다."
