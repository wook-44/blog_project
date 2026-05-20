#!/bin/bash
# 2026-05-20 자동 생성 풀 파이프라인 (호스트 실행 전용)
# - PNG 재변환 (Chrome headless로 한글/foreignObject 제대로 렌더)
# - copy_tool.html 재생성 (정상 PNG 반영)
# - daily/ 폴더 정리
# - git commit + push

set -e
TODAY="2026-05-20"
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "🗓️  대상 날짜: $TODAY"
echo ""

# 1) HTML → PNG (Chrome headless, 한글 정상)
echo "🖼️  Step 1: HTML → PNG 변환"
python3 scripts/html_to_png.py "$TODAY" 2>&1 | tail -10
echo ""

# 2) copy_tool.html 재생성 (정상 PNG 임베드)
echo "📄 Step 2: copy_tool.html 재생성"
python3 scripts/generate_copy_tool.py "$TODAY" 2>&1 | tail -5
echo ""

# 3) v2 유튜브 버튼 재주입
echo "📺 Step 3: 유튜브 설명란 버튼 주입"
python3 << 'PY'
from pathlib import Path
import re, json
html_path = Path("output/2026-05-20_copy_tool.html")
seo_path = Path("2026-05-20_seo.md")
html = html_path.read_text(encoding="utf-8")
seo = seo_path.read_text(encoding="utf-8")
m = re.search(r"\*\*한 줄.*?\*\*\s*\n(.+?)\n", seo)
yt_line = m.group(1).strip() if m else "오늘 영상 풀 분석"
if "ytBox" in html:
    print("이미 주입됨, 스킵")
else:
    inject = f'''
<div style="margin-top:10px;padding:14px;background:rgba(6,182,212,0.10);border:2px solid #06b6d4;border-radius:10px;">
  <div style="font-size:13px;color:#06b6d4;font-weight:700;margin-bottom:8px;">▶ 유튜브 설명란용 한 줄 (v2 — 외부 유입 ↑)</div>
  <div id="ytBox" style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:14px;line-height:1.5;word-break:break-all;">{yt_line}</div>
  <button class="btn" style="background:#06b6d4;color:#fff;margin-top:10px;" onclick="copyPlain('ytBox','toastYt')">📺 유튜브 설명란용 한 줄 복사</button>
  <div id="toastYt" class="toast" style="display:none;">복사됨!</div>
</div>
'''
    target = '<button class="btn btn-text" style="background:#8b5cf6;margin-top:10px;" onclick="copyPlain(\'titleBox\',\'toastTitle\')">📋 제목 복사</button>'
    if target in html:
        html = html.replace(target, target + inject)
    else:
        html = html.replace("</body>", inject + "\n</body>")
    html_path.write_text(html, encoding="utf-8")
    print("주입 완료")
PY
echo ""

# 4) daily/ 폴더 정리 + git push
echo "📤 Step 4: daily/ 폴더 정리 + GitHub 푸시"
bash scripts/git_push_daily.sh "$TODAY"

echo ""
echo "✅ 전체 파이프라인 완료"
read -p "엔터를 눌러 닫기..."
