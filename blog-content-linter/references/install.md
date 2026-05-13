# blog-content-linter 설치 방법

이 스킬은 `/Users/chanwook/Documents/Claude/Projects/블로그/blog-content-linter/` 에 소스가 있다.
Cowork 플러그인으로 정식 등록하려면 두 가지 방법:

## 방법 1. Cowork 플러그인 등록 (권장)

Claude에게 다음 요청:
> "이 폴더(blog-content-linter)를 Cowork 플러그인으로 만들어서 설치해줘"

→ `create-cowork-plugin` 스킬이 동작해 `.plugin` 번들 생성·설치 안내.

## 방법 2. 수동 복사 (빠른 방법)

기존 stock-youtube-blog-writer 스킬이 설치된 폴더에 같이 두기:

```bash
# 호스트 머신의 Cowork 플러그인 폴더 (Mac 기준)
# 정확한 경로는 시스템마다 다를 수 있음
SKILL_HOST="$HOME/Library/Application Support/Claude/plugins/anthropic-skills/skills"
cp -r "/Users/chanwook/Documents/Claude/Projects/블로그/blog-content-linter" "$SKILL_HOST/"
```

설치 후 Claude를 재시작하면 `anthropic-skills:blog-content-linter` 로 자동 발견됨.

## 방법 3. 등록 없이 사용 (현재 상태)

스킬이 정식 등록되지 않아도, 이 프로젝트 폴더에서 작업할 때 Claude는:
- 사용자가 "블로그 검수해줘" 등을 말하면
- `blog-content-linter/SKILL.md` 를 찾아 룰에 따라 동작

→ 실제 차이: 정식 등록 시 `<available_skills>` 목록에 노출되어 트리거 정확도가 더 높아짐.
