# NLLB 다국어 번역 서비스

FastAPI와 Streamlit으로 만든 Day 8 자유주제 프로젝트입니다. NLLB-200 모델로 한국어, 영어, 중국어(간체), 일본어를 번역하며, Google OAuth/OIDC 로그인으로 번역 API를 보호합니다.

## 구현 결과

**worked** — NLLB 번역, Google 로그인, 보호된 FastAPI 요청, 번역 기록·복사, TXT/CSV 파일 번역을 로컬에서 확인했습니다. 단위 테스트는 `9 passed`입니다.

## 주요 기능

- 한국어·영어·중국어(간체)·일본어 간 번역
- Google 계정 로그인 및 로그아웃
- Google ID 토큰 기반 FastAPI Bearer 인증
- 최근 20개 번역 기록과 결과 복사
- TXT 파일 번역 및 다운로드
- CSV의 선택 열 번역, `translated_text` 열 추가 및 다운로드

## 동작 흐름

```text
Streamlit 화면
  → Google OIDC 로그인
  → Google ID 토큰을 Bearer 헤더로 전달
  → FastAPI POST /predict
  → 토큰·입력 검증
  → NLLB 모델 추론
  → 번역 결과·기록 표시
```

## 프로젝트 구조

```text
app/
  auth.py               Google ID 토큰 검증
  config.py             환경 변수 설정
  schemas.py            요청·응답 Pydantic 모델
  model_service.py      NLLB 모델 로드와 번역 어댑터
  main.py               FastAPI 엔드포인트
frontend/
  app.py                Streamlit 로그인·번역·파일 UI
.streamlit/
  secrets.toml.example  Google OAuth 설정 예시
tests/
  test_auth.py          Google 토큰 인증 테스트
  test_schemas.py       요청 검증 테스트
  test_model_service.py NLLB 언어 토큰 매핑 테스트
project.ipynb           단계별 실행·검증 노트북
```

## 실행 환경 준비

Python 3.12와 NVIDIA GPU 환경을 기준으로 작성했습니다.

```powershell
cd D:\Codes\sandbox\translate-project
uv sync --python 3.12 --group dev
Copy-Item .env.example .env
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`torch==2.6.0+cu126`을 사용하며, NLLB 모델은 첫 FastAPI 실행 때 다운로드되어 메모리에 한 번만 로드됩니다. `hf-xet`은 Hugging Face Xet 저장소 다운로드를 지원합니다.

## Google OAuth 설정

Google Cloud Console에서 OAuth Client를 만들 때 애플리케이션 유형은 **Web application**으로 선택하고, 다음 Redirect URI를 등록합니다.

```text
http://localhost:8501/oauth2callback
```

`.env`에는 Google Client ID와 신뢰할 API 주소를 넣습니다.

```env
GOOGLE_OAUTH_CLIENT_ID=...apps.googleusercontent.com
TRANSLATION_API_URL=http://127.0.0.1:8000
```

`.streamlit/secrets.toml`에는 같은 Client ID와 Client secret을 설정합니다.

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "충분히-긴-무작위-문자열"
client_id = "...apps.googleusercontent.com"
client_secret = "Google-Client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
expose_tokens = "id"
```

`.env`와 `secrets.toml`은 실제 비밀값을 담으므로 Git이나 제출 폴더에 포함하지 않습니다. Google OAuth 앱이 Testing 상태라면 로그인할 계정을 Test user로 등록해야 합니다.

## 서버 실행

터미널을 두 개 열어 각각 실행합니다.

```powershell
# 터미널 1: FastAPI
cd D:\Codes\sandbox\translate-project
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# 터미널 2: Streamlit
cd D:\Codes\sandbox\translate-project
uv run streamlit run frontend/app.py
```

- Streamlit: `http://127.0.0.1:8501`
- FastAPI Swagger: `http://127.0.0.1:8000/docs`

Streamlit은 프로젝트 루트에서 실행해야 `.streamlit/secrets.toml`과 `.env`를 읽습니다. OAuth는 iframe에 임베드된 앱을 지원하지 않으므로 브라우저에서 Streamlit 주소를 직접 엽니다.

## 모델과 보안 설계

API 언어 코드 `ko`, `en`, `zh`, `ja`는 NLLB 언어 토큰 `kor_Hang`, `eng_Latn`, `zho_Hans`, `jpn_Jpan`으로 변환됩니다. 번역 시 `tokenizer.src_lang`과 `forced_bos_token_id`를 설정합니다.

FastAPI는 Google ID 토큰의 서명, audience, 만료 시간, issuer, 사용자 고유값 `sub`를 확인합니다. Streamlit에서 API URL을 직접 수정할 수 없게 해 ID 토큰이 임의의 주소로 전송되지 않도록 했습니다. 토큰이 만료되면 재로그인을 안내합니다.

## 테스트

```powershell
uv run pytest -q
```

최종 테스트 결과:

```text
9 passed
```
