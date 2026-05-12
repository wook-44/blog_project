#!/bin/bash
cd "/Users/chanwook/Documents/Claude/Projects/블로그"

# HEAD.lock 제거 (sandbox 실패로 남은 잠금 파일)
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null

echo "📝 변경사항 커밋 중..."
git add scripts/check_playlist.py .github/workflows/youtube-check.yml

git commit -m "fix: check_playlist.py 버그 3종 수정

- Fix 1: SEEN_FILE output/ → data/ (output/은 .gitignore 대상이라 Actions마다 초기화됨)
- Fix 2: RSS playlist_id 방식 제거 (YouTube 미지원 → 항상 실패)
- Fix 3: maxResults=1 → 10 (누락 영상 일괄 감지)
- data/seen_videos.json + seen_videos.txt 병행 저장 (하위 호환)
- 신규 영상 data/new_videos.csv 자동 append"

echo ""
echo "📤 GitHub 푸시 중..."
git push origin HEAD

echo ""
if [ $? -eq 0 ]; then
  echo "✅ 완료! 수정사항이 GitHub에 반영됐습니다."
else
  echo "❌ 푸시 실패"
fi
echo ""
read -p "엔터를 눌러 닫기..."
