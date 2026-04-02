# LangChain 학습형 리팩토링 계획

## 1. 문서 목적

이 문서는 `hk-llm-1day/project.ipynb`에 있는 **AI 면접 질문 생성 에이전트** 프로젝트를 LangChain으로 다시 만들어보는 과정에서, "완성형 리팩토링"보다 "직접 구현하며 학습하는 실습형 리팩토링"을 목표로 한다.

이 문서의 기준 프로젝트는 아래 소개 문단과 동일한 대상을 가리킨다.

- JD(직무기술서)와 자기소개서를 함께 분석한다.
- JD 기반 요구 역량과 자소서 기반 경험 근거를 연결한다.
- 면접 질문을 생성하고, 평가-개선 루프를 거쳐 정제한다.
- 최종적으로 질문을 분류하고 우선순위화한다.

즉, 이 문서는 다른 예제 프로젝트를 위한 계획서가 아니다.  
오직 `hk-llm-1day/project.ipynb`의 아래 흐름을 LangChain 학습용으로 다시 구성하기 위한 계획서다.

- Phase 1: JD를 워커별로 병렬 분석해 Phase 2 입력용 JSON wrapper 생성
- Phase 2: 자소서 문항을 분리하고, JD 항목과 매칭하여 질문 생성용 컨텍스트 구성
- Phase 3: 면접 질문 생성
- Phase 4: 생성된 질문 평가 및 FAIL 시 개선
- Phase 5: PASS 질문 분류 및 점수화, 우선순위 리포트 생성

즉, 내가 전부 대신 구현하는 방향이 아니라 아래 방향을 따른다.

- 노트북 중심으로 실습한다.
- 핵심 로직은 `TODO`로 남겨 직접 작성한다.
- 설명은 충분히 주되, 정답 코드는 최소화한다.
- `langchain_practice` 폴더의 노트북처럼 단계별 학습 흐름을 만든다.
- 리팩토링 결과보다 LangChain 개념을 몸에 익히는 것을 우선한다.

여기서 `langchain_practice`는 **리팩토링 대상이 아니라 노트북 구성 방식만 참고하는 예시**다.  
내용의 기준은 항상 `AI 면접 질문 생성 에이전트` 프로젝트다.

## 2. 최종 산출물 방향

최종 결과물은 "프로덕션용 앱"보다 아래와 같은 "학습용 리팩토링 세트"를 목표로 한다.

- `refactoring` 폴더 아래 학습용 노트북 1개 이상
- 각 단계별 마크다운 설명
- 직접 채워 넣을 `TODO` 셀
- 최소한의 정답 또는 참고 코드
- 원본 OpenAI SDK 방식과 LangChain 방식의 대응 설명

권장 산출물 예시는 아래와 같다.

```text
hk-llm-1day/
  refactoring/
    PLAN.md
    practice_refactoring_agent_pipeline.ipynb
    refactoring.py
    data/
      jd_sample.md
      essay_sample.md
      phase1_sample.json
```

여기서 핵심은 `practice_refactoring_agent_pipeline.ipynb`가 메인 실습 공간이 되는 것이다.

## 3. 학습 목표

이번 리팩토링을 통해 익히려는 LangChain 포인트는 아래와 같다.

1. `ChatPromptTemplate`로 프롬프트를 구조화하는 방법
2. `ChatOpenAI`로 모델을 연결하는 방법
3. `PydanticOutputParser` 또는 `with_structured_output()`으로 구조화 출력을 받는 방법
4. `RunnableSequence`로 단계형 체인을 만드는 방법
5. `RunnableParallel`로 여러 분석 체인을 병렬 실행하는 방법
6. `RunnableLambda`로 후처리/병합 로직을 연결하는 방법
7. 기존 OpenAI SDK 코드와 LangChain 코드의 역할 차이를 이해하는 방법

## 4. 리팩토링 범위

원본 `project.ipynb` 전체를 한 번에 다 옮기기보다, 학습 효율이 높은 구간부터 나눈다.

### 이번 계획이 직접 다루는 원본 프로젝트 범위

원본 프로젝트의 핵심 흐름은 아래와 같다.

1. JD를 여러 워커(`role`, `req`, `plus`, `biz`, `corp`) 관점에서 병렬 분석한다.
2. 이 결과를 Phase 2에서 사용할 JSON wrapper 형태로 정리한다.
3. 자소서 문항을 분리하고, JD 항목과 매칭한다.
4. 질문 생성에 필요한 컨텍스트를 만든다.
5. 이후 질문 생성, 평가/개선, 분류/랭킹으로 이어진다.

이번 학습형 리팩토링은 이 흐름 전체를 머릿속에 두되, **학습 난이도와 효율을 고려해 앞단부터 잘라서 실습**한다.

### 우선 학습할 범위

- Phase 1: JD 다중 에이전트 분석
- Phase 2: 자소서 문항 분석 및 JD 매칭

### 나중에 확장할 범위

- Phase 3: 질문 생성
- Phase 4: 질문 평가 및 개선 루프
- Phase 5: 질문 분류 및 랭킹

이유는 Phase 1, 2만 잘 옮겨도 LangChain의 핵심 개념인 프롬프트, structured output, 병렬 실행을 거의 다 학습할 수 있기 때문이다.

또한 원본 프로젝트의 Phase 3~5는 결국 Phase 1~2가 만들어낸 구조화 데이터 위에서 동작하므로, 학습 순서상 앞단을 먼저 이해하는 것이 가장 효율적이다.

## 5. 원본 프로젝트 흐름과 LangChain 학습 포인트 매핑

아래는 원본 프로젝트의 각 Phase가 LangChain 학습에서 무엇으로 연결되는지 정리한 표다.

| 원본 Phase | 원래 역할 | LangChain에서 주로 연습할 것 | 이번 계획의 우선순위 |
| --- | --- | --- | --- |
| Phase 1 | JD를 워커별 병렬 분석 | `ChatPromptTemplate`, structured output, `RunnableParallel` | 높음 |
| Phase 2 | 자소서 문항 분석 및 JD 매칭 | Pydantic 모델, `with_structured_output()`, `batch()`/병렬 처리 | 높음 |
| Phase 3 | 질문 생성 | prompt chaining, 출력 포맷 통제 | 중간 |
| Phase 4 | 질문 평가 및 개선 루프 | 체인 재호출, retry 흐름, 조건 분기 | 중간 |
| Phase 5 | 질문 분류 및 랭킹 | 후처리 chain, score 구조화, 결과 병합 | 중간 |

이 매핑의 목적은 "원본 프로젝트를 잊고 다른 예제를 공부하는 것"이 아니라,  
**원본 프로젝트의 각 기능을 LangChain 개념과 연결해서 학습 포인트를 분해하는 것**이다.

## 6. 현재 코드에서 학습 포인트가 되는 부분

현재 코드에서 특히 LangChain 실습으로 바꾸기 좋은 부분은 아래와 같다.

### 5-1. Phase 1

관련 파일:

- `hk-llm-1day/lib/phase1.py`
- `hk-llm-1day/project.ipynb`

학습 포인트:

- 하나의 입력(JD)을 여러 관점의 chain으로 병렬 분석
- agent별 프롬프트 분리
- 결과를 JSON 구조로 통일

LangChain으로 바꿀 때 대응되는 개념:

- 프롬프트 함수 -> `ChatPromptTemplate`
- 비동기 병렬 호출 -> `RunnableParallel`
- JSON 문자열 파싱 -> `PydanticOutputParser` 또는 `with_structured_output()`

### 5-2. Phase 2

관련 파일:

- `hk-llm-1day/lib/phase2.py`

학습 포인트:

- 자소서 문항을 개별 단위로 나누는 전처리
- 문항별 structured output 생성
- 여러 문항을 병렬 또는 batch 방식으로 처리
- 후속 질문 생성을 위한 context 구성

LangChain으로 바꿀 때 대응되는 개념:

- 단일 분석 함수 -> Runnable chain
- ThreadPool 병렬 처리 -> `batch()` 또는 `RunnableParallel`
- `_structured_call()` -> `with_structured_output()`

## 7. 이번 계획의 핵심 설계 판단

이번 문서에서 일부러 이렇게 잡은 이유를 명확히 적어둔다.

### 판단 1. "전체 완성"보다 "실습 가치가 높은 앞단"을 먼저 다룬다

원본 프로젝트는 Phase 1~5까지 이어지는 완결형 파이프라인이지만, 학습 관점에서는 앞단이 가장 중요하다.

- Phase 1은 병렬 워커 구조를 배우기 좋다.
- Phase 2는 structured output과 데이터 매칭을 배우기 좋다.
- 이 두 단계를 익히면 뒤 단계는 같은 패턴의 응용이 많다.

### 판단 2. `biz`, `corp`는 처음부터 필수로 넣지 않는다

이 둘은 검색 기능까지 섞여 있어 처음 LangChain을 익히는 데는 복잡도가 높다.

- 첫 실습은 `role`, `req`, `plus` 중심으로 간다.
- `biz`, `corp`는 선택 과제나 확장 과제로 둔다.
- 이렇게 해야 사용자가 체인 구조 자체를 먼저 익힐 수 있다.

### 판단 3. 정답 코드보다 사고 과정을 남긴다

이번 계획의 목적은 결과물을 빠르게 얻는 것이 아니라, 사용자가 직접 아래 질문에 답해보는 데 있다.

- 왜 이 단계에 parser가 필요한가?
- 왜 여기서는 `RunnableParallel`이 맞는가?
- 왜 dict 후처리를 `RunnableLambda`로 분리하는가?

그래서 노트북은 풀이집보다 실습지에 가깝게 설계한다.

## 8. 구현 원칙

이번 작업은 아래 원칙으로 진행한다.

### 원칙 1. 핵심 셀은 일부러 비워둔다

실제로 손으로 쳐봐야 학습이 되므로, 아래 같은 부분은 `TODO`로 남긴다.

- prompt 정의
- output parser 정의
- chain 연결
- parallel 구성
- 결과 merge 함수

### 원칙 2. 힌트는 주되 정답은 바로 주지 않는다

예를 들면 아래처럼 구성한다.

```python
# TODO: role 분석용 ChatPromptTemplate을 구성하세요
# 힌트:
# - system 메시지에는 "JD Role 섹션을 분석하는 전문가"라는 역할을 줍니다.
# - human 메시지에는 {content} 변수를 사용합니다.
```

### 원칙 3. 한 노트북에서 개념을 단계적으로 쌓는다

한 번에 완성본을 만들기보다 아래 순서로 학습하게 한다.

1. 원본 코드 이해
2. 단일 프롬프트 체인 만들기
3. structured output 붙이기
4. 병렬 실행 붙이기
5. 후처리 붙이기

### 원칙 4. 비교 학습 구조를 넣는다

가능하면 각 단계에서 아래 비교를 같이 넣는다.

- 기존 OpenAI SDK 방식
- LangChain 방식
- 무엇이 더 편한지
- 어디서 추상화가 생기는지

## 9. 노트북 구성안

권장 노트북 제목:

- `practice_refactoring_agent_pipeline.ipynb`

권장 섹션 구성:

### 섹션 1. 환경 준비

내용:

- 필요한 import 정리
- 모델 초기화 예시
- 샘플 JD 텍스트 불러오기

`TODO` 예시:

```python
# TODO: ChatOpenAI 모델을 초기화하세요
# 힌트: temperature, model 이름을 명시해보세요
```

### 섹션 2. 단일 에이전트 체인 실습

내용:

- 먼저 `role` 하나만 LangChain으로 바꿔본다.
- prompt -> model -> parser 흐름을 가장 작게 실습한다.

`TODO` 예시:

```python
# TODO: RoleAnalysis Pydantic 모델을 정의하세요
# TODO: ChatPromptTemplate을 구성하세요
# TODO: prompt | model | parser 체인을 완성하세요
```

학습 목표:

- LangChain 기본 체인 문법 익히기
- structured output 익히기

### 섹션 3. Phase 1 다중 에이전트 확장

내용:

- `role`, `req`, `plus`를 각각 체인으로 만든다.
- 그 다음 `RunnableParallel`로 묶는다.
- `biz`, `corp`는 검색이 들어가므로 처음에는 제외하거나 선택 과제로 둔다.

`TODO` 예시:

```python
# TODO: req_chain, plus_chain을 구성하세요
# TODO: RunnableParallel로 role/req/plus를 동시에 실행하세요
# TODO: 결과를 보기 좋은 dict 형태로 정리하세요
```

학습 목표:

- 병렬 실행 개념 익히기
- 여러 체인의 출력 구조 이해하기

### 섹션 4. Phase 2 문항 분석 실습

내용:

- 자소서 문항 분리
- 문항 1개 분석 chain 작성
- 여러 문항 반복 적용

`TODO` 예시:

```python
# TODO: 자기소개서 문항 1개를 분석하는 Pydantic 모델을 정의하세요
# TODO: analyzed_item을 만드는 chain을 작성하세요
# TODO: 여러 문항에 대해 batch 또는 반복 실행을 해보세요
```

학습 목표:

- structured output이 많은 필드를 가질 때의 사용법 익히기
- 문항 단위 처리와 전체 리스트 처리의 차이 이해하기

### 섹션 5. Context 생성 실습

내용:

- 분석 결과를 바탕으로 후속 질문용 context를 만든다.
- 이 단계는 chain 하나를 더 연결하는 연습으로 쓸 수 있다.

`TODO` 예시:

```python
# TODO: question_context 생성을 위한 prompt를 작성하세요
# TODO: analysis 결과를 입력받아 context를 반환하는 chain을 구성하세요
```

학습 목표:

- 이전 chain의 출력을 다음 chain의 입력으로 연결하는 감각 익히기

### 섹션 6. 선택 과제

선택 과제로 아래를 둔다.

- `biz`, `corp` 에이전트도 LangChain 스타일로 옮겨보기
- `with_structured_output()`과 `PydanticOutputParser` 비교하기
- `RunnableParallel` 대신 `batch()` 사용해보기
- 질문 생성 단계까지 직접 확장해보기

### 섹션 7. 원본 코드와 비교 회고

내용:

- OpenAI SDK 직접 호출 방식과 LangChain 방식 차이 정리
- 어떤 부분이 더 읽기 쉬운지 비교
- 어떤 추상화가 도움이 됐고, 어떤 추상화는 아직 과한지 기록

`TODO` 예시:

```python
# TODO: 아래 질문에 답해보세요
# 1. 원본 phase1.py와 비교했을 때 LangChain 버전의 장점은?
# 2. 반대로 원본 코드가 더 직접적이라 이해가 쉬운 부분은?
# 3. 다음으로 직접 리팩토링하고 싶은 단계는?
```

## 10. TODO 설계 원칙

노트북 안의 `TODO`는 난이도를 나눠서 배치한다.

### Level 1. 따라 치기

예시:

- import 완성
- Pydantic 필드 채우기
- 간단한 prompt 작성

### Level 2. 개념 연결

예시:

- prompt, model, parser를 하나의 chain으로 연결
- `RunnableParallel` 구성
- 결과를 후처리 함수로 병합

### Level 3. 스스로 확장

예시:

- 새 agent 추가
- parser 교체
- batch 처리 방식 바꾸기

이렇게 해야 너무 쉬운 복붙도 아니고, 너무 어려운 백지 상태도 아니게 된다.

## 11. 사용자가 직접 구현해야 하는 핵심 TODO 후보

아래 항목들은 이번 학습형 리팩토링에서 특히 직접 손으로 구현하는 것을 권장한다.

- `role` 분석용 Pydantic 모델 정의
- `req` 분석용 prompt 작성
- `plus` 분석용 parser 또는 structured output 구성
- `role`, `req`, `plus` 체인을 `RunnableParallel`로 묶기
- Phase 1 결과를 보기 좋은 dict로 merge 하기
- 자소서 문항 1개 분석 chain 작성
- 여러 문항에 `batch()` 또는 반복 invoke 적용하기
- question context 생성 chain 작성

반대로 아래 항목은 처음부터 완성해두기보다 선택 과제로 남기는 것이 좋다.

- 검색이 들어가는 `biz`, `corp` 완전 이식
- Phase 4 평가-최적화 루프 전체 구현
- Phase 5 점수화 리포트 완성

## 12. 구현 순서 제안

실제로 작업할 때는 아래 순서를 추천한다.

1. `PLAN.md`를 기준으로 노트북 목차를 먼저 만든다.
2. 섹션 0~2까지의 마크다운과 기본 코드 셀을 만든다.
3. `role` 단일 체인 실습부터 완성한다.
4. `role -> req -> plus` 병렬 분석 실습으로 확장한다.
5. Phase 2의 단일 문항 분석 실습을 만든다.
6. 마지막으로 선택 과제와 회고 섹션을 붙인다.

핵심은 "전체 구현"보다 "학습 흐름이 끊기지 않는 노트북"을 먼저 만드는 것이다.

## 13. 이번 계획에서 일부러 하지 않을 것

이번 학습형 리팩토링에서는 아래를 우선순위에서 제외한다.

- 처음부터 전체 앱 구조를 완성하는 것
- 테스트 코드까지 모두 만드는 것
- LangGraph까지 바로 도입하는 것
- `biz/corp` 검색 경로를 완벽히 일반화하는 것
- 기존 코드와 완전히 동일한 결과를 보장하는 것

이유는 지금 목적이 "실무 완성도"보다 "LangChain 개념 체득"이기 때문이다.

## 14. 문서 해석 가이드

이 문서를 읽을 때 아래처럼 이해하면 된다.

- 리팩토링 대상: `AI 면접 질문 생성 에이전트`
- 구현 방식: LangChain 학습용 노트북
- 참고한 것: `langchain_practice`의 노트북 구성 스타일
- 우선 구현 대상: 원본 프로젝트의 Phase 1, Phase 2
- 구현 철학: 핵심 로직은 `TODO`로 남기고 직접 작성

즉, "다른 프로젝트를 참고해서 엉뚱한 계획을 쓴 문서"가 아니라,  
"현재 프로젝트를 학습형으로 다시 풀어낸 리팩토링 계획서"라고 보면 된다.

## 15. 완료 기준

이번 계획이 잘 수행됐다고 볼 기준은 아래와 같다.

- 노트북이 `langchain_practice`처럼 학습 흐름을 가진다.
- 섹션별 설명, 힌트, `TODO`가 있다.
- 최소한 `role` 분석 chain은 사용자가 직접 구현해볼 수 있다.
- `RunnableParallel`을 활용한 Phase 1 축소판 실습이 있다.
- Phase 2에서 structured output 실습이 있다.
- 사용자가 빈칸을 채우며 LangChain 개념을 익힐 수 있다.

## 16. 바로 다음 액션

다음 작업은 아래 순서를 추천한다.

1. `practice_refactoring_agent_pipeline.ipynb` 초안 생성
2. 섹션 0~3까지 마크다운/코드/TODO 셀 작성
3. `role` 단일 체인 실습 셀 작성
4. `RunnableParallel` 실습 셀 작성
5. Phase 2 단일 문항 분석 실습 셀 작성

이 문서 기준으로 이후 작업도 "내가 대신 완성"이 아니라 "직접 구현할 수 있도록 실습 구조를 설계"하는 방향으로 진행한다.
