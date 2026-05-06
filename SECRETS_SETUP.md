# GitHub Secrets 설정 가이드

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

## 필수 (이미 설정됨)
| Secret 이름 | 설명 |
|---|---|
| `GEMINI_API_KEY` | ✅ 기설정 완료 |

## 네이버 블로그 (Chrome 자동화)
| Secret 이름 | 설명 |
|---|---|
| `NAVER_ID` | 네이버 아이디 |
| `NAVER_PW` | 네이버 비밀번호 |
| `NAVER_BLOG_ID` | 블로그 ID (URL의 myblog 부분) |

## 티스토리 (공식 API)
1. https://www.tistory.com/guide/api/manage/register 에서 앱 등록
2. 아래 Secret 설정:

| Secret 이름 | 설명 |
|---|---|
| `TISTORY_APP_ID` | 앱 ID |
| `TISTORY_SECRET_KEY` | Secret Key |
| `TISTORY_ACCESS_TOKEN` | OAuth 액세스 토큰 |
| `TISTORY_BLOG_NAME` | 블로그명 (URL의 myblog 부분) |

**토큰 발급:**
```
python scripts/agents/05_tistory_poster.py
# 출력되는 인증 URL 접속 → code 받기 → 토큰 교환
```

## 워드프레스 (REST API)
| Secret 이름 | 설명 |
|---|---|
| `WP_URL` | WordPress 사이트 URL (예: https://myblog.com) |
| `WP_USERNAME` | 관리자 계정명 |
| `WP_APP_PASS` | 앱 비밀번호 (관리자→사용자→프로필→애플리케이션 비밀번호) |

## 브런치 (Chrome 자동화 — 카카오 계정)
| Secret 이름 | 설명 |
|---|---|
| `BRUNCH_EMAIL` | 카카오 이메일 |
| `BRUNCH_PW` | 카카오 비밀번호 |

## 미디엄 (API 우선, 없으면 Chrome)
| Secret 이름 | 설명 |
|---|---|
| `MEDIUM_EMAIL` | 미디엄 이메일 (Chrome 자동화용) |
| `MEDIUM_PW` | 미디엄 비밀번호 (Chrome 자동화용) |
| `MEDIUM_TOKEN` | Integration Token (API 방식, 선택) |

**미디엄 토큰 발급:**
Profile → Settings → Security and apps → Integration tokens
