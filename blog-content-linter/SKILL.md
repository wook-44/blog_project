---
name: blog-content-linter
description: |
  네이버 주식 블로그 포스트의 톤북 v1 룰 준수 여부를 검사·리포팅·자동 보정하는 스킬.
  제목 길이/키워드 위치, 첫 100자 후킹, 태그 30개 풀, 영상 메타 누수, 시리즈 내부 링크,
  본문 분량, 투자 주의 문구, 인포그래픽 사양을 한 번에 점검한다.

  다음 상황에서 반드시 이 스킬을 사용한다:
  - "블로그 검수해줘", "이 글 톤북 룰 통과해?", "발행 전에 린트 돌려줘"
  - "지난 글들 일괄 점검해줘", "4-5월 포스트 SEO 다시 봐줘"
  - "이 포스트 제목·태그 리라이팅 도와줘"
  - 사용자가 발행 직전 블로그 .md 파일을 보여주며 품질 확인을 요청할 때
---

# blog-content-linter

'12시에 만나요' 블로그 시리즈의 **단일 품질 게이트** 역할.
`stock-youtube-blog-writer/references/tone-book.md`를 SoT로 참조하며,
린트 → 자동 보정 제안 → 통과 시 발행, 실패 시 재작성 트리거.

## 트리거 시점

1. **단건 발행 직전** — 새로 만든 .md를 검사
2. **일괄 백필** — `--all` 옵션으로 4-5월 누적분 점검
3. **사용자 명시 요청** — "이 글 검수해줘", "톤북 룰 확인"

## 의존 자원

- `scripts/agents/00_title_tag_linter.py` — 핵심 린터
- `scripts/agents/09_series_linker.py` — 시리즈 링크 보완
- `scripts/agents/08_quality_checker.py` — 종합 품질 점수 (Gemini, 선택)
- `stock-youtube-blog-writer/references/tone-book.md` — 룰 SoT

## 실행 흐름

### A. 단건 검수
```bash
cd /Users/chanwook/Documents/Claude/Projects/블로그
python scripts/agents/00_title_tag_linter.py 2026-05-13-*.md
```

출력 예시:
```
✅ PASS  2026-05-13-kospi-8000-touch.md
  제목(30자) · 태그(31개) · 본문(2,847자)
  ✓ [T1] 제목 길이 OK (30자)
  ✓ [T3] 메인 키워드 '코스피' 앞쪽 배치 OK (0자)
  ✓ [H1] 첫 후킹 문단 길이 OK (128자)
  ✓ [G1] 태그 수 OK (31개)
```

### B. 일괄 백필 (지난 글 점검)
```bash
python scripts/agents/00_title_tag_linter.py --all
```

플랫폼 전체 .md를 스캔, 통과/실패 통계 출력.

### C. 자동 보정 시나리오

린터 실패 시 Claude가 다음 순서로 보정 제안:

1. **제목 리라이팅** (T1/T2/T3 위반 시)
   - 현재 제목 → 30자 이내 / 키워드 앞 / 날짜 접두어 제거
   - 후보 3개 제시

2. **첫 100자 후킹 추가** (H1/H2/H3 위반 시)
   - 영상 정보 테이블을 본문 최하단으로 이동
   - 제목 직후에 결론 + 키워드 2회 + 숫자 1개 포함 문단 삽입

3. **태그 30개 풀 (G1/G2 위반 시)**
   - 메인 5 + 서브 10 + 롱테일 15 템플릿 적용
   - 본문 키워드에서 추출 + 시리즈 키워드 보강

4. **시리즈 링크 (S1 위반 시)**
   - `09_series_linker.py --apply` 자동 실행

5. **투자 주의 문구 (B2 위반 시)**
   - 본문 최하단 표준 문구 자동 추가

## 통과 기준

- 린터 11개 검사 항목 **전부 통과** (issues 0개)
- (선택) `08_quality_checker.py` 70점 이상

## 백필 워크플로우 (4-5월 14편 일괄 보정)

1. `python scripts/agents/00_title_tag_linter.py --all --json > lint_report.json`
2. Claude가 lint_report.json을 읽고 실패 항목별로 그룹핑
3. 우선순위(T1/T2/T3 → H1/H2 → G1/G2) 순으로 일괄 수정 PR/커밋
4. 백업: 모든 수정은 `.bak` 파일 동반

## 안전 룰

- 본문 의미를 바꾸지 않는다 — 제목/태그/구조만 손댐
- 자동 보정 후 반드시 사용자에게 diff 확인받기
- 영상 정보 테이블은 삭제하지 않고 본문 최하단 부록으로 이동
- 인사이트(💡) 텍스트는 유지, attribution만 제거

## 출력 위치

- 린트 리포트: `output/lint/{date}_lint_report.json`
- 보정 백업: `{원본}.bak`
- 일괄 요약: `output/lint/{date}_batch_summary.md`

## 톤북 변경 시

`tone-book.md`가 업데이트되면 린터 임계값(`TITLE_MIN`, `TAGS_MIN` 등)도
함께 수정해야 한다. 두 파일은 항상 동기화.
