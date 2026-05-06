"""
SEO 분석 에이전트 (Agent 01)
================================
역할: YouTube 영상 정보를 받아 SEO 최적화 데이터를 생성
- 핵심 키워드 추출 (Gemini API)
- 플랫폼별 SEO 제목 / 메타 디스크립션 생성
- 태그 / 카테고리 추천
- Google Trends 기반 키워드 트렌드 점수
출력: output/seo/seo_data_{video_id}.json
"""

import os
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
import requests
from pytrends.request import TrendReq

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SEO Agent] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/01_seo_analyzer.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
OUTPUT_DIR = Path("output/seo")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PLATFORMS = ["naver", "tistory", "wordpress", "brunch", "medium"]

# 플랫폼별 SEO 특성
PLATFORM_SEO_RULES = {
    "naver": {
        "title_max": 60,
        "desc_max": 160,
        "tag_count": 10,
        "note": "검색 유입 중심, 정보성 키워드 강조, '~하는 법', '~이란' 패턴 선호",
    },
    "tistory": {
        "title_max": 70,
        "desc_max": 200,
        "tag_count": 15,
        "note": "구글 SEO 중심, Long-tail 키워드, 영어+한국어 혼용 태그",
    },
    "wordpress": {
        "title_max": 65,
        "desc_max": 160,
        "tag_count": 10,
        "note": "글로벌 SEO, Focus keyword 1개, Yoast SEO 기준 준수",
    },
    "brunch": {
        "title_max": 50,
        "desc_max": 120,
        "tag_count": 5,
        "note": "감성적 제목, 독자 흥미 유발, 해시태그 최소화",
    },
    "medium": {
        "title_max": 65,
        "desc_max": 150,
        "tag_count": 5,
        "note": "영문 병기 권장, Subtitle 활용, 명료한 가치 제안",
    },
}


class SEOAnalyzer:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.pytrends = TrendReq(hl="ko", tz=540)  # KST

    # ── 1. 키워드 추출 ─────────────────────────────────
    def extract_keywords(self, video_title: str, video_description: str, transcript: str = "") -> dict:
        """Gemini로 핵심 키워드 추출"""
        prompt = f"""
다음 주식/투자 YouTube 영상 정보에서 SEO용 키워드를 추출해줘.

[영상 제목]
{video_title}

[영상 설명]
{video_description}

[자막/내용 요약]
{transcript[:3000] if transcript else "없음"}

다음 JSON 형식으로만 응답해:
{{
  "primary_keywords": ["메인 키워드 3개"],
  "secondary_keywords": ["보조 키워드 5~7개"],
  "lsi_keywords": ["LSI(잠재의미) 키워드 5개"],
  "stock_names": ["언급된 종목명 리스트"],
  "themes": ["투자테마/섹터 리스트"],
  "search_intent": "정보성|상업적|탐색적|거래적 중 하나",
  "difficulty": "상|중|하"
}}
"""
        response = self.model.generate_content(prompt)
        raw = response.text.strip()
        # JSON 블록 추출
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        logger.warning("키워드 추출 JSON 파싱 실패, raw 반환")
        return {"raw": raw}

    # ── 2. 트렌드 점수 ────────────────────────────────
    def get_trend_scores(self, keywords: list) -> dict:
        """Google Trends로 키워드 관심도 점수 조회"""
        scores = {}
        # Trends API는 한 번에 최대 5개
        chunks = [keywords[i:i+5] for i in range(0, len(keywords), 5)]
        for chunk in chunks:
            try:
                self.pytrends.build_payload(chunk, timeframe="now 7-d", geo="KR")
                data = self.pytrends.interest_over_time()
                if not data.empty:
                    for kw in chunk:
                        if kw in data.columns:
                            scores[kw] = int(data[kw].mean())
                time.sleep(1)  # rate limit
            except Exception as e:
                logger.warning(f"Trends API 오류 ({chunk}): {e}")
                for kw in chunk:
                    scores[kw] = -1
        return scores

    # ── 3. 플랫폼별 SEO 메타데이터 생성 ──────────────
    def generate_platform_seo(self, video_title: str, keywords: dict, platform: str) -> dict:
        """플랫폼별 최적화된 제목, 메타 설명, 태그 생성"""
        rules = PLATFORM_SEO_RULES[platform]
        primary = keywords.get("primary_keywords", [])
        secondary = keywords.get("secondary_keywords", [])
        stock_names = keywords.get("stock_names", [])
        themes = keywords.get("themes", [])

        prompt = f"""
한국 주식/투자 블로그 포스트의 SEO 메타데이터를 {platform} 플랫폼에 맞게 생성해줘.

[원본 영상 제목]
{video_title}

[핵심 키워드]
- 주요: {', '.join(primary)}
- 보조: {', '.join(secondary)}
- 종목명: {', '.join(stock_names)}
- 테마: {', '.join(themes)}

[{platform} SEO 규칙]
- 제목 최대 {rules['title_max']}자
- 메타 설명 최대 {rules['desc_max']}자
- 태그 {rules['tag_count']}개
- 특징: {rules['note']}

다음 JSON 형식으로만 응답해:
{{
  "seo_title": "SEO 최적화 제목",
  "seo_title_alt": "대안 제목 (A/B 테스트용)",
  "meta_description": "메타 설명 (검색 결과 스니펫)",
  "slug": "url-friendly-slug",
  "focus_keyword": "대표 키워드 1개",
  "tags": ["태그1", "태그2", ...],
  "category": "카테고리명",
  "internal_links_suggestion": ["연관 포스트 주제 2~3개"],
  "schema_type": "Article|BlogPosting|NewsArticle"
}}
"""
        response = self.model.generate_content(prompt)
        raw = response.text.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"raw": raw}

    # ── 4. 전체 SEO 분석 실행 ────────────────────────
    def analyze(self, video_info: dict) -> dict:
        """
        video_info = {
            "video_id": str,
            "title": str,
            "description": str,
            "transcript": str,  # optional
            "published_at": str,
        }
        """
        video_id = video_info.get("video_id", "unknown")
        logger.info(f"SEO 분석 시작: {video_info['title']}")

        # 1) 키워드 추출
        logger.info("키워드 추출 중...")
        keywords = self.extract_keywords(
            video_info["title"],
            video_info.get("description", ""),
            video_info.get("transcript", ""),
        )

        # 2) 트렌드 점수
        logger.info("Google Trends 점수 조회 중...")
        all_kw = (
            keywords.get("primary_keywords", []) +
            keywords.get("secondary_keywords", [])
        )
        trend_scores = self.get_trend_scores(all_kw[:10])

        # 3) 플랫폼별 SEO 메타데이터
        platform_seo = {}
        for platform in PLATFORMS:
            logger.info(f"[{platform}] SEO 메타데이터 생성 중...")
            platform_seo[platform] = self.generate_platform_seo(
                video_info["title"], keywords, platform
            )
            time.sleep(0.5)

        # 4) 결과 조합
        result = {
            "video_id": video_id,
            "analyzed_at": datetime.now().isoformat(),
            "source_title": video_info["title"],
            "keywords": keywords,
            "trend_scores": trend_scores,
            "platform_seo": platform_seo,
            "top_keyword_by_trend": max(trend_scores, key=trend_scores.get) if trend_scores else None,
        }

        # 5) 저장
        out_path = OUTPUT_DIR / f"seo_data_{video_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"SEO 분석 완료: {out_path}")

        return result


# ── CLI 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # 테스트 또는 파이프라인에서 video_info JSON 경로를 인수로 받음
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            video_info = json.load(f)
    else:
        # 테스트용 샘플
        video_info = {
            "video_id": "test_001",
            "title": "[12시에 만나요] 오늘 주목해야 할 반도체 종목 3선",
            "description": "삼성전자, SK하이닉스, 한미반도체를 중심으로 오늘의 시황을 분석합니다.",
            "transcript": "",
            "published_at": datetime.now().isoformat(),
        }

    analyzer = SEOAnalyzer()
    result = analyzer.analyze(video_info)
    print(json.dumps(result, ensure_ascii=False, indent=2))
