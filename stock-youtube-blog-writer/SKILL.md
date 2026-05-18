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

## ⚠️ 모든 에이전트는 톤북을 먼저 읽는다

`references/tone-book.md` — 제목 룰, 첫 100자 후킹 공식, 태그 30개 템플릿,
인포그래픽 여백/카드 룰, 영상 메타 처리, 시리즈 내부 링크 규칙의 단일 SoT.

발행 직전 `scripts/agents/00_title_tag_linter.py`가 톤북 룰을 강제 검사하며,
실패 시 발행 차단. 자세한 검수는 `blog-content-linter` 스킬 참조.

### 🆕 톤북 v2 (2026-05-18~) — 트래픽 성장 룰

본 스킬의 모든 에이전트는 다음 v2 룰을 반드시 따른다 (상세는 톤북 §1·§3·§10~§13):

1. **제목**: 종목명/지수 키워드를 앞 12자 이내에 강제. 브랜드 키워드("12시에 만나요") 제목 노출 금지. **3안 생성 후 키워드 매트릭스로 평가**.
2. **본문**: `## 📍 이 글에서 다루는 것`(목차 3~5줄) + `## 🔗 관련 종목 한눈에`(3~5개 표) 섹션 신설. 최저 분량 2,500자.
3. **에이전트 2.5 추가**: 영상에서 추출된 핵심 종목의 **현재가/등락률**을 네이버 금융(WebFetch)으로 보강하여 에이전트 3·4에 전달.
4. **인포그래픽 market**: stats 첫 카드를 **종목 스냅샷**(종목명+가격+등락률)으로. 한국 관례 컬러(상승=빨강 #EF4444, 하락=파랑).
5. **인포그래픽 summary**: `related_chips` 필드로 관련 종목 칩 row 노출.
6. **SEO 메타**: 태그 앞 5개에 종목/지수 키워드 3개 이상. 유튜브 영상 설명란용 한 줄 + 고정댓글용 3줄도 함께 생성.
7. **HTML 복붙 도구**: 8번 버튼(시안색) "유튜브 설명란용 한 줄 복사" 추가.

시황 요약(15:30)은 별도 스킬/스케줄 `daily-market-summary`로 분리. 본 스킬은 영상 분석 본편(17:30)만 담당.

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
  섹션별 핵심 데이터 → 인포그래픽 PNG 3~5장 가변 생성
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

블로그 작성과 동시에 각 섹션의 핵심 데이터를 추출해 이미지 에이전트에 전달한다.

**개수 규칙 (2026-05-15 갱신): PNG는 영상 내용에 따라 3~5장 가변**
- **필수 3개**: `market`, `psychology`, `summary` — 매일 반드시 채움
- **선택 1~2개**: 아래 표의 추가 섹션 중 영상에서 비중 있게 다뤘다면 포함
- `insight`는 항상 데이터에 두되 이미지 생성은 안 함 (본문 텍스트로만 들어감)

| 키 | 언제 추가 | 빌더 | 액센트 색 |
|---|---|---|---|
| `outlook` | 향후 시나리오/관전 포인트가 명확하게 언급된 날 | generic | 청록·보라 |
| `sector` | 섹터 로테이션, 주도주 교체가 메인 테마일 때 | generic | 청록 |
| `risk` | 리스크 시나리오, 회피 종목·패턴이 강조될 때 | generic | 적·주황 |
| `checklist` | 행동 체크리스트(매수/매도 조건) 형태가 있을 때 | generic | 주황 |

같은 날 같은 의미 섹션을 2개 만들지 않는다 (예: outlook+sector 둘 다는 가능, risk+checklist 둘 다는 충돌 — 1개만 선택).

```
infographic_data: {
  // ── 필수 3종 ──────────────────────────────
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

  // ── 선택 0~2종 (해당일에 의미 있을 때만) ──
  "outlook": {
    "title": "전망 & 관전 포인트",
    "hero_value": "단기 시계 키워드", "hero_label": "관전 포인트",
    "stats": [{"value":"수치","label":"라벨","delta":"보조"}],
    "chips": ["관전포인트1","관전포인트2"],
    "points": ["근거 1","근거 2","근거 3"],
    "footer_quote": "전망 한 줄", "footer_author": "발화자"
  },

  // ── 본문 텍스트 전용 (PNG 생성 안 함) ────
  "insight": {
    "title": "내 인사이트",
    "quote": "블로그 인사이트 섹션의 핵심 한 문장 (50자 이내)",
    "color": "#B7950B"
  }
}
```

선택 섹션을 추가할 만큼의 내용이 없으면 그냥 키를 넣지 않는다(빈 dict는 자동 스킵). 억지로 채우지 말 것.

---

## 에이전트 4: 이미지 생성 에이전트

**목적**: 섹션별 인포그래픽 PNG 3~5장 가변 생성 (필수 3 + 선택 0~2)

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

### 출력 파일 (3~5장 가변 — insight는 이미지로 만들지 않음)
필수 3장 (매일 생성):
- `YYYY-MM-DD-market.png` — 시장 분석 & 투자 전략
- `YYYY-MM-DD-psychology.png` — 투자 심리 & 행동 교정
- `YYYY-MM-DD-summary.png` — 오늘의 핵심 포인트

선택 0~2장 (해당일에 infographic_data에 키가 들어있을 때만):
- `YYYY-MM-DD-outlook.png` — 전망/관전 포인트
- `YYYY-MM-DD-sector.png` — 섹터 로테이션
- `YYYY-MM-DD-risk.png` — 리스크 시나리오
- `YYYY-MM-DD-checklist.png` — 행동 체크리스트

각 이미지 크기: **1080×1080 정사각형** (모바일/네이버 최적, 2026-05-13 v3 결정).
상세 스펙은 `references/tone-book.md` §5 참조.

### Mac에서 PNG 변환
샌드박스에 Chrome 없으므로 Mac에서 실행해야 한다:
- 일괄: `run_week3_full.command` 등 .command 더블클릭 (Chrome headless `--window-size=1080,1080`)
- 단건: `python stock-youtube-blog-writer/references/generate_infographics.py --date YYYY-MM-DD --data '...' --output images/YYYY-MM-DD/`
- PNG 사이즈 정상치 280~400KB. 18KB 이하면 fallback(Chrome 실행 실패) — 재실행 필요.

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
- PNG: `/Users/chanwook/Documents/Claude/Projects/블로그/images/YYYY-MM-DD/` 폴더에 3~5장 (그날 infographic_data 키 개수에 따라)

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
- [ ] PNG 3~5장 로컬 저장 (`images/YYYY-MM-DD/`) — 필수 3 + 선택 0~2
- [ ] Notion 페이지 생성 (실패 허용)
