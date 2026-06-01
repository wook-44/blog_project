#!/bin/bash
# 자동 생성: 2026-05-29 블로그 GitHub 푸시 위임 스크립트
# 샌드박스에서 git 락 파일을 unlink할 수 없어 커밋이 완료되지 못함.
# 맥에서 이 파일을 더블클릭하면 오늘 산출물을 정리·커밋·푸시한다.
set -e
BASE="/Users/chanwook/Documents/Claude/Projects/블로그"
cd "$BASE"

echo "🧹 stale 락 정리..."
rm -f .git/index.lock .git/HEAD.lock .git/*.lock 2>/dev/null || true
rm -f .git/index.lock.stale-* .git/index.lock.bak* .git/index.lock.del* .git/HEAD.lock.* 2>/dev/null || true
rm -f .git/objects/*/tmp_obj_* 2>/dev/null || true

echo "📤 git_push_daily.sh 실행 (2026-05-29)..."
bash "$BASE/scripts/git_push_daily.sh" 2026-05-29

echo ""
echo "✅ 완료. 이 창은 닫아도 됩니다."
