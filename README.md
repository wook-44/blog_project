# blog_project

게임 및 앱 제품 기획·상품화 작업을 정리하는 작업 공간입니다.

## YouTube 플레이리스트 자동 체크

대상 플레이리스트: https://www.youtube.com/playlist?list=PLpDZdhM6kelSHHNdphTwAWuxxwbI4kGyX

GitHub Actions가 매일 **오전 8시 KST**에 위 플레이리스트를 확인하고,
새로 올라온 영상이 있으면 Gemini API로 분석한 결과를 `data/new_videos.csv`에 기록합니다.

### 구조

```
blog_project/
├── .github/workflows/youtube-check.yml   # 매일 자동 실행 워크플로우
├── scripts/check_playlist.py             # RSS 체크 + Gemini 분석 스크립트
├── data/
│   ├── seen_videos.txt                   # (자동 생성) 이미 확인한 영상 ID 목록
│   └── new_videos.csv                    # (자동 생성) 신규 영상 + Gemini 분석 결과
├── README.md
└── .gitignore
```

### 필요한 설정 (1회)

GitHub 저장소 Settings → Secrets and variables → Actions 에서
`GEMINI_API_KEY` 이름으로 Google AI Studio API 키를 등록합니다.

### 수동 실행

GitHub 저장소의 Actions 탭 → "YouTube Playlist Check" → **Run workflow** 클릭.

### 로컬에서 테스트

```bash
export GEMINI_API_KEY="your-key"
python scripts/check_playlist.py
```
