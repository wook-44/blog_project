"""
블로그 작성 에이전트 (Agent 03)
=================================
역할: SEO 데이터 + 스타일 가이드를 참조하여 플랫폼별 최적화 블로그 포스트 생성
- 플랫폼별 서로 다른 문체/구조/길이 적용
- SEO 키워드 자연스럽게 녹여서 작성
- HTML(네이버/티스토리/워드프레스) 또는 마크다운(브런치/미디엄) 형식 출력
출력: output/posts/{platform}/{video_id}.{html|md}
      output/posts/{platform}/{video_id}_meta.json
"""

import os
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

# ── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Writer Agent] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/03_blog_writer.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 설정 ───────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
OUTPUT_BASE = Path("output/posts")
SEO_DIR = Path("output/seo")
STYLE_DIR = Path("output/style_guides")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")  # Pro: 더 긴 컨텍스트, 고품질 글쓰기

# 플랫폼별 출력 형식
PLATFORM_FORMAT = {
    "naver": "html",
    "tistory": "html",
    "wordpress": "html",
    "brunch": "markdown",
    "medium": "markdown",
}

# 플랫폼별 길이 목표
PLATFORM_LENGTH = {
    "naver": (1200, 1800),
    "tistory": (2000, 3000),
    "wordpress": (1500, 2500),
    "brunch": (1000, 1500),
    "medium": (1200, 2000),
}


class BlogWriter:
    def __init__(self):
        self.model = model

    # ── 데이터 로드 ────────────────────────────────────
    def load_seo_data(self, video_id: str) -> dict:
        path = SEO_DIR / f"seo_data_{video_id}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        logger.warning(f"SEO 데이터 없음: {path}")
        return {}

    def load_style_guide(self, platform: str) -> dict:
        path = STYLE_DIR / f"style_guide_{platform}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        logger.warning(f"스타일 가이드 없음: {path}")
        return {}

    # ── 프롬프트 구성 ──────────────────────────────────
    def _build_prompt(
        self,
        video_info: dict,
        seo_data: dict,
        style_guide: dict,
        platform: str,
        output_format: str,
    ) -> str:
        platform_seo = seo_data.get("platform_seo", {}).get(platform, {})
        keywords = seo_data.get("keywords", {})
        structure = style_guide.get("structure", {})
        content_pattern = style_guide.get("content_pattern", {})
        writing_style = style_guide.get("writing_style", {})

        min_len, max_len = PLATFORM_LENGTH[platform]
        today = datetime.now().strftime("%Y년 %m월 %d일")

        format_instruction = (
            "HTML 형식으로 작성 (<h2>, <h3>, <p>, <ul>, <li>, <strong>, <table> 태그 사용)"
            if output_format == "html"
            else "마크다운 형식으로 작성 (##, ###, **, - 사용)"
        )

        return f"""
당신은 한국 최고의 주식/투자 블로그 작가입니다.
아래 정보를 바탕으로 {platform} 플랫폼에 최적화된 블로그 포스트를 작성하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[기본 정보]
날짜: {today}
원본 영상 제목: {video_info.get('title', '')}
원본 영상 내용: {video_info.get('transcript', video_info.get('description', ''))[:3000]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SEO 요구사항]
- 포스트 제목: {platform_seo.get('seo_title', video_info.get('title', ''))}
- 핵심 키워드: {platform_seo.get('focus_keyword', '')}
- 주요 키워드: {', '.join(keywords.get('primary_keywords', []))}
- 보조 키워드: {', '.join(keywords.get('secondary_keywords', []))}
- 언급할 종목: {', '.join(keywords.get('stock_names', []))}
- 키워드는 자연스럽게 본문에 2~3회 반복

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[{platform} 스타일 가이드]
- 문체 톤: {writing_style.get('tone', '친근하고 분석적')}
- 격식: {writing_style.get('formality', '존댓말')}
- 감성 수준: {writing_style.get('emotion_level', '중간')}
- 소제목 스타일: {structure.get('heading_style', '소제목 3~4개')}
- 문단 길이: {structure.get('paragraph_length', '3~5문장')}
- 이모지 사용: {structure.get('uses_emoji', False)}
- 불릿 포인트: {structure.get('uses_bullet_points', True)}
- 표 사용: {structure.get('uses_tables', False)}
- 인트로 패턴: {structure.get('intro_pattern', '시장 상황으로 시작')}
- 아웃트로 패턴: {structure.get('outro_pattern', '핵심 요약 + 구독 유도')}

반드시 포함할 항목: {', '.join(content_pattern.get('must_include', []))}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

[출력 조건]
- 형식: {format_instruction}
- 글자 수: {min_len}}{max_len}자 (공백 포함)
- 제목 태그(h1) 없이 본문만 작성 (제목은 별도 메타로 관리)
- 투자 주의 문구를 맨 마지막에 반드시 추가: "※ 이 글은 투자 참고용이며, 투자의 책임은 본인에게 있습니다."
- 지금 바로 포스팅 가능한 완성형 글 작성

지금 바로 작성 시작:
"""

    # ── 단일 플랫폼 포스트 생성 ───────────────────────
    def write_for_platform(self, video_info: dict, platform: str, seo_data: dict = None, style_guide: dict = None) -> dict:
        output_format = PLATFORM_FORMAT[platform]
        out_dir = OUTPUT_BASE / platform
        out_dir.mkdir(parents=True, exist_ok=True)

        video_id = video_info.get("video_id", "unknown")

        # 데이터 로드
        if seo_data is None:
            seo_data = self.load_seo_data(video_id)
        if style_guide is None:
            style_guide = self.load_style_guide(platform)

        # 글 생성
        logger.info(f"[{platform}] 포스트 작성 중...")
        prompt = self._build_prompt(video_info, seo_data, style_guide, platform, output_format)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.75,
                    max_output_tokens=4096,
                ),
            )
            content = response.text.strip()
        except Exception as e:
            logger.error(f"[{platform}] Gemini 생성 실패: {e}")
            raise

        # 파일 저장
        ext = "html" if output_format == "html" else "md"
        content_path = out_dir / f"{video_id}.{ext}"
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 메타데이터 저장
        platform_seo = seo_data.get("platform_seo", {}).get(platform, {})
        meta = {
            "video_id": video_id,
            "platform": platform,
            "created_at": datetime.now().isoformat(),
            "title": platform_seo.get("seo_title", video_info.get("title", "")),
            "slug": platform_seo.get("slug", video_id),
            "focus_keyword": platform_seo.get("focus_keyword", ""),
            "tags": platform_seo.get("tags", []),
            "category": platform_seo.get("category", "주식"),
            "meta_description": platform_seo.get("meta_description", ""),
            "content_path": str(content_path),
            "char_count": len(content),
            "format": output_format,
            "status": "draft",  # 포스팅 전 draft
        }
        meta_path = out_dir / f"{video_id}_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"[{platform}] 완료 ({len(content)}자): {content_path}")
        return {"meta": meta, "content": content}

    # ── 전체 플랫폼 포스트 생성 ───────────────────────
    def write_all(self, video_info: dict, platforms: list = None) -> dict:
        if platforms is None:
            platforms = list(PLATFORM_FORMAT.keys())

        # SEO/스타일 데이터 미리 로드 (공유)
        video_id = video_info.get("video_id", "unknown")
        seo_data = self.load_seo_data(video_id)

        results = {}
        for platform in platforms:
            style_guide = self.load_style_guide(platform)
            try:
                results[platform] = self.write_for_platform(
                    video_info, platform, seo_data=seo_data, style_guide=style_guide
                )
            except Exception as e:
                logger.error(f"[{platform}] 작성 실패: {e}")
                results[platform] = {"error": str(e)}
            time.sleep(2)  # rate limit

        return results


# ── CLI 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            video_info = json.load(f)
    else:
        video_info = {
            "video_id": "test_001",
            "title": "[12시에 만나요] 오늘 주목해야 할 반도체 종목 3선",
            "description": "삼성전자, SK하이닉스, 한미반도체 시황 분석",
            "transcript": "오늘 시장은 반도체 섹터 중심으로 움직였습니다...",
            "published_at": datetime.now().isoformat(),
        }

    writer = BlogWriter()
    results = writer.write_all(video_info)
    for platform, result in results.items():
        if "error" in result:
            print(f"[{platform}] 실패: {result['error']}")
        else:
            print(f"[{platform}] 성공: {result['meta']['content_path']} ({result['meta']['char_count']}자)")
