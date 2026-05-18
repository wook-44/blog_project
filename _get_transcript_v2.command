#!/bin/bash
# yt-dlp로 자막 직접 받기
cd "$(dirname "$0")"
URL="https://www.youtube.com/watch?v=nSs3vOKKI2E"
DATE="2026-05-15"
OUT_DIR="data/transcripts"

mkdir -p "$OUT_DIR"

echo "🔍 yt-dlp 확인..."
if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "❌ yt-dlp 미설치. 설치: pip3 install --break-system-packages yt-dlp"
  pip3 install --break-system-packages yt-dlp 2>&1 | tail -3
fi

echo ""
echo "📥 자막 시도 (수동 → 자동 → 영상 정보)..."

cd "$OUT_DIR"

# 1차: 수동 한국어 자막
yt-dlp --skip-download --write-sub --sub-lang ko --sub-format vtt \
  --output "${DATE}_%(title).40s.%(ext)s" "$URL" 2>&1 | tail -5

# 2차: 자동 한국어 자막
yt-dlp --skip-download --write-auto-sub --sub-lang ko --sub-format vtt \
  --output "${DATE}_%(title).40s.%(ext)s" "$URL" 2>&1 | tail -5

# 결과 정리
cd ..
cd ..
VTT=$(ls "$OUT_DIR"/${DATE}_*.vtt 2>/dev/null | head -1)
if [ -n "$VTT" ]; then
  TXT="$OUT_DIR/${DATE}_transcript_v2.txt"
  # VTT → 순수 텍스트
  python3 -c "
import re, sys
with open('$VTT', encoding='utf-8') as f:
    lines = f.read().splitlines()
out = []
for ln in lines:
    if re.match(r'\d+:\d+:\d+', ln) or '-->' in ln or ln.strip() == '' or ln.startswith('WEBVTT') or ln.startswith('Kind:') or ln.startswith('Language:'):
        continue
    # tag 제거
    ln = re.sub(r'<[^>]+>', '', ln).strip()
    if ln and (not out or ln != out[-1]):
        out.append(ln)
print('\n'.join(out))
" > "$TXT"
  SIZE=$(wc -c < "$TXT" | tr -d ' ')
  LINES=$(wc -l < "$TXT" | tr -d ' ')
  echo "✅ 변환 완료: $TXT (${SIZE} bytes / ${LINES} lines)"
  python3 notify.py "📝 <b>5/15 자막 yt-dlp v2 성공</b>
${SIZE} bytes / ${LINES} lines
다음: Claude가 본문 작성"
else
  echo "❌ vtt 파일 없음 — 자막 미제공 영상일 수 있음"
  python3 notify.py "⚠️ <b>5/15 자막 yt-dlp 실패</b>
자막 없는 영상일 가능성. 영상 제목·설명 기반으로 본문 작성 시도."
fi

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
