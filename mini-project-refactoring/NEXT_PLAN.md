# LangChain 학습형 리팩토링 후속 계획

## 1. 문서 목적

이 문서는 [PLAN.md](c:\Users\user\working\langchain_v0_basics\hk-llm-1day\refactoring\PLAN.md)에서 우선순위를 낮게 둔 나머지 범위, 즉 아래 3개 단계를 어떻게 이어서 구현하고 확장할지 정리한 후속 계획서다.

- Phase 3: 질문 생성
- Phase 4: 질문 평가 및 개선 루프
- Phase 5: 질문 분류 및 랭킹

기준 프로젝트는 동일하게 `hk-llm-1day/project.ipynb`의 **AI 면접 질문 생성 에이전트**다.  
이 문서 역시 학습형 리팩토링 관점을 유지하며, "완성품을 대신 구현"하기보다 "직접 채워 넣을 실습 구조"를 만드는 데 목적이 있다.

## 2. PLAN.md 와의 관계

정리하면 역할 분담은 아래와 같다.

- [PLAN.md](c:\Users\user\working\langchain_v0_basics\hk-llm-1day\refactoring\PLAN.md): Phase 1, Phase 2 중심 1차 학습 계획
- [NEXT_PLAN.md](c:\Users\user\working\langchain_v0_basics\hk-llm-1day\refactoring\NEXT_PLAN.md): Phase 3, Phase 4, Phase 5 중심 후속 구현 및 확장 계획

권장 학습 순서는 다음과 같다.

1. `PLAN.md` 기준으로 Phase 1, 2를 먼저 실습한다.
2. 구조화된 context 데이터가 만들어지면 이 문서 기준으로 Phase 3~5를 이어 붙인다.
3. 마지막에 전체 파이프라인을 노트북 한 흐름으로 연결한다.

## 3. 현재 원본 코드 상태 요약

### Phase 3

- `hk-llm-1day/lib/phase3.py`는 아직 실질 구현이 없다.
- 실제 질문 생성 로직은 `project.ipynb` 안 셀에 더 가깝게 존재한다.
- 따라서 Phase 3은 "기존 파일을 리팩토링"하기보다 "노트북 기반 로직을 새로 정리하는 작업"에 가깝다.

### Phase 4

관련 파일:

- `hk-llm-1day/lib/phase4.py`

현재 구조:

- 질문 1개 평가
- FAIL이면 질문 1개 개선
- 개선 질문 재평가
- 최대 `max_retries`만큼 반복
- 각 시도 이력을 `attempts`에 저장
- 최종 PASS 질문만 추출하는 헬퍼 존재

즉, 이미 "평가 -> 개선 -> 재평가"라는 반복 루프 골격은 잘 잡혀 있다.

### Phase 5

관련 파일:

- `hk-llm-1day/lib/phase5.py`

현재 구조:

- 질문 1개를 5개 유형 중 하나로 분류
- 카테고리별 질문들을 점수화
- 점수 기준으로 정렬
- 카테고리별 랭킹 해설 생성
- 최종 출력 포맷팅

즉, 이미 후처리 파이프라인 형태가 있으므로 LangChain으로 옮기기 좋은 상태다.

## 4. 후속 리팩토링 목표

이 문서에서 다루는 후속 목표는 아래와 같다.

1. Phase 3 질문 생성 단계를 학습 가능한 LangChain chain으로 설계한다.
2. Phase 4의 평가-개선 루프를 LangChain Runnable 관점으로 재구성한다.
3. Phase 5의 분류-점수화-랭킹을 체인과 후처리 관점으로 정리한다.
4. 이 단계들도 모두 `TODO` 중심 실습으로 남겨 사용자가 직접 구현할 수 있게 한다.
5. 최종적으로 Phase 1~5를 하나의 학습용 파이프라인으로 연결할 수 있게 한다.

## 5. 전체 연결 구조

후속 단계의 입력과 출력은 아래처럼 이해하면 된다.

```text
Phase 2 결과
  -> question context
  -> Phase 3 질문 생성
  -> Phase 4 질문 평가/개선 루프
  -> PASS 질문 리스트
  -> Phase 5 질문 분류/점수화/랭킹
  -> 최종 리포트
```

즉, 이 문서의 핵심은 "Phase 2가 만든 context를 어떻게 실제 질문 리스트와 최종 리포트로 이어줄 것인가"이다.

## 6. Phase 3 상세 계획: 질문 생성

### 6-1. Phase 3의 역할

Phase 3은 단순히 질문 문장 몇 개를 만드는 단계가 아니다.  
원본 프로젝트 맥락에서 보면, 아래 요소를 반영한 질문을 만들어야 한다.

- JD에서 요구하는 역량
- 자소서에서 확인된 실제 경험 근거
- 검증 포인트
- 리스크 포인트
- 꼬리질문으로 이어질 수 있는 주제

즉, "문항별 컨텍스트를 실제 면접 질문 세트로 바꾸는 단계"다.

### 6-2. 권장 입력 구조

Phase 3 입력은 최소 아래 정보를 포함하는 것이 좋다.

- `question_id`
- `question_text`
- `answer_text`
- `item_type`
- `matched_jd`
- `key_points`
- `possible_risks`
- `question_context.main_topics`
- `question_context.verification_points`
- `question_context.risk_points`
- `question_context.followup_topics`

이 구조는 이미 Phase 2 결과에 대부분 들어 있으므로, 별도 추가 수집보다 입력 모델을 명확히 정의하는 게 중요하다.

### 6-3. 추천 산출물 구조

Phase 3 출력은 질문 문자열 리스트만 던지기보다 아래처럼 구조화하는 것이 좋다.

```json
{
  "question_id": "Q1",
  "generated_questions": [
    {
      "question": "...",
      "question_type": "경험검증",
      "source_topic": "AI 서빙 플랫폼 성능 향상",
      "intent": "구체적 역할 검증"
    }
  ]
}
```

이렇게 해야 Phase 4와 Phase 5에서 디버깅과 추적이 쉬워진다.

### 6-4. LangChain 학습 포인트

Phase 3에서 중점적으로 익힐 포인트는 아래와 같다.

- `ChatPromptTemplate`로 긴 생성 프롬프트를 구조화하는 방법
- `with_structured_output()`으로 질문 리스트를 안정적으로 받는 방법
- `RunnableLambda`로 여러 문항의 질문 리스트를 flatten 하는 방법
- 입력 context를 prompt 친화적인 문자열로 가공하는 방법

### 6-5. 노트북 실습 구성안

권장 섹션 제목:

- `Phase 3 질문 생성 실습`

세부 구성:

1. Phase 2 결과 샘플 다시 보기
2. 질문 생성용 입력 모델 정의
3. 질문 생성 prompt 작성
4. structured output 모델 정의
5. 단일 문항 기준 질문 4개 생성
6. 여러 문항으로 확장
7. 질문 리스트 평탄화

### 6-6. TODO 후보

- 질문 생성 결과용 Pydantic 모델 정의
- 단일 문항 질문 생성 prompt 작성
- `model.with_structured_output()` 적용
- 생성 질문 4개를 반환하는 chain 만들기
- 여러 문항 결과를 하나의 리스트로 합치기

### 6-7. 구현 시 주의점

- 질문 수를 고정할지 선택 가능하게 할지 먼저 결정해야 한다.
- 질문이 너무 추상적으로 나오지 않게 "실제 경험 기반 답변 가능" 조건을 프롬프트에 강하게 줘야 한다.
- 질문이 중복되지 않도록 distinct 조건을 넣는 것이 좋다.
- 면접관스러운 톤과 꼬리질문 확장성을 함께 요구하는 것이 좋다.

### 6-8. 확장 아이디어

- 질문 생성 시 `question_type`별로 다른 prompt를 쓰는 라우팅 구조
- `item_type`에 따라 다른 질문 생성 전략 적용
- 생성 질문마다 예상 follow-up도 함께 생성
- 중복 질문 제거용 post-processing chain 추가

## 7. Phase 4 상세 계획: 평가 및 개선 루프

### 7-1. Phase 4의 역할

Phase 4는 생성된 질문이 실제 면접관 관점에서 유효한지 검증하고, 부족하면 더 나은 질문으로 개선하는 단계다.

현재 `lib/phase4.py`는 이 역할을 아래 기준으로 수행하고 있다.

- 꼬리질문으로 이어질 수 있는가
- 질문이 구체적인가
- JD 요구 역량과 연결되는가
- 자기소개서 기반으로 답할 수 있는가
- 실제 면접관이 할 법한 질문인가

이 기준은 후속 LangChain 실습에서도 그대로 가져가는 것이 좋다.

### 7-2. 현재 코드에서 유지할 가치가 있는 부분

- 평가 프롬프트와 개선 프롬프트가 역할별로 분리돼 있다.
- `PASS / FAIL / UNKNOWN` 상태 추출 로직이 단순하다.
- 시도 이력을 남기는 구조가 학습과 디버깅에 유용하다.
- 질문 1개 단위 최적화와 질문 리스트 단위 최적화가 분리돼 있다.

즉, Phase 4는 완전 재설계보다 "LangChain 문법으로 치환"하는 접근이 적절하다.

### 7-3. LangChain으로 바꿀 때의 핵심

- `phase4()` -> evaluator chain
- `improve_question()` -> improver chain
- `optimize_question_with_retries()` -> Python 제어 흐름 + LangChain invoke 조합

여기서 중요한 점은 반복문 자체는 꼭 Runnable로만 만들 필요는 없다는 것이다.  
학습 초기에는 Python `for` 루프로 제어하고, 내부 평가/개선만 LangChain chain으로 만드는 방식이 가장 이해하기 쉽다.

### 7-4. 추천 출력 구조

현재 구조를 거의 유지하되, 평가 결과를 더 구조화하는 것이 좋다.

```json
{
  "original_question": "...",
  "initial_status": "FAIL",
  "attempts": [
    {
      "attempt": 1,
      "optimized_question": "...",
      "optimized_status": "PASS",
      "feedback_summary": "구체성이 보강됨"
    }
  ],
  "final_question": "...",
  "final_status": "PASS"
}
```

### 7-5. 노트북 실습 구성안

권장 섹션 제목:

- `Phase 4 평가-최적화 루프 실습`

세부 구성:

1. 질문 평가 기준 읽기
2. evaluator chain 만들기
3. improver chain 만들기
4. PASS/FAIL 상태 추출 함수 작성
5. 질문 1개에 대한 retry 루프 구현
6. 여러 질문으로 확장
7. PASS 질문만 필터링

### 7-6. TODO 후보

- 평가 결과용 구조화 모델 정의
- evaluator prompt 작성
- improver prompt 작성
- evaluator chain 구성
- improver chain 구성
- retry 루프 구현
- PASS 질문만 추출하는 함수 작성

### 7-7. 학습 포인트

- 체인과 Python 제어 흐름을 섞는 방법
- 구조화 출력 실패 시 fallback을 다루는 방법
- 프롬프트 품질이 반복 루프 결과에 미치는 영향
- 개선 이력을 기록하는 설계 감각

### 7-8. 확장 아이디어

- 단순 PASS/FAIL 대신 1~5 점수형 평가 추가
- 평가 항목별 세부 점수 구조화
- 질문이 일정 점수 이상일 때만 PASS 처리
- `with_fallbacks()` 또는 규칙 기반 fallback 도입
- 향후 LangGraph로 옮겨 상태 기반 루프로 확장

## 8. Phase 5 상세 계획: 질문 분류 및 랭킹

### 8-1. Phase 5의 역할

Phase 5는 PASS된 질문들을 최종 면접 준비 관점의 리포트로 바꾸는 단계다.

현재 `lib/phase5.py`에서는 아래 흐름으로 처리한다.

1. 질문 유형 분류
2. 카테고리별 점수 부여
3. 카테고리 내 내림차순 정렬
4. 카테고리별 순위 해설 생성
5. 최종 텍스트 포맷팅

### 8-2. LangChain 학습 포인트

- 원자적 태스크를 여러 개 이어붙이는 방법
- LLM 출력과 파이썬 후처리를 적절히 분리하는 방법
- classification, scoring, summarization 체인을 따로 만드는 방법
- 카테고리별 그룹핑 후 재처리하는 패턴

### 8-3. 유지하면 좋은 현재 설계

- 분류, 채점, 해설이 함수로 잘 분리되어 있음
- 최종 포맷팅이 별도 함수로 분리되어 있음
- category 단위로 독립 처리하기 쉬운 구조임

이 구조는 학습용 노트북에서도 그대로 유지하는 편이 좋다.

### 8-4. 추천 출력 구조

기존 구조를 유지하되, category 메타데이터를 조금 더 붙이는 것을 권장한다.

```json
{
  "AI/LLM/Agent 역량 검증": {
    "question_count": 3,
    "ranked_questions": [
      {
        "question": "...",
        "difficulty": 4,
        "frequency": 5,
        "relevance": 5,
        "total": 14,
        "reason": "..."
      }
    ],
    "ranking_reason": "..."
  }
}
```

### 8-5. 노트북 실습 구성안

권장 섹션 제목:

- `Phase 5 질문 분류 및 랭킹 실습`

세부 구성:

1. 분류 기준 읽기
2. classifier chain 만들기
3. scorer chain 만들기
4. category별 groupby 구현
5. category별 점수 정렬
6. ranking reason chain 만들기
7. 최종 텍스트 리포트 출력

### 8-6. TODO 후보

- 질문 분류 prompt 작성
- 점수화 결과 스키마 정의
- scorer chain 구성
- 카테고리별 groupby 함수 작성
- 정렬 로직 작성
- ranking reason 생성 chain 작성
- 최종 formatter 함수 작성

### 8-7. 구현 시 주의점

- category 이름이 미세하게 흔들리면 groupby가 깨질 수 있으므로 enum 또는 고정 문자열 검증이 필요하다.
- score JSON 파싱 실패에 대비한 fallback이 필요하다.
- 카테고리별 질문 수가 적을 때도 자연스럽게 동작해야 한다.

### 8-8. 확장 아이디어

- 카테고리별 최소 질문 수 보장
- 전체 질문 Top-N 랭킹도 추가
- 질문별 예상 답변 난이도나 준비 우선순위 추가
- 시각화 표 또는 markdown 리포트 자동 생성

## 9. 학습용 노트북 분리 전략

후속 범위는 한 노트북에 모두 넣을 수도 있지만, 아래처럼 분리하는 것이 학습에 더 좋다.

권장안:

- `practice_refactoring_agent_pipeline_part2.ipynb`

또는 세분화:

- `practice_phase3_question_generation.ipynb`
- `practice_phase4_question_optimization.ipynb`
- `practice_phase5_ranking_report.ipynb`

권장 기준은 아래와 같다.

- 한 노트북이 너무 길어지면 분리
- Phase 4 retry 루프를 설명하려면 독립 노트북이 더 편함
- 복습용으로는 Phase 3~5를 한 번에 보는 통합 노트북도 가치가 있음

## 10. 후속 단계의 TODO 설계 원칙

Phase 3~5에서도 아래 원칙을 유지한다.

- 질문 생성 prompt의 핵심 조건은 사용자가 직접 쓴다.
- evaluator / improver prompt는 골격만 주고 세부 문장은 직접 보강하게 한다.
- scoring schema는 일부 필드만 주고 나머지는 직접 채우게 한다.
- formatter는 완성본을 주기보다 중간 출력부터 직접 확인하게 한다.

즉, 후속 단계도 여전히 "풀이 제공"보다 "구현 경험 제공"이 우선이다.

## 11. 구현 우선순위

후속 단계는 아래 순서로 구현하는 것이 자연스럽다.

1. Phase 3 단일 문항 질문 생성 실습
2. Phase 3 여러 문항 확장
3. Phase 4 evaluator chain
4. Phase 4 improver chain
5. Phase 4 retry 루프
6. Phase 5 classifier chain
7. Phase 5 scorer chain
8. Phase 5 ranking reason chain
9. 최종 리포트 formatter

이 순서를 권장하는 이유는, 먼저 질문 리스트가 생겨야 평가와 랭킹이 가능하기 때문이다.

## 12. 완료 기준

이 문서 범위의 작업이 잘 끝났다고 볼 기준은 아래와 같다.

- Phase 3에서 문항별 질문 생성 chain이 동작한다.
- Phase 4에서 질문 1개에 대한 평가-개선 루프를 직접 구현해볼 수 있다.
- Phase 5에서 PASS 질문을 분류하고 점수화할 수 있다.
- category별 랭킹 해설과 최종 보고서 출력까지 이어진다.
- 각 단계에 설명, 힌트, `TODO`가 포함된다.
- 사용자가 직접 빈칸을 채우며 원본 프로젝트의 뒷단 로직을 LangChain으로 옮겨볼 수 있다.

## 13. 바로 다음 액션

이 문서를 기준으로 다음 작업은 아래 순서를 추천한다.

1. `NEXT_PLAN.md` 기준의 노트북 목차를 만든다.
2. Phase 3 질문 생성 실습 셀부터 작성한다.
3. Phase 4 evaluator / improver 실습 셀을 붙인다.
4. retry 루프 실습 셀을 작성한다.
5. Phase 5 분류/점수화/리포트 실습 셀을 작성한다.
6. 마지막으로 Phase 2 결과를 입력으로 넣어 end-to-end 연결 실습을 만든다.
