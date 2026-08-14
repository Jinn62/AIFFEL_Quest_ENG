# Day 3: 비동기 처리와 에러 핸들링

Day 2에서 만든 MNIST 추론 API를 바탕으로, 동기 추론이 동시 요청을 막는 문제를 확인하고 `run_in_executor` 기반의 전용 스레드풀, 로깅, 글로벌 예외 처리까지 적용했다.

## 1. 섹션 2 수행내역 — 동기와 비동기 실행 비교

동일하게 2초가 걸리는 작업 세 개를 순차 실행과 비동기 실행으로 비교했다.

```text
[동기 실행]
작업 A → 작업 B → 작업 C 순서로 종료
총 소요 시간: 6.0초

[비동기 실행]
작업 A, B, C가 함께 시작·종료
총 소요 시간: 2.0초
```

## 2. 섹션 3 수행내역 — 동기 추론의 블로킹 문제

비교 서버인 `app/main_sync_problem.py`에 두 엔드포인트를 만들었다.

```python
@app.post("/predict/blocking")
async def predict_blocking():
    time.sleep(INFERENCE_TIME)


@app.post("/predict/threadpool")
def predict_threadpool():
    time.sleep(INFERENCE_TIME)
```

`/predict/blocking`은 `async def` 내부에서 동기 함수 `time.sleep()`을 호출하므로 이벤트 루프가 멈춘다. 따라서 3초짜리 요청 3개가 동시에 들어와도 순서대로 처리되어 약 3초, 6초, 9초에 응답하게 된다. 이때 `/health` 요청도 대기할 수 있다.

반대로 일반 `def`로 선언한 `/predict/threadpool`은 FastAPI가 기본 스레드풀에서 실행한다. 이벤트 루프를 직접 막지 않아 여러 요청을 겹쳐 처리할 수 있음을 확인했다.

## 3. 섹션 4 수행내역 — `run_in_executor`와 전용 스레드풀

`app/main_async_solution.py`에서 추론 전용 스레드풀을 만들었다.

```python
inference_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="inference",
)
```

권장 엔드포인트는 다음 방식이다.

```python
@app.post("/predict/v3-executor")
async def predict_v3():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        inference_executor,
        heavy_inference,
    )
    return {"method": "v3-executor", **result}
```

이 방식은 동기 함수 `heavy_inference()`를 최대 4개의 전용 작업자 스레드에서 실행한다. `await`로 현재 요청의 결과는 기다리되, 이벤트 루프 자체는 멈추지 않아 다른 HTTP 요청을 처리할 수 있다.

## 4. 섹션 5·6 수행내역 — 최종 MNIST API, 로깅, 오류 처리

최종 서버는 `app/main_final.py`이며 다음 요소를 결합했다.

```text
Pydantic 입력 검증
  → NumPy/PyTorch 전처리
  → inference_executor의 모델 추론
  → Pydantic 응답 생성
  → 미들웨어 로그 및 X-Process-Time 응답 헤더
```

서버 시작 시 모델을 한 번만 로드하도록 작성했다.

```python
@app.on_event("startup")
async def startup():
    global model
    logger.info(f"모델 로드 중: {MODEL_PATH}")
    model = load_model(MODEL_PATH)
    logger.info("모델 로드 완료")
```

실행 결과:

```text
2026-08-14 10:57:54 INFO [ml_api] 모델 로드 완료
서버 실행됨: http://127.0.0.1:8000
```

실제 MNIST 추론 동시 요청 결과는 모두 HTTP 200으로 처리됐다.

```text
1개 동시 요청: 전체 2.05초
2개 동시 요청: 전체 2.03초
4개 동시 요청: 전체 2.03초
8개 동시 요청: 전체 2.03초
```

`max_workers=4` 환경에서 1·2·4·8개 요청 모두 비슷한 전체 시간이 관찰됐으며, 각 요청의 서버 처리 로그에는 `POST /predict/pixels -> 200`이 기록됐다.

오류 상황도 확인했다.

```text
[잘못된 28x28 크기] POST /predict/pixels -> 422
[잘못된 Base64 이미지] POST /predict/image -> 400
[헬스체크] GET /health -> 200
{'status': 'healthy', 'model_loaded': True}
```

`RequestLoggingMiddleware`는 모든 요청의 메서드, 경로, 상태 코드, 처리 시간을 기록하고 `X-Process-Time` 응답 헤더를 추가한다. `register_error_handlers(app)`은 예상하지 못한 예외를 서버 로그에 남기고, 클라이언트에는 내부 traceback 대신 안전한 500 JSON 응답을 반환한다.

## 5. 체크포인트 답변

### 섹션 2. 동기와 비동기 기초

#### 1. `time.sleep(3)`과 `await asyncio.sleep(3)`의 핵심 차이는 무엇입니까?

**답변:** `time.sleep(3)`은 실행 중인 스레드를 멈추므로 이벤트 루프도 멈춘다. `await asyncio.sleep(3)`은 현재 코루틴만 기다리는 상태로 만들고 제어권을 이벤트 루프에 돌려주므로, 그동안 다른 코루틴을 실행할 수 있다.

#### 2. 모델 추론처럼 CPU를 계속 사용하는 작업에서 `async/await`만으로 동시 처리가 안 되는 이유는 무엇입니까?

**답변:** `async/await`은 주로 네트워크 대기 같은 I/O 대기 시간에 다른 작업으로 전환하는 방식이다. CPU/GPU 연산은 기다리는 상태가 아니라 실제 실행 중이므로 이벤트 루프에서 그대로 수행하면 다른 요청을 처리할 수 없다.

### 섹션 3. 동기 추론의 문제

#### 1. `async def` 안에서 `time.sleep(3)`을 호출하면 왜 다른 요청까지 지연됩니까?

**답변:** 동기 함수가 이벤트 루프가 실행되는 스레드를 점유하기 때문이다. 이벤트 루프가 멈추므로 그 스레드에서 처리할 다른 코루틴과 요청도 시작하거나 재개할 수 없다.

#### 2. 일반 `def`로 선언된 엔드포인트는 FastAPI가 내부적으로 어떻게 처리합니까?

**답변:** FastAPI/Starlette가 기본 스레드풀로 작업을 넘겨 실행한다. 따라서 이벤트 루프를 직접 블로킹하지 않는다.

#### 3. blocking 추론 중 헬스체크까지 막히면 실무에서 어떤 문제가 발생할 수 있습니까?

**답변:** 로드밸런서나 컨테이너 오케스트레이터가 서버를 비정상으로 판단해 트래픽을 제외하거나 재시작할 수 있다. 실제 서버는 단지 느린 추론을 처리 중이었는데 불필요한 장애 처리가 발생한다.

### 섹션 4. `run_in_executor`

#### 1. `run_in_executor`가 이벤트 루프 블로킹을 방지하는 원리는 무엇입니까?

**답변:** 무거운 동기 함수를 이벤트 루프가 아닌 executor의 작업자 스레드에서 실행한다. 이벤트 루프는 완료 결과를 `await`할 뿐, 기다리는 동안 다른 요청을 처리할 수 있다.

#### 2. `run_in_executor`의 첫 번째 인자에 `None`을 넣으면 어떤 스레드풀이 사용됩니까?

**답변:** asyncio 이벤트 루프의 기본 executor, 즉 기본 `ThreadPoolExecutor`가 사용된다.

#### 3. 일반 `def`와 `async def + run_in_executor`의 핵심 차이는 무엇입니까?

**답변:** 일반 `def`는 FastAPI의 기본 스레드풀에 엔드포인트 전체를 맡긴다. `run_in_executor`는 `async def`의 흐름을 유지하면서 무거운 특정 작업만 개발자가 지정한 전용 executor에 위임한다.

#### 4. GPU 추론 시 스레드풀 크기를 1~2로 제한하는 이유는 무엇입니까?

**답변:** GPU 메모리는 제한되어 있고, 과도한 동시 추론은 메모리 부족·문맥 전환·지연 증가를 유발할 수 있다. GPU 용량과 모델 크기에 맞춰 작은 값으로 제한하는 편이 안정적이다.

### 섹션 5. 에러 핸들링과 로깅

#### 1. 글로벌 Exception Handler를 사용하면 어떤 반복을 줄일 수 있습니까?

**답변:** 모든 엔드포인트에 같은 일반 예외 처리, traceback 기록, 500 JSON 응답 반환 코드를 반복해서 작성하는 일을 줄인다.

#### 2. 클라이언트에게 스택 트레이스를 노출하면 안 되는 이유는 무엇입니까?

**답변:** 파일 경로, 내부 모듈, 라이브러리 버전, 구현 세부 정보가 노출되어 보안 위험이 생기고 사용자에게도 이해하기 어려운 오류가 전달되기 때문이다.

#### 3. `logging` 모듈이 `print()`보다 나은 점은 무엇입니까?

**답변:** 로그 수준(INFO/WARNING/ERROR), 시간·로거명·형식 설정, 출력 대상 분리, 운영 환경의 수집 도구 연동을 지원한다. `print()`보다 검색·필터링·장기 보관이 쉽다.

### Day 3 최종 체크포인트

#### Q1. 동기 서버에서 3초 걸리는 추론을 3명이 동시에 요청하면 총 몇 초 걸립니까?

**답변:** 이벤트 루프를 막는 동기 추론이라면 순차 처리되므로 약 9초다.

#### Q2. `time.sleep(3)`과 `await asyncio.sleep(3)`의 핵심 차이는 무엇입니까?

**답변:** 전자는 이벤트 루프가 있는 스레드를 멈추고, 후자는 현재 코루틴만 대기시켜 다른 코루틴이 실행될 기회를 준다.

#### Q3. `async def` 안에서 동기 블로킹 코드를 실행하면 왜 헬스체크까지 영향받습니까?

**답변:** 헬스체크도 같은 이벤트 루프에서 처리되므로, 동기 코드가 그 이벤트 루프를 점유하면 헬스체크 요청을 처리할 수 없다.

#### Q4. `run_in_executor`가 이벤트 루프 블로킹을 방지하는 원리는 무엇입니까?

**답변:** 동기 추론을 별도 작업자 스레드로 보내고, 이벤트 루프는 완료 통지만 비동기로 기다리기 때문이다.

#### Q5. 글로벌 Exception Handler를 사용하는 이유는 무엇입니까?

**답변:** 예상하지 못한 예외를 일관된 형식으로 기록하고, 내부 정보가 노출되지 않는 안전한 오류 응답을 만들기 위해서다.

#### Q6. 클라이언트에게 스택 트레이스를 노출하면 안 되는 이유는 무엇입니까?

**답변:** 내부 구현과 민감한 정보를 노출할 수 있으며, 사용자에게는 해결할 수 없는 기술적인 정보이기 때문이다.
