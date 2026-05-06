"""
전체 블로그 파이프라인 오케스트레이터
=======================================
실행 순서:
  1. check_playlist.py (기존) → 새 영상 감지
  2. Agent 01: SEO 분석
  3. Agent 02: 벤치마크/스타일 분석 (캐시 24h)
  4. Agent 03: 플랫폼별 블로그 작성
  5. Agent 08: 품질 검증 (미달 시 재작성 1회)
  6. Agent 04~07: 플랫폼별 포스팅
  7. 결과 리포트 생성 → GitHub Issues 또는 로그 저장

실행:
  python scripts/pipeline.py --video-info output/latest_video.json
  python scripts/pipeline.py --platforms naver tistory  # 특정 플랫폼만
"""

import os
import sys
import json
import logging
import time
import argparse
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from agents.agent_01_seo_analyzer import SEOAnalyzer
from agents.agent_02_benchmark_analyzer import BenchmarkAnalyzer
from agents.agent_03_blog_writer import BlogWriter
from agents.agent_08_quality_checker import QualityChecker

# ── 로깅 ───────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Pipeline] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 전체 플랫폼 ────────────────────────────────────────
ALL_PLATFORMS = ["naver", "tistory", "wordpress", "brunch", "medium"]

# 포스터 임포트 (실패해도 파이프라인 계속)
try:
    from agents.agent_04_naver_poster import NaverBlogPoster
    NAVER_AVAILABLE = True
except ImportError:
    NAVER_AVAILABLE = False
    logger.warning("네이버 포스터 로드 실패 (selenium 미설치?)")

try:
    from agents.agent_05_tistory_poster import TistoryPoster
    TISTORY_AVAILABLE = True
except ImportError:
    TISTORY_AVAILABLE = False
    logger.warning("티스토리 포스터 로드 실패")

try:
    from agents.agent_06_wordpress_poster import WordPressPoster
    WORDPRESS_AVAILABLE = True
except ImportError:
    WORDPRESS_AVAILABLE = False
    logger.warning("워드프레스 포스터 로드 실패")

try:
    from agents.agent_07_brunch_medium_poster import BrunchPoster, MediumPoster
    BRUNCH_AVAILABLE = True
    MEDIUM_AVAILABLE = True
except ImportError:
    BRUNCH_AVAILABLE = False
    MEDIUM_AVAILABLE = False
    logger.warning("브런치/미디엄 포스터 로드 실패")


class BlogPipeline:
    def __init__(self, platforms: list = None, headless: bool = True, max_retry: int = 1):
        self.platforms = platforms or ALL_PLATFORMS
        self.headless = headless
        self.max_retry = max_retry
        self.results = {}

    # ── Step 1: SEO 분석 ──────────────────────────────
    def step_seo(self, video_info: dict) -> dict:
        logger.info("=" * 50)
        logger.info("STEP 1: SEO 분석")
        analyzer = SEOAnalyzer()
        seo_data = analyzer.analyze(video_info)
        logger.info(f"SEO 분석 완료. 최고 트렌드 키워드: {seo_data.get('top_keyword_by_trend')}")
        return seo_data

    # ── Step 2: 벤치마크 분석 ────────────────────────
    def step_benchmark(self) -> dict:
        logger.info("=" * 50)
        logger.info("STEP 2: 벤치마크 & 스타일 분석")
        analyzer = BenchmarkAnalyzer()
        style_guides = analyzer.analyze_all(platforms=self.platforms)
        logger.info(f"스타일 가이드 생성 완료: {list(style_guides.keys())}")
        return style_guides

    # ── Step 3: 블로그 작성 ───────────────────────────
    def step_write(self, video_info: dict, seo_data: dict, style_guides: dict) -> dict:
        logger.info("=" * 50)
        logger.info("STEP 3: 블로그 포스트 작성")
        writer = BlogWriter()
        posts = writer.write_all(video_info, platforms=self.platforms)
        success = [p for p, r in posts.items() if "error" not in r]
        logger.info(f"작성 완료: {success}")
        return posts

    # ── Step 4: 품질 검증 & 재작성 ───────────────────
    def step_quality_check(self, video_info: dict, posts: dict) -> dict:
        logger.info("=" * 50)
        logger.info("STEP 4: 품질 검증")
        checker = QualityChecker()
        writer = BlogWriter()
        quality_reports = {}

        for platform, post_result in posts.items():
            if "error" in post_result:
                logger.warning(f"[{platform}] 작성 실패 스킵")
                continue

            meta = post_result["meta"]
            content = post_result["content"]

            for attempt in range(self.max_retry + 1):
                report = checker.check(meta, content, platform)
                quality_reports[platform] = report

                if report["passed"]:
                    logger.info(f"[{platform}] ✅ 품질 통과 ({report['overall_score']}/100)")
                    # meta 상태 업데이트
                    meta["status"] = "quality_passed"
                    meta_path = Path(meta["content_path"]).parent / f"{meta['video_id']}_meta.json"
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    break
                else:
                    if attempt < self.max_retry:
                        logger.warning(f"[{platform}] ❌ 품질 미달 ({report['overall_score']}/100), 재작성 시도 {attempt+1}/{self.max_retry}")
                        try:
                            rewrite_result = writer.write_for_platform(video_info, platform)
                            meta = rewrite_result["meta"]
                            content = rewrite_result["content"]
                            posts[platform] = rewrite_result
                        except Exception as e:
                            logger.error(f"[{platform}] 재작성 실패: {e}")
                            break
                    else:
                        logger.warning(f"[{platform}] ❌ 최대 재시도 후에도 미달. 수동 검토 필요")
                        meta["status"] = "quality_failed"

        return quality_reports

    # ── Step 5: 포스팅 ────────────────────────────────
    def step_post(self, posts: dict, quality_reports: dict) -> dict:
        logger.info("=" * 50)
        logger.info("STEP 5: 플랫폼별 포스팅")
        post_results = {}

        for platform in self.platforms:
            if platform not in posts or "error" in posts[platform]:
                logger.warning(f"[{platform}] 포스팅 스킵 (작성 실패)")
                continue

            report = quality_reports.get(platform, {})
            if not report.get("passed", False):
                logger.warning(f"[{platform}] 품질 미달 포스팅 스킵")
                post_results[platform] = {"status": "skipped", "reason": "quality_failed"}
                continue

            meta = posts[platform]["meta"]
            content = posts[platform]["content"]

            try:
                if platform == "naver" and NAVER_AVAILABLE:
                    poster = NaverBlogPoster(headless=self.headless)
                    post_results[platform] = poster.post(meta, content)

                elif platform == "tistory" and TISTORY_AVAILABLE:
                    poster = TistoryPoster()
                    post_results[platform] = poster.post(meta, content)

                elif platform == "wordpress" and WORDPRESS_AVAILABLE:
                    poster = WordPressPoster()
                    post_results[platform] = poster.post(meta, content)

                elif platform == "brunch" and BRUNCH_AVAILABLE:
                    poster = BrunchPoster(headless=self.headless)
                    post_results[platform] = poster.post(meta, content)

                elif platform == "medium" and MEDIUM_AVAILABLE:
                    poster = MediumPoster(headless=self.headless)
                    post_results[platform] = poster.post(meta, content)

                else:
                    post_results[platform] = {"status": "unavailable", "reason": f"{platform} poster not loaded"}

                time.sleep(3)  # 플랫폼 간 간격

            except Exception as e:
                logger.error(f"[{platform}] 포스팅 예외: {e}")
                post_results[platform] = {"status": "error", "error": str(e)}

        return post_results

    # ── 전체 파이프라인 실행 ──────────────────────────
    def run(self, video_info: dict) -> dict:
        start_time = datetime.now()
        video_id = video_info.get("video_id", "unknown")
        logger.info(f"🚀 파이프라인 시작: {video_info.get('title', '')}")
        logger.info(f"대상 플랫폼: {self.platforms}")

        try:
            seo_data = self.step_seo(video_info)
            style_guides = self.step_benchmark()
            posts = self.step_write(video_info, seo_data, style_guides)
            quality_reports = self.step_quality_check(video_info, posts)
            post_results = self.step_post(posts, quality_reports)
        except Exception as e:
            logger.error(f"파이프라인 오류: {e}", exc_info=True)
            post_results = {"error": str(e)}

        # 최종 리포트
        elapsed = (datetime.now() - start_time).total_seconds()
        summary = {
            "video_id": video_id,
            "title": video_info.get("title", ""),
            "platforms": self.platforms,
            "started_at": start_time.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "post_results": post_results,
            "quality_summary": {
                p: {
                    "score": quality_reports.get(p, {}).get("overall_score", 0),
                    "passed": quality_reports.get(p, {}).get("passed", False),
                }
                for p in self.platforms
            },
        }

        # 리포트 저장
        report_path = Path("output") / f"pipeline_report_{video_id}_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*50}")
        logger.info(f"🏁 파이프라인 완료 ({elapsed:.1f}초)")
        for platform, res in post_results.items():
            status = res.get("status", "unknown")
            url = res.get("post_url", "")
            icon = "✅" if status == "success" else "❌"
            logger.info(f"  {icon} {platform}: {status} {url}")
        logger.info(f"리포트: {report_path}")

        return summary


# ── CLI 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="주식 블로그 자동화 파이프라인")
    parser.add_argument("--video-info", required=True, help="영상 정보 JSON 파일 경로")
    parser.add_argument("--platforms", nargs="+", default=None,
                        choices=ALL_PLATFORMS, help="포스팅할 플랫폼 (기본: 전체)")
    parser.add_argument("--headless", action="store_true", help="Chrome 헤드리스 모드")
    parser.add_argument("--no-retry", action="store_true", help="품질 미달 시 재작성 안 함")
    args = parser.parse_args()

    with open(args.video_info, encoding="utf-8") as f:
        video_info = json.load(f)

    pipeline = BlogPipeline(
        platforms=args.platforms,
        headless=args.headless,
        max_retry=0 if args.no_retry else 1,
    )
    result = pipeline.run(video_info)
    print(json.dumps(result, ensure_ascii=False, indent=2))
