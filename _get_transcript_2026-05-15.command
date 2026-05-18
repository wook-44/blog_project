#!/bin/bash
# 5/15 영상 자막 추출
cd "$(dirname "$0")"
URL="https://www.youtube.com/watch?v=nSs3vOKKI2E"
DATE="2026-05-15"

echo "🎬 5/15 영상 자막 추출 시작..."
python3 scripts/get_youtube_transcript.py "$URL" "$DATE"
EXIT=$?

OUT="data/transcripts/${DATE}_transcript.txt"
if [ -f "$OUT" ]; then
  SIZE=$(wc -c < "$OUT" | tr -d ' ')
  LINES=$(wc -l < "$OUT" | tr -d ' ')
  echo "✅ 저장 완료: $OUT (${SIZE} bytes / ${LINES} lines)"
  python3 notify.py "📝 <b>5/15 자막 추출 완료</b>
${SIZE} bytes / ${LINES} lines
다음: 본문 작성 시작"
else
  echo "❌ 추출 실패 (exit $EXIT)"
  python3 notify.py "❌ <b>5/15 자막 추출 실패</b>
exit $EXIT"
fi

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
