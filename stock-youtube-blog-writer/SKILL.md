---
name: stock-youtube-blog-writer
description: |
  유튜브 주식/투자 영상을 분석해서 블로그 포스트와 섹션별 인포그래픽 PNG를 자동 생성하는 스킬.
  '12시에 만나요' 재생목록(PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX)의 최신 영상을 Claude in Chrome으로 접근해
  5개 파이프라인 에이전트가 순차 실행된다: 수집 → 분석 → 블로그작성 → 이미지생성 → 저장

  다음 상황에서 반드시 이 스킬을 사용한다:
  - "유튜브 주식 블로그 써줘", "오늘 영상 분석해줘", "12시에 만나요 블로그"
  - 유튜브 URL + 블로그/분석 요청이 함께 올 때
  - 재생목록에서 새 영상을 찾아 블로그를 만들어달라는 요청
---

# stock-youtube-blog-writer

유튜브 주식 영상을 분석해서 **분석 아카이브(Google Sheets)**, **발행용 블로그(Notion + 로컬 .md)**, **섹션별 인포그래픽 PNG**, **플랫폼별 SEO 최적화본**을 자동 생성하는 6단계 파이프라인 스킬.

## 파이프라인 구조

```
[에이전트 1] 수집 에이전트
  Claude in Chrome → YouTube 재생목록 접근 → 최신 영상 자막 추출
      ↓ 전달: 자막 텍스트 + 메타데이터
[에이전트 2] 분석 에이전트
  3개 카테고리 심층 분석 → 구조화된 분석 데이터 생성
      ↓ 전달: 분석 JSON 데이터
[에이전트 3] 블로그 작성 에이전트
  분석 데이터 → 인사이트 레이어 추가 → 발행용 블로그 초안 생성
      ↓ 전달: 블로그 마크다운 + 섹션별 핵심 데이터
[에이전트 4] 이미지 생성 에이전트
  섹션별 핵심 데이터 → 인포그래픽 PNG 4장 생성
      ↓ 전달: PNG 파일 경로 목록
[에이전트 5] SEO 전략 에이전트
  블로그 원본 → 네이버·티스토리·브런치 플랫폼별 최적화 변형본 생성
      ↓ 전달: 플랫폼별 제목/태그/메타/도입부
[에이전트 6] 저장 에이전트
  블로그 + PNG + SEO 변형본 → Google Sheets / Notion / 로컬 .md 동시 저장
```

각 에이전트는 이전 에이전트의 출력을 입력으로 받아 순차 실행된다. 한 에이전트가 실패하면 오류를 기록하고 다음 에이전트로 넘어간다 (저장 에이전트 제외 — 저장 에이전트는 가능한 모든 목적지에 저장 시도).

---

## 에이전트 1: 수집 에이전트

**목적**: YouTube 영상 접근 및 원본 데이터 수집

### 실행 순서 (Claude in Chrome 필수)

1. Chrome으로 재생목록 열기: `https://www.youtube.com/playlist?list=PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX`
2. 가장 최근 업로드된 영상 확인 후 클릭
3. 자막 추출:
   - 영상 하단 `...` → `자막(스크립트) 열기` 또는 `Show transcript` 클릭
   - 전체 자막 텍스트 복사
4. 메타데이터 수집: 영상 제목, 채널명, 출연자 목록, 업로드 날짜, URL, 영상 길이

### 출력 (에이전트 2로 전달)
```
{
  "title": "영상 제목",
  "channel": "채널명",
  "speakers": ["출연자1", "출연자2"],
  "upload_date": "YYYY-MM-DD",
  "url": "https://...",
  "duration": "HH:MM",
  "transcript": "전체 자막 텍스트..."
}
```

### 실패 처리
- Chrome 비활성화 시: 사용자에게 영상 URL 또는 자막 텍스트 직접 요청
- 자막 없는 경우: 영상 설명란 + 상위 댓글 10개로 대체, `transcript_source: "description+comments"` 표기

---

## 에이전트 2: 분석 에이전트

**목적**: 자막을 3개 카테고리로 심층 분석

### ⚠️ 골든룰 — 절대 준수

**수치의 구체성**: 모호한 요약 금지
- ❌ "구글은 AI에 대규모 투자를 하고 있다"
- ✅ "구글은 전년 대비 100% 늘린 1,900억 달러를 2025년에 집행한다"

**출처 명시**: 발언마다 "누가" 말했는지 표기
**타임스탬프**: 중요 발언에 영상 내 시간 기록 (예: 12:34)

### 카테고리 분석

**[카테고리 1] 시장 분석 및 투자 전략**
- 전체 흐름 요약
- 출연자별 사례(Case): 구체적 수치 + 에피소드
- 대응 지침(Direction): 실행 가능한 투자 행동

**[카테고리 2] 투자 심리 및 행동 교정**
- 전체 흐름 요약
- 사례(Case): 심리 함정의 구체적 예시
- 대응 지침(Direction): 교정 방법론

**[카테고리 3] 종합 요약 및 팁**
- 핵심 메시지 3~5개 (번호 목록)
- 출연자 공통 강조 포인트
- 오늘 당장 적용 가능한 팁

### 출력 (에이전트 3으로 전달)
분석된 데이터를 구조화된 형태로 출력. 각 카테고리별 요약/사례/지침 포함.

---

## 에이전트 3: 블로그 작성 에이전트

**목적**: 분석 데이터 + 인사이트 레이어 → 발행용 블로그 초안

### 작성 원칙
- **톤**: 1인칭 분석 일지. 단순 요약이 아닌 "내가 이 정보를 어떻게 해석하는가"가 핵심
- **독자**: 투자에 관심 있는 일반 성인 + 게임/앱 기획자 관점을 기대하는 독자
- **SEO**: 제목 후보 3개 → 검색 의도 최적 선택, 메타 디스크립션 80자 이내

### 블로그 구조

`references/blog-template.md`를 읽고 해당 구조에 맞게 작성한다.

### 섹션별 인포그래픽용 데이터 추출

블로그 작성과 동시에 각 섹션의 핵심 데이터를 추출해 이미지 에이전트에 전달한다:

```
infographic_data: {
  "market": {
    "title": "시장 분석 & 투자 전략",
    "key_stat": "가장 임팩트 있는 수치 1개 (예: +15.3%)",
    "points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
    "color": "#1B4F72"
  },
  "psychology": {
    "title": "투자 심리 & 행동 교정",
    "key_stat": "심리 관련 수치 또는 키워드",
    "points": ["함정 1", "함정 2", "교정법"],
    "color": "#6C3483"
  },
  "summary": {
    "title": "오늘의 핵심 포인트",
    "points": ["포인트 1", "포인트 2", "포인트 3", "포인트 4"],
    "color": "#1E8449"
  },
  "insight": {
    "title": "내 인사이트",
    "quote": "블로그 인사이트 섹션의 핵심 한 문장 (50자 이내)",
    "color": "#B7950B"
  }
}
```

---

## 에이전트 4: 이미지 생성 에이전트

**목적**: 섹션별 인포그래픽 PNG 4장 생성

### 실행 방법

`references/generate_infographics.py` 스크립트를 실행한다:

```bash
cd [블로그 폴더 경로]
pip install pillow matplotlib --break-system-packages -q
python stock-youtube-blog-writer/references/generate_infographics.py \
  --date YYYY-MM-DD \
  --data '[infographic_data JSON]' \
  --output [블로그 폴더]/images/YYYY-MM-DD/
```

### 출력 파일 (4장)
- `YYYY-MM-DD-market.png` — 시장 분석 & 투자 전략
- `YYYY-MM-DD-psychology.png` — 투자 심리 & 행동 교정
- `YYYY-MM-DD-summary.png` — 오늘의 핵심 포인트
- `YYYY-MM-DD-insight.png` — 내 인사이트

각 이미지 크기: 1200×630px (SNS/블로그 OG 이미지 최적 사이즈)

---

## 에이전트 5: 저장 에이전트

**목적**: 모든 결과물(블로그 + PNG)을 3개 목적지에 저장

### 저장 목적지

**① Google Sheets (분석 아카이브)**
- 위치: Google Drive `blog` 폴더
- 파일명: `12time / YYYY-MM-DD`
- 형식: **Google Spreadsheet** (Docs/Word 절대 금지)
- 컬럼: A(카테고리) / B(항목) / C(내용)

**② 로컬 파일**
- 블로그: `/Users/chanwook/Documents/Claude/Projects/블로그/YYYY-MM-DD-[슬러그].md`
- PNG: `/Users/chanwook/Documents/Claude/Projects/블로그/images/YYYY-MM-DD/` 폴더에 4장

**③ Notion**
- Notion MCP → 블로그 데이터베이스에 새 페이지 생성
- 제목, 날짜, 태그, 본문, 이미지 첨부
- 상태: "Draft"

### 저장 실패 처리
- Google Sheets 실패 → 로컬 CSV로 대체 저장
- Notion 실패 → 로컬 저장만으로 진행, 사용자에게 알림
- 어떤 목적지든 최소 로컬 저장은 반드시 완료

---

## 완료 기준

- [ ] Google Sheets 파일 생성 (`12time / YYYY-MM-DD`)
- [ ] 로컬 .md 블로그 파일 저장
- [ ] PNG 4장 로컬 저장 (`images/YYYY-MM-DD/`)
- [ ] Notion 페이지 생성 (실패 허용)
