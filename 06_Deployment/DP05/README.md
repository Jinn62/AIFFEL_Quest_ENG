# AIFFEL Campus Online Code Peer Review Templete
- 코더 : 채진현 (Jinn62)
- 리뷰어 : 천세문


# PRT(Peer Review Template)

- [x]  **1. 주어진 문제를 해결하는 완성된 코드가 제출되었나요?**
    - **California Housing 정형 데이터 회귀 모델 학습부터 FastAPI 백엔드 구축, Streamlit 프론트엔드 연동, 통합 테스트 및 결과 시각화까지 전체 서빙 파이프라인이 완성도 높게 구현되었습니다.**
    - `Day05.ipynb` 노트북의 36개 실행 셀이 에러 없이 순차적으로 모두 실행 완료되었습니다.
    - **근거 1) 모델 학습 및 테스트 데이터셋 MAE 평가 완료 (셀 21 출력)**
      ```text
      테스트 MSE:  0.3253
      테스트 MAE:  0.3873 ($100,000 단위)
      테스트 MAE:  $38,726 (실제 금액)
      ```
    - **근거 2) 모델 가중치 및 전처리 통계량 분리 저장 & `HousingPredictor` 단일 추론 검증 (셀 23, 26 출력)**
      ```text
      ✅ 모델 저장: models/housing_model.pth (13.3 KB)
      ✅ 전처리 파라미터 저장: models/housing_preprocessing.json
      입력 피처: {'MedInc': 1.6812, 'HouseAge': 25.0, 'AveRooms': 4.1922, 'AveBedrms': 1.0222, ...}
      예측 가격: $68,345
      실제 가격: $47,700
      ```
    - **근거 3) 4종 통합 테스트 100% All Pass (셀 53~63 출력)**
      - `테스트 1 (정상 요청)`: 다양한 주택 케이스별 가격 산출 ($186,049 등)
      - `테스트 2 (에러 상황)`: 필드 누락, 위도 범위 초과 등 4개 케이스 모두 HTTP 422 반환 확인
      - `테스트 3 (동시 요청)`: 8개 동시 요청을 2.02초 만에 비동기로 완벽 처리
      - `테스트 4 (헬스체크)`: `/health` 엔드포인트 200 OK 정상 응답 확인
    - **근거 4) Streamlit 대시보드 실행 화면 및 새니티 체크 스크린샷 첨부 (`Day5.md` 문서)**
      - 기본 예측 화면(`images/test1.png`), 소득 변화 비교(`images/test2_1.png`, `images/test2_2.png`), 서버 연결 오류 처리(`images/test3.png`)가 모두 빠짐없이 첨부되어 있습니다.
    
- [x]  **2. 전체 코드에서 가장 핵심적이거나 가장 복잡하고 이해하기 어려운 부분에 작성된 주석 또는 doc string을 보고 해당 코드가 잘 이해되었나요?**
    - **핵심 블록 1) `app/housing_model.py`의 `HousingPredictor.predict()` 메서드 (셀 25)**
      - 딕셔너리 입력 시 JSON 키 순서가 보장되지 않으므로, 모델이 학습할 때 정의된 `self.feature_names` 순서대로 명시적 정렬(`[features[name] for name in self.feature_names]`)을 수행하는 이유가 주석과 함께 명확히 작성되었습니다.
      - 학습 데이터 통계량(`mean`, `std`)을 사용한 Z-score 정규화 공식 `(raw_features - self.mean) / self.std`이 캡슐화되어 있어 이해하기 쉬웠습니다.
    - **핵심 블록 2) `app/housing_api.py`의 비동기 추론 처리 (셀 33)**
      - PyTorch 모델 추론과 같은 CPU-bound 동기 작업을 FastAPI 이벤트 루프에서 직접 실행할 경우 발생할 수 있는 블로킹 현상을 방지하기 위해 `loop.run_in_executor(None, predictor.predict, features)`로 스레드풀에 작업을 위임하는 패턴이 주석과 함께 깔끔하게 작성되었습니다.
    - **핵심 블록 3) `app/housing_schemas.py`의 도메인 제약조건 (셀 29)**
      - Pydantic V2의 `Field(..., ge=32, le=42, description="위도 (캘리포니아: 32 ~ 42)")`와 같이 캘리포니아 주의 지리적 경계 범위를 벗어난 이상 데이터를 API 진입점에서 차단하는 이유가 주석 및 `Day5.md` 체크포인트에 잘 설명되어 있습니다.
        
- [x]  **3. 에러가 난 부분을 디버깅하여 문제를 해결한 기록을 남겼거나 새로운 시도 또는 추가 실험을 수행해봤나요?**
    - **디버깅 기록**:
      - `Day5.md` 회고에 기술된 바와 같이, API 기본 주소(루트 `/`)에 POST 요청을 보냈을 때 발생하는 HTTP 404 에러 원인을 파악하고, 엔드포인트를 `/predict`로 명확히 지정하여 해결한 트러블슈팅 과정이 잘 기록되어 있습니다.
    - **새로운 시도 및 추가 실험 (Sanity Check & Error Handling)**:
      1. **소득 변화 새니티 체크(Sanity Check)**: 다른 변수를 고정한 상태에서 중위 소득(`MedInc`)을 `8.0`(고소득)으로 올렸을 때 `$354,564`, `1.0`(저소득)으로 낮췄을 때 `$102,477`로 예측 가격이 도메인 상식에 부합하게 변하는지 정량적으로 검증하고 캡처를 첨부했습니다 (`test2_1.png`, `test2_2.png`).
      2. **서버 연결 예외 처리 UI 검증**: FastAPI 서버가 꺼져 있을 때 Streamlit 프론트엔드가 크래시되지 않고 연결 오류 메시지를 우아하게 표시하는 예외 처리(`test3.png`)를 추가 검증했습니다.
      3. **4종 엣지 케이스 유효성 검증**: 통합 테스트 셀 57에서 필수 필드 누락, 위도 범위 초과, 잘못된 타입, 잘못된 JSON 포맷에 대해 백엔드가 422 상태 코드로 방어하는지 모두 실험했습니다.
        
- [x]  **4. 회고를 잘 작성했나요?**
    - **`Day5.md`의 체크포인트 총정리 및 최종 회고가 매우 구체적이고 깊이 있게 작성되었습니다.**
      - **핵심 배운 점**: 단순히 모델 가중치(`model.pth`)만 저장해서는 배포 환경을 온전히 재현할 수 없으며, 학습 시점의 전처리 파라미터(`mean`, `std`, `feature_names`)를 함께 보존해야 학습-서빙 불일치(Train-Serve Skew)와 데이터 누수(Data Leakage)를 원천 차단할 수 있다는 점을 핵심 원리로 정리했습니다.
      - **지표 관점의 고찰**: 단일 샘플의 예측값과 실제값의 단순 차이에 매몰되지 않고, 전체 테스트셋의 MAE($38,726)와 같은 객관적 메트릭으로 서빙 모델의 신뢰도를 평가해야 함을 명확히 짚었습니다.
      - **향후 개선 방향**: 은닉층 크기, 학습 epoch, 학습률 튜닝 등을 통한 MAE 개선 방향을 제시했습니다.
        
- [x]  **5. 코드가 간결하고 효율적인가요?**
    - **모듈화 및 역할 분리가 매우 깔끔합니다.**
      - `app/housing_model.py`: 모델 아키텍처 및 전처리/추론 캡슐화
      - `app/housing_schemas.py`: Pydantic V2 Request/Response DTO 정의
      - `app/housing_api.py`: FastAPI 라우팅, 에러 핸들러 연동, 비동기 스레드풀 추론
      - `frontend/app_housing.py`: Streamlit 컴포넌트 분리 및 시각화
    - **PEP8 표준 스타일을 충실히 준수**하였으며, `model_dump()` 등 Pydantic 최신 API를 적절하게 활용했습니다.


# 회고(참고 링크 및 코드 개선)
```
[리뷰어 회고]
- 모델 학습부터 FastAPI 비동기 서빙, Streamlit UI, 4종 통합 테스트까지 전체 서빙 파이프라인을 완성도 높게 구현하셨습니다.
- 특히 소득 변화(8.0 vs 1.0)에 따른 예측 가격의 합리성을 검증한 새니티 체크(Sanity Check)와 `run_in_executor`를 활용한 이벤트 루프 논블로킹 처리가 매우 인상적이었습니다.
- 전처리 파라미터(mean, std, 피처 순서)를 분리 저장하여 Train-Serve Skew를 원천 방지한 점도 훌륭합니다.

[참고 링크]
- FastAPI Concurrency: https://fastapi.tiangolo.com/async/
- Pydantic V2 Validators: https://docs.pydantic.dev/latest/concepts/validators/

[코드 개선 팁: Pydantic V2 교차 필드 검증]
- 방 수보다 침실 수가 많은 비정상 입력을 방지하기 위해 스키마에 아래 검증 로직을 추가하면 좋습니다.

@model_validator(mode="after")
def validate_cross_fields(self):
    if self.AveBedrms > self.AveRooms:
        raise ValueError("침실 수가 전체 방 수보다 클 수 없습니다.")
    return self
```