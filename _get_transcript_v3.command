#!/bin/bash
# v3: brew로 yt-dlp 설치 후 자막 시도 + 자동 자막까지
cd "$(dirname "$0")"
URL="https://www.youtube.com/watch?v=nSs3vOKKI2E"
DATE="2026-05-15"
OUT_DIR="data/transcripts"
mkdir -p "$OUT_DIR"

# 1. yt-dlp 확인/설치
if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "📦 yt-dlp 설치 (brew)..."
  if command -v brew >/dev/null 2>&1; then
    brew install yt-dlp 2>&1 | tail -3
  else
    echo "❌ Homebrew도 없음. pipx 시도..."
    if command -v pipx >/dev/null 2>&1; then
      pipx install yt-dlp 2>&1 | tail -3
    fi
  fi
fi

# PATH 갱신
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "❌ yt-dlp 설치 실패. 종료."
  python3 notify.py "❌ <b>yt-dlp 설치 실패</b>"
  read -t 60 || true
  exit 1
fi

echo "✅ yt-dlp 사용 가능: $(yt-dlp --version)"
echo ""

cd "$OUT_DIR"
rm -f "${DATE}_"*.vtt "${DATE}_"*.txt 2>/dev/null

# 2. 수동 한국어 자막
echo "📥 [1차] 수동 한국어 자막..."
yt-dlp --skip-download --write-sub --sub-lang ko --convert-subs vtt \
  --output "${DATE}_manual.%(ext)s" "$URL" 2>&1 | tail -8

# 3. 자동 한국어 자막
echo ""
echo "📥 [2차] 자동 생성 한국어 자막..."
yt-dlp --skip-download --write-auto-sub --sub-lang ko --convert-subs vtt \
  --output "${DATE}_auto.%(ext)s" "$URL" 2>&1 | tail -8

# 4. 결과 정리
cd ..
cd ..
VTT=$(ls "$OUT_DIR"/${DATE}_*.vtt 2>/dev/null | head -1)
if [ -n "$VTT" ]; then
  TXT="$OUT_DIR/${DATE}_transcript_v3.txt"
  python3 -c "
import re
with open('$VTT', encoding='utf-8') as f:
    lines = f.read().splitlines()
out = []
for ln in lines:
    if re.match(r'^\d+:\d+', ln) or '-->' in ln or ln.strip() == '' or ln.startswith('WEBVTT') or ln.startswith('Kind:') or ln.startswith('Language:'):
        continue
    ln = re.sub(r'<[^>]+>', '', ln).strip()
    if ln and (not out or ln != out[-1]):
        out.append(ln)
print('\n'.join(out))
" > "$TXT"
  SIZE=$(wc -c < "$TXT" | tr -d ' ')
  LINES=$(wc -l < "$TXT" | tr -d ' ')
  echo ""
  echo "✅ 변환 완료: $TXT (${SIZE} bytes / ${LINES} lines)"
  echo "── 첫 20줄 ──"
  head -20 "$TXT"
  python3 notify.py "✅ <b>5/15 자막 v3 성공</b>
${SIZE} bytes / ${LINES} lines"
else
  echo "❌ vtt 없음 — 자막 실제 미제공"
  python3 notify.py "⚠️ <b>5/15 자막 미제공 영상</b>"
fi

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
