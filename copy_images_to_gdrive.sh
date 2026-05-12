#!/bin/bash
# 블로그 이미지를 Google Drive 동기화 폴더로 날짜별 복사

BLOG_ROOT="/Users/chanwook/Documents/Claude/Projects/블로그"
GDRIVE_ROOT="/Users/chanwook/Documents/Google_drive"

# 날짜별 폴더 복사
for DATE_DIR in "$BLOG_ROOT"/20*; do
  if [ -d "$DATE_DIR" ]; then
    DATE=$(basename "$DATE_DIR")
    DEST="$GDRIVE_ROOT/$DATE"
    mkdir -p "$DEST"
    cp "$DATE_DIR"/*.jpg "$DEST/" 2>/dev/null
    echo "✅ $DATE → Google Drive 복사 완료 ($(ls "$DEST"/*.jpg 2>/dev/null | wc -l)개)"
  fi
done

echo ""
echo "Google Drive 동기화 대기 중... 완료되면 Claude에게 알려주세요!"
