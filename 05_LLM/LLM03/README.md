# AIFFEL Campus Online Code Peer Review Templete
- 코더 : 채진현
- 리뷰어 : 조희연


# PRT(Peer Review Template)
- [x]  **1. 주어진 문제를 해결하는 완성된 코드가 제출되었나요?**
    - 문제에서 요구하는 최종 결과물이 첨부되었는지 확인
        - 중요! 해당 조건을 만족하는 부분을 캡쳐해 근거로 첨부
    - **네, 완성되었습니다.** 과제의 완료 조건인 "두 도메인의 RAGAS 비교표 출력"과 "Langfuse Traces에서 `rag-question`·`ragas-evaluation` 확인"을 모두 충족합니다.
        - KorQuAD(위키)·KLUE-MRC(뉴스) 두 도메인에서 Naive RAG와 Advanced RAG를 실행하고, 4개 RAGAS 지표(Faithfulness / Answer Relevancy / Context Precision / Context Recall)의 `naive / advanced / delta` 비교표가 실제 출력값으로 첨부되어 있습니다.
        ```
                            naive                       advanced                    delta
        domain    KLUE-MRC  KorQuAD          KLUE-MRC  KorQuAD          KLUE-MRC  KorQuAD
        answer_relevancy     0.250    0.323             0.313    0.356             0.062    0.034
        context_precision    0.600    0.783             0.892    0.842             0.292    0.058
        context_recall       0.600    0.850             0.850    0.850             0.250    0.000
        faithfulness         0.650    0.800             0.800    0.825             0.150    0.025
        ```
        - `run_pipeline`에서 각 질문을 `rag-question` trace로, `evaluate_pair`에서 도메인별 평가를 `ragas-evaluation` trace로 기록하고, 마지막에 `Attached 320 RAGAS scores. Langfuse events flushed.` 로그로 trace 부착까지 확인됩니다.

- [x]  **2. 전체 코드에서 가장 핵심적이거나 가장 복잡하고 이해하기 어려운 부분에 작성된 
주석 또는 doc string을 보고 해당 코드가 잘 이해되었나요?**
    - 해당 코드 블럭을 왜 핵심적이라고 생각하는지 확인
    - 해당 코드 블럭에 doc string/annotation이 달려 있는지 확인
    - 해당 코드의 기능, 존재 이유, 작동 원리 등을 기술했는지 확인
    - 주석을 보고 코드 이해가 잘 되었는지 확인
        - 중요! 잘 작성되었다고 생각되는 부분을 캡쳐해 근거로 첨부
    - **네, 매우 잘 이해되었습니다.** 이 프로젝트에서 가장 핵심적이고 복잡한 부분은 Advanced 검색 파이프라인(`advanced_retrieve`)과 Self-RAG 루프(`self_rag`)라고 생각합니다. Multi-Query → HyDE → RRF 병합 → Cross-Encoder rerank로 이어지는 여러 검색 기법이 한 흐름으로 결합되고, 여기에 근거성 비평·재검색까지 얹혀 있어 흐름을 놓치기 쉬운 지점입니다.
    - 모든 함수에 **영문 1줄 + 한글 1줄** 형태의 주석이 일관되게 달려 있어, 각 단계의 기능·존재 이유·작동 원리가 명확합니다. 특히 아래 주석이 인상적이었습니다.
        - RRF: `# RRF로 여러 순위 목록을 합치며, 여러 검색에서 상위에 반복된 문서에 더 높은 점수를 줍니다.` → 점수식 `1.0 / (k + rank)`의 의미가 바로 이해됩니다.
        - HyDE: `# 가상의 참고 문단을 생성하고 추가 검색 질의로 사용합니다.` → HyDE를 "답 생성"이 아닌 "검색 질의 확장"으로 쓴다는 설계 의도가 드러납니다.
        - Self-RAG: `# 검색 필요성을 판단하고 근거성을 비평한 뒤 필요하면 한 번 재시도합니다.` → `force_retrieval`, `critique`, `retries`로 이어지는 제어 흐름이 명확합니다.
    - 프롬프트도 답변/질의확장/HyDE/검색판단/비평으로 역할이 분리되어 있어 각 LLM 호출의 목적이 헷갈리지 않았습니다.

- [x]  **3. 에러가 난 부분을 디버깅하여 문제를 해결한 기록을 남겼거나
새로운 시도 또는 추가 실험을 수행해봤나요?**
    - 문제 원인 및 해결 과정을 잘 기록하였는지 확인
    - 프로젝트 평가 기준에 더해 추가적으로 수행한 나만의 시도, 
    실험이 기록되어 있는지 확인
        - 중요! 잘 작성되었다고 생각되는 부분을 캡쳐해 근거로 첨부
    - **네, 기본 과제를 넘어선 추가 시도가 풍부합니다.**
        - Chroma 익명 텔레메트리 오류(`Failed to send telemetry event ...`)를 인지하고 `ANONYMIZED_TELEMETRY=FALSE`와 `Settings(anonymized_telemetry=False)`로 선제 차단한 점이 좋았습니다.
        - `.env`에서 `LANGFUSE_HOST`와 `LANGFUSE_BASE_URL`을 모두 지원하도록 처리하고, 필수 키가 없으면 `assert`로 조기 중단하도록 방어 코드를 넣었습니다.
        - 단순 Naive vs Advanced 비교를 넘어 **두 도메인(위키·뉴스) 교차 실험**을 수행하고, 질문별 RAGAS 점수를 원래 trace에 부착(`attach_ragas_scores`)해 Langfuse에서 저점 사례부터 정렬·분석할 수 있게 만든 점이 특히 인상적입니다.
        - 결과 분석 셀에서 **실패 유형을 검색 실패 / 생성 실패 / 평가 지표 오판 3가지로 분류**한 것이 실질적인 디버깅 기록입니다. 예: "유아인의 고향"은 후보 집합에 근거 자체가 없는 검색 실패, "대형망치 쿠데타 재심 연도"·"현대로지스틱스 국적"은 답이 정답과 일치하는데 Faithfulness가 0으로 나온 LLM Judge 오판 사례로 짚어냈습니다.

- [x]  **4. 회고를 잘 작성했나요?**
    - 주어진 문제를 해결하는 완성된 코드 내지 프로젝트 결과물에 대해
    배운점과 아쉬운점, 느낀점 등이 기록되어 있는지 확인
    - 전체 코드 실행 플로우를 그래프로 그려서 이해를 돕고 있는지 확인
        - 중요! 잘 작성되었다고 생각되는 부분을 캡쳐해 근거로 첨부
    - **네, 회고와 흐름도가 모두 충실합니다.**
        - `## 실험 흐름도`에 **Mermaid flowchart**로 데이터 로드 → 인덱스 구축 → Naive/Advanced 분기 → RRF·Reranking·Self-RAG → Langfuse trace → RAGAS 평가 → 저점 사례 분류 → 재실험까지 전체 파이프라인이 한눈에 보이게 그려져 있습니다.
        - `## 8. 결과 분석과 해석`에서 도메인별 점수 변화를 수치와 함께 해석하고, "KLUE-MRC(뉴스)에서 개선 폭이 큰 이유"를 인물·기관·날짜 등 표현이 다양한 뉴스 특성과 Multi-Query/HyDE의 검색 확장으로 잘 연결했습니다.
        - 마지막 인용문에서 "도메인별 20문항의 소규모 평가이므로 점수 차이를 확정적 성능 우위로 단정하지 않는다"라고 실험 규모의 한계를 스스로 명시한 점이 신뢰가 갔습니다.

- [x]  **5. 코드가 간결하고 효율적인가요?**
    - 파이썬 스타일 가이드 (PEP8) 를 준수하였는지 확인
    - 코드 중복을 최소화하고 범용적으로 사용할 수 있도록 함수화/모듈화했는지 확인
        - 중요! 잘 작성되었다고 생각되는 부분을 캡쳐해 근거로 첨부
    - **네, 간결하고 모듈화가 잘 되어 있습니다.**
        - `load_korquad_records` / `load_klue_records`가 서로 다른 데이터셋을 **공통 레코드 스키마**로 정규화하고, `build_vectorstore` / `run_pipeline` / `evaluate_pair` / `summarize_pair`가 도메인·파이프라인에 상관없이 재사용됩니다. 덕분에 두 도메인 × 두 파이프라인 실험이 `run_pipeline(...)` 4줄로 깔끔하게 표현됩니다.
        - `invoke_chain` / `trace_config` / `trace_observation`으로 Langfuse 콜백·태그 설정을 한 곳에 모아 중복을 제거했습니다.
        - 상수(`CORPUS_N`, `EVAL_N`, `SEED`, 모델명)를 상단에 분리하고 `SEED`로 재현성을 확보했습니다. 함수·변수명이 명확하고 PEP8 스타일에 큰 위반이 없습니다.


# 회고(참고 링크 및 코드 개선)
```
[리뷰어 조희연의 회고]

- 여러 Advanced RAG 기법(Multi-Query, HyDE, RRF, Cross-Encoder Reranking, Self-RAG)을
  하나의 파이프라인으로 결합하고, 이를 RAGAS 4지표 + Langfuse trace로 정량·정성 평가한
  완성도 높은 프로젝트였습니다. 특히 "평균 점수만 보지 말고 저점 trace를 열어
  검색/생성/평가 중 어디서 실패했는지 구분하라"는 관점이 인상 깊었고,
  평가 방법론 자체를 배울 수 있었습니다.

- 참고 링크
  - RAGAS 지표 정의: https://docs.ragas.io/en/stable/concepts/metrics/
  - RRF 원 논문(Cormack et al., 2009): https://plg.uwaterloo.ca/~gvcormack/cormacksigir09-rrf.pdf
  - HyDE(Precise Zero-Shot Dense Retrieval): https://arxiv.org/abs/2212.10496

- 개선 제안 (코더 본인도 회고에서 언급한 부분과 동일선상)
  1) Self-RAG 재시도 후에도 critique=NOT_SUPPORTED이면 현재는 마지막 답변을 그대로
     반환할 수 있습니다. 최종 실패 시 "문서에서 확인할 수 없습니다"로 강제하는
     거절(reject) 정책을 넣으면 Faithfulness가 낮은 hallucination을 줄일 수 있어 보입니다.
  2) 단답형 정답에서 Faithfulness가 0으로 오판되는 사례가 관측되었으므로,
     정답성 판단을 보조할 EM/F1 같은 lexical 지표를 함께 기록하면
     LLM Judge 오판과 실제 실패를 더 잘 구분할 수 있을 것 같습니다.
  3) fan_out_queries에서 variants[:4] 슬라이싱과 앞서 4개 생성 프롬프트가 맞물려
     최대 5개 질의가 되는데, 생성 개수와 사용 개수를 상수로 묶어두면
     가독성이 더 좋아질 것 같습니다. (사소한 제안)

- 전반적으로 주석·회고·흐름도·실패 분석까지 모두 갖춘 모범적인 제출물이었습니다.
  많이 배웠습니다. 고생하셨습니다!
```
