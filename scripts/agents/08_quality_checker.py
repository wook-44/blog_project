"""
품질 검증 에이전트 (Agent 08)
===============================
역할: 포스팅 전 최종 품질 검증 — SEO 점수 / 가독성 / 문체 일관성 / 투자 주의 문구
- SEO 점수: 키워드 밀도, 제목 최적화, 메타 길이, 내부 링크 권장 등
- 가독성: 평균 문장 길이, 문단 수, Flesch 한국어 변형 점수
- 문체 일관성: 스타일 가이드 대비 실제 문체 비교
- 통과 기준 미달 시 자동 재작성 트리거
출력: output/quality/{platform}_{video_id}_report.json
"""

import os
import json
import re
import logging
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Quality Agent] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/08_quality_checker.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
OUTPUT_DIR = Path("output/quality")
STYLE_DIR = Path("output/style_guides")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 플랫폼별 최소 글자 수 (v2: 네이버/티스토리 2500으로 상향)
PLATFORM_MIN_LENGTH = {
    "naver": 2500,      # v2: 목차·관련 종목표 추가분 반영
    "tistory": 2500,
    "wordpress": 2000,
    "brunch": 1500,
    "medium": 1500,
}

# 통과 기준 점수 (100점 만점)
PASS_THRESHOLD = 70

# ── 톤북 v2 임계값 ─────────────────────────────────────
TITLE_MIN, TITLE_MAX = 28, 32
TITLE_KW_HEAD_LIMIT = 12
TAG_MIN_COUNT = 30
HOOK_MIN_CHARS = 100

# v2 신설
TAG_HEAD_KW_MIN = 3            # 태그 앞 5개에 종목/지수 키워드 3개 이상
TAG_HEAD_WINDOW = 5
RELATED_TABLE_MIN_ROWS = 3     # 관련 종목표 최소 3행

BRAND_KEYWORDS_FORBIDDEN_IN_TITLE = ["12시에 만나요", "12시에만나요"]
TOC_SECTION_PATTERNS = ["📍 이 글에서 다루는 것", "📍이 글에서 다루는 것"]
RELATED_SECTION_PATTERNS = ["🔗 관련 종목 한눈에", "🔗관련 종목 한눈에"]

VIDEO_META_PHRASES = [
    "📺 영상 정보", "## 영상 정보", "채널 |", "출연자 |",
    "광수 생각", "오후장 한 마디", "방과후 경제교실",
]
MAIN_KW_POOL = [
    "코스피", "코스닥", "삼성전자", "SK하이닉스", "현대차", "기아",
    "LG에너지솔루션", "포스코홀딩스", "셀트리온", "한화에어로스페이스",
    "한미반도체", "HD현대중공업", "KB금융", "신한지주",
    "엔비디아", "테슬라", "구글", "메타", "애플",
    "반도체", "AI", "로봇", "이차전지", "방산", "조선", "원자력",
    "금리", "환율", "유가", "호르무즈", "FOMC", "트럼프",
]


class QualityChecker:
    def __init__(self):
        self.model = model

    # ── 1. SEO 점수 계산 (규칙 기반) ──────────────────
    def calc_seo_score(self, content: str, meta: dict) -> dict:
        score = 100
        issues = []
        suggestions = []

        title = meta.get("title", "")
        focus_kw = meta.get("focus_keyword", "")
        meta_desc = meta.get("meta_description", "")
        tags = meta.get("tags", [])

        # 1) 제목 길이 (톤북 v1: 28~32자)
        title_len = len(title)
        if title_len < TITLE_MIN:
            score -= 15
            issues.append(f"제목이 짧습니다 ({title_len}자). 톤북 권장 {TITLE_MIN}~{TITLE_MAX}자")
        elif title_len > TITLE_MAX:
            score -= 10
            issues.append(f"제목이 깁니다 ({title_len}자). 톤북 권장 {TITLE_MIN}~{TITLE_MAX}자 (모바일 잘림 위험)")
        else:
            suggestions.append(f"✓ 제목 길이 OK ({title_len}자)")

        # 1-b) 날짜 접두어 금지
        if re.match(r"\s*\[?\d{4}[\.\-/]\d{1,2}[\.\-/]\d{1,2}", title):
            score -= 10
            issues.append("제목에 [YYYY.MM.DD] 접두어 — 본문 메타로 옮길 것 (CTR 손실)")

        # 1-c) 메인 키워드 앞쪽 배치
        kw_pos = -1
        for k in MAIN_KW_POOL:
            p = title.find(k)
            if p >= 0:
                kw_pos = p
                break
        if kw_pos < 0:
            score -= 10
            issues.append("제목에 메인 키워드 없음 (코스피/삼성전자/SK하이닉스 등)")
        elif kw_pos > TITLE_KW_HEAD_LIMIT:
            score -= 8
            issues.append(f"메인 키워드가 제목 {kw_pos}자 뒤 — 앞 {TITLE_KW_HEAD_LIMIT}자 이내로")

        # 2) 핵심 키워드 제목 포함
        if focus_kw and focus_kw not in title:
            score -= 10
            issues.append(f"핵심 키워드 '{focus_kw}'가 제목에 없습니다")
        elif focus_kw:
            suggestions.append(f"✓ 핵심 키워드 제목 포함")

        # 3) 메타 설명 길이 (70~160자)
        desc_len = len(meta_desc)
        if desc_len < 50:
            score -= 10
            issues.append(f"메타 설명이 너무 짧습니다 ({desc_len}자). 70자 이상 권장")
        elif desc_len > 200:
            score -= 5
            issues.append(f"메타 설명이 너무 깁니다 ({desc_len}자). 160자 이내 권장")
        else:
            suggestions.append(f"✓ 메타 설명 길이 적절 ({desc_len}자)")

        # 4) 태그 수 (톤북 v1: 30개 풀 활용)
        tag_count = len(tags)
        if tag_count < TAG_MIN_COUNT:
            penalty = min(20, (TAG_MIN_COUNT - tag_count))
            score -= penalty
            issues.append(f"태그 {tag_count}개 — 톤북 권장 {TAG_MIN_COUNT}개 (롱테일 포함 풀 활용)")
        else:
            suggestions.append(f"✓ 태그 수 OK ({tag_count}개)")
            # 롱테일 비중 (7자 이상 한글)
            longtail = sum(1 for t in tags if len(re.findall(r"[가-힣]", t)) >= 7)
            ratio = longtail / max(1, tag_count)
            if ratio < 0.4:
                score -= 5
                issues.append(f"롱테일 비중 {ratio:.0%} — 40% 이상 권장 ({longtail}/{tag_count})")

        # 5) 핵심 키워드 본문 밀도 (1#3t)
        if focus_kw:
            plain = re.sub(r'<[^>]+>', '', content)
            word_count = len(plain)
            kw_count = plain.count(focus_kw)
            density = (kw_count / word_count * 100) if word_count > 0 else 0
            if kw_count == 0:
                score -= 15
                issues.append(f"핵심 키워드 '{focus_kw}'가 본문에 없습니다")
            elif density < 0.5:
                score -= 5
                issues.append(f"키워드 밀도가 낮습니다 ({density:.1f}%). 1% 이상 권장")
            elif density > 5:
                score -= 10
                issues.append(f"키워드 과다 사용 ({density:.1f}%). 3% 이하 권장 (키워드 스터핑 위험)")
            else:
                suggestions.append(f"✓ 키워드 밀도 적절 ({density:.1f}%)")

        # 6) 소제목 존재 여부
        has_headings = bool(re.search(r'<h[2-4]|^#{2,4}\s', content, re.MULTILINE))
        if not has_headings:
            score -= 10
            issues.append("소제목(H2/H3)이 없습니다. 구조화를 위해 추가 권장")
        else:
            suggestions.append("✓ 소제목 구조화 확인")

        # 7) 투자 주의 문구
        disclaimer_keywords = ["투자의 책임", "참고용", "투자 손실", "본인에게 있"]
        has_disclaimer = any(kw in content for kw in disclaimer_keywords)
        if not has_disclaimer:
            score -= 10
            issues.append("⚠️ 투자 주의 문구가 없습니다. 필수 추가 필요")
        else:
            suggestions.append("✓ 투자 주의 문구 포함")

        # 8) 첫 100자 후킹 + 영상 메타 누수 (톤북 v1)
        plain_full = re.sub(r'<[^>]+>', '', content)
        body_after_title = re.split(r"^#\s+.+$", plain_full, maxsplit=1, flags=re.MULTILINE)
        if len(body_after_title) > 1:
            hook_zone = body_after_title[1].lstrip()[:400]
            hook_chars = len(re.sub(r"\s", "", hook_zone[:300]))
            if hook_chars < HOOK_MIN_CHARS:
                score -= 8
                issues.append(f"첫 후킹 영역 {hook_chars}자 — {HOOK_MIN_CHARS}자 이상 권장")
            else:
                suggestions.append(f"✓ 후킹 영역 OK ({hook_chars}자)")

            leaked = [p for p in VIDEO_META_PHRASES if p in hook_zone]
            if leaked:
                score -= 12
                issues.append(f"영상 메타가 첫 영역에 노출: {leaked} — 부록으로 이동 (검색 미리보기 손실)")
            else:
                suggestions.append("✓ 영상 메타 누수 없음")

        # 9) v2 — 브랜드 키워드 제목 노출 금지
        brand_leaked = [b for b in BRAND_KEYWORDS_FORBIDDEN_IN_TITLE if b in title]
        if brand_leaked:
            score -= 15
            issues.append(f"[v2] 제목에 브랜드 키워드 {brand_leaked} 노출 — 검색 트래픽 0, 종목/지수 키워드로 교체")
        else:
            suggestions.append("✓ [v2] 제목 브랜드 키워드 없음")

        # 10) v2 — 본문에 📍 목차 섹션
        if not any(p in content for p in TOC_SECTION_PATTERNS):
            score -= 10
            issues.append("[v2] '📍 이 글에서 다루는 것' 목차 섹션 없음 — 톤북 v2 §3 신설 필수")
        else:
            suggestions.append("✓ [v2] 목차 섹션 존재")

        # 11) v2 — 🔗 관련 종목 한눈에 + 표 행 3개 이상
        if not any(p in content for p in RELATED_SECTION_PATTERNS):
            score -= 12
            issues.append("[v2] '🔗 관련 종목 한눈에' 섹션 없음 — 톤북 v2 §3 신설 필수 (체류시간 핵심)")
        else:
            m = re.search(r"🔗\s*관련 종목 한눈에.*?\n([\s\S]+?)(?=\n##\s|\n---|$)", content)
            if m:
                table_rows = [ln for ln in m.group(1).splitlines() if ln.strip().startswith("|") and "---" not in ln]
                data_rows = max(0, len(table_rows) - 1)
                if data_rows < RELATED_TABLE_MIN_ROWS:
                    score -= 6
                    issues.append(f"[v2] 관련 종목 표 데이터 행 {data_rows}개 — 최소 {RELATED_TABLE_MIN_ROWS}개")
                else:
                    suggestions.append(f"✓ [v2] 관련 종목 표 행 OK ({data_rows}개)")

        # 12) v2 — 태그 앞 5개에 종목/지수 키워드 3개 이상
        if tags:
            head_tags = list(tags)[:TAG_HEAD_WINDOW]
            head_kw_count = sum(1 for t in head_tags if any(kw in t for kw in MAIN_KW_POOL))
            if head_kw_count < TAG_HEAD_KW_MIN:
                score -= 8
                issues.append(f"[v2] 태그 앞 {TAG_HEAD_WINDOW}개 중 종목/지수 키워드 {head_kw_count}개 — 최소 {TAG_HEAD_KW_MIN}개")
            else:
                suggestions.append(f"✓ [v2] 태그 앞 종목 키워드 OK ({head_kw_count}개)")

        return {
            "seo_score": max(0, score),
            "issues": issues,
            "suggestions": suggestions,
        }

    # ── 인포그래픽 사양 점검 ───────────────────────────
    def check_infographics(self, date: str, blog_dir: str = ".") -> dict:
        """date(YYYY-MM-DD) 기준 images/{date}/ 폴더의 PNG 존재/사양 점검."""
        from pathlib import Path as _P
        img_dir = _P(blog_dir) / "images" / date
        issues, suggestions = [], []
        score = 100
        required = ["market", "psychology", "summary"]
        for kind in required:
            png = img_dir / f"{date}-{kind}.png"
            if not png.exists():
                score -= 25
                issues.append(f"인포그래픽 누락: {png.name}")
            else:
                suggestions.append(f"✓ {png.name}")
        # insight PNG는 톤북상 금지
        forbidden = img_dir / f"{date}-insight.png"
        if forbidden.exists():
            score -= 10
            issues.append(f"insight PNG는 톤북 위반(텍스트로만 표시): {forbidden.name}")
        return {
            "infographic_score": max(0, score),
            "issues": issues,
            "suggestions": suggestions,
        }

    # ── 2. 가독성 점수 계산 ────────────────────────────
    def calc_readability(self, content: str, platform: str) -> dict:
        plain = re.sub(r'<[^>]+>', '', content)
        plain = re.sub(r'#+\s', '', plain)  # 마크다운 헤딩 제거

        char_count = len(plain.replace(" ", ""))
        sentences = re.split(r'[.!?c��]\s*', plain)
        sentences = [s for s in sentences if len(s.strip()) > 5]
        sentence_count = len(sentences)
        avg_sentence_len = char_count / sentence_count if sentence_count > 0 else 0

        paragraphs = [p.strip() for p in plain.split("\n\n") if len(p.strip()) > 20]
        paragraph_count = len(paragraphs)

        score = 100
        issues = []
        suggestions = []

        # 글자 수 검사
        min_len = PLATFORM_MIN_LENGTH.get(platform, 1000)
        if char_count < min_len:
            score -= 20
            issues.append(f"글자 수 부족 ({char_count}자). {platform}은 {min_len}자 이상 권장")
        else:
            suggestions.append(f"✓ 글자 수 충분 ({char_count}자)")

        # 평균 문장 길이 (한국어: 30~60자 이상 권장)
        if avg_sentence_len > 100:
            score -= 15
            issues.append(f"문장이 너무 깁니다 (평균 {avg_sentence_len:.0f}자). 80자 이내 권장")
        elif avg_sentence_len < 15 and sentence_count > 5:
            score -= 5
            issues.append(f"문장이 너무 짧습니다 (평균 {avg_sentence_len:.0f}자). 정보 밀도 부족 가능")
        else:
            suggestions.append(f"✓ 문장 길이 적절 (평균 {avg_sentence_len:.0f}자)")

        # 문단 수
        if paragraph_count < 3:
            score -= 10
            issues.append(f"문단이 너무 적습니다 ({paragraph_count}개). 구조화 필요")
        else:
            suggestions.append(f"✓ 문단 구조 적절 ({paragraph_count}개)")

        return {
            "readability_score": max(0, score),
            "char_count": char_count,
            "sentence_count": sentence_count,
            "avg_sentence_len": round(avg_sentence_len, 1),
            "paragraph_count": paragraph_count,
            "issues": issues,
            "suggestions": suggestions,
        }

    # ── 3. 문체 일관성 (Gemini 분석) ──────────────────
    def check_style_consistency(self, content: str, platform: str) -> dict:
        style_path = STYLE_DIR / f"style_guide_{platform}.json"
        style_guide = {}
        if style_path.exists():
            with open(style_path, encoding="utf-8") as f:
                style_guide = json.load(f)

        writing_style = style_guide.get("writing_style", {})
        do_list = style_guide.get("do_list", [])
        dont_list = style_guide.get("dont_list", [])

        plain = re.sub(r'<[^>]+>', '', content)[:3000]

        prompt = f"""
+��음 블로그 글이 {platform} 플랫폼 스타일 가이드를 잘 따르고 있는지 평가해줘.

[스타일 가이드]
- 문체 톤: {writing_style.get('tone', '미지정')}
- 격식: {writing_style.get('formality', '미지정')}
- 감성 수준: {writing_style.get('emotion_level', '미지정')}
- 해야 할 것: {', '.join(do_list)}
- 하지 말아야 할 것: {', '.join(dont_list)}

[실제 글 (앞 3000자)]
{plain}

다음 JSON 형식으로만 응답해:
{{
  "style_score": 0~100,
  "tone_match": "높음|중간|낮음",
  "style_issues": ["문체 문제점 리스트"],
  "style_suggestions": ["개선 제안 리스트"],
  "overall_verdict": "통과|수정필요|재작성필요"
}}
"""
        response = self.model.generate_content(prompt)
        raw = response.text.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"style_score": 50, "raw": raw, "overall_verdict": "수정필요"}

    # ── 4. 전체 검증 실행 ─────────────────────────────
    def check(self, meta: dict, content: str, platform: str) -> dict:
        video_id = meta.get("video_id", "unknown")
        logger.info(f"[{platform}] 품질 검증 시작: {meta.get('title', '')}")

        seo = self.calc_seo_score(content, meta)
        readability = self.calc_readability(content, platform)
        style = self.check_style_consistency(content, platform)

        # 종합 점수 (가중 평균)
        overall = int(
            seo["seo_score"] * 0.4 +
            readability["readability_score"] * 0.3 +
            style.get("style_score", 70) * 0.3
        )

        passed = overall >= PASS_THRESHOLD

        report = {
            "video_id": video_id,
            "platform": platform,
            "checked_at": datetime.now().isoformat(),
            "title": meta.get("title", ""),
            "overall_score": overall,
            "passed": passed,
            "threshold": PASS_THRESHOLD,
            "seo": seo,
            "readability": readability,
            "style": style,
            "action": "post" if passed else style.get("overall_verdict", "수정필요"),
        }

        out_path = OUTPUT_DIR / f"{platform}_{video_id}_report.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        status_icon = "✅" if passed else "❌"
        logger.info(f"[{platform}] {status_icon} 품질 점수: {overall}/100 ({'통과' if passed else '미달'})")
        return report


# ── CLI 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python 08_quality_checker.py <meta_json_path> <platform>")
        sys.exit(1)

    meta_path = Path(sys.argv[1])
    platform = sys.argv[2]

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    with open(meta["content_path"], encoding="utf-8") as f:
        content = f.read()

    checker = QualityChecker()
    report = checker.check(meta, content, platform)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n결과: {'✅ 통과' if report['passed'] else '❌ 수정 필요'} ({report['overall_score']}/100)")
