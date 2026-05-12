#!/bin/bash
cd "/Users/chanwook/Documents/Claude/Projects/블로그"
echo "📤 GitHub에 이미지 푸시 중..."
git push origin HEAD
echo ""
if [ $? -eq 0 ]; then
  echo "✅ 푸시 완료!"
  echo ""
  echo "📷 이미지 URL (네이버 블로그에서 사용):"
  echo "https://raw.githubusercontent.com/wook-44/blog_project/main/images/2026-04-27/img1_market_status.png"
  echo "https://raw.githubusercontent.com/wook-44/blog_project/main/images/2026-04-27/img2_market_structure.png"
  echo "https://raw.githubusercontent.com/wook-44/blog_project/main/images/2026-04-27/img3_psychology.png"
  echo "https://raw.githubusercontent.com/wook-44/blog_project/main/images/2026-04-27/img4_checklist.png"
  echo "https://raw.githubusercontent.com/wook-44/blog_project/main/images/2026-04-27/img5_summary.png"
else
  echo "❌ 푸시 실패 — 아래 명령어로 수동 실행해주세요:"
  echo "  cd /Users/chanwook/Documents/Claude/Projects/블로그 && git push origin HEAD"
fi
echo ""
read -p "엔터를 눌러 닫기..."
