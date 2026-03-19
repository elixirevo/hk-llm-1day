# Phase 1 실행 계획

## 1. 목표

Phase 1의 현재 목표는 JD를 분석해서 하나의 통합 결과를 만드는 것이 아니다.

이번 목표는 각 병렬 워커의 결과를 동일한 공통 wrapper JSON 형태로 만들어서, Phase 2가 워커 결과별로 여러 번 실행될 수 있게 하는 것이다.

즉, Phase 1은 아래 역할에 집중한다.

- JD를 워커별로 안정적으로 분해
- 각 워커가 자기 책임에 맞는 JSON 생성
- 각 JSON을 동일한 wrapper 형태로 감싸기
- Phase 2가 `agent_id` 기준으로 개별 실행할 수 있게 넘기기

핵심은 `통합 분석`이 아니라 `개별 워커 결과 표준화`다.

## 2. Phase 1에서 Phase 2로 넘길 공통 JSON 구조

이번 단계에서 합의한 공통 구조는 아래와 같다.

```json
{
  "company_name": "",
  "job_title": "",
  "agent_id": "",
  "payload": {}
}
```

의미는 다음과 같다.

- `company_name`: JD 첫 줄 또는 기본 정보에서 추출한 회사명
- `job_title`: JD 기본 정보에서 추출한 직무명
- `agent_id`: 어떤 워커 결과인지 나타내는 식별자
- `payload`: 해당 워커가 생성한 원래 JSON 결과

이 구조를 사용하면 `payload` 내부는 워커별로 달라도 되고, Phase 2는 `agent_id`를 보고 적절한 후속 처리를 수행할 수 있다.

## 3. 현재 코드 기준 유지할 구조

현재 코드에서 유지할 주요 변수명과 함수명은 아래와 같다.

- `AgentTask`
- `ANCHORS`
- `AGENT_MAP`
- `build_tasks(jd_text)`
- `get_req_prompt(content)`
- `get_plus_prompt(content)`
- `get_role_prompt(content)`
- `get_biz_prompt(content)`
- `get_corp_prompt(content)`
- `PROMPT_FN_MAP`
- `get_worker_prompt(agent_id, content)`
- `build_prompt_details(tasks)`
- `run_llm_parallel(prompt_details, llm_async_fn)`
- `run_jd_workers(jd_text, llm_async_fn)`
- `llm_async_fn(prompt, model)`

문서와 구현은 이 이름을 그대로 기준으로 맞춘다.

## 4. Phase 1 처리 흐름

### 4-1. `build_tasks(jd_text)`

역할:

- JD 첫 줄 추출
- `ANCHORS` 기준 섹션 분리
- `AGENT_MAP` 기준 `role`, `req`, `plus` 태스크 생성
- `Career Vision`과 첫 줄을 조합해 `biz`, `corp` 태스크 생성

출력:

- `AgentTask` 리스트

### 4-2. `build_prompt_details(tasks)`

역할:

- `AgentTask` 리스트를 실제 LLM 호출 입력 형태로 변환
- 각 태스크에 `agent_id`, `user_prompt`, `model`을 붙임

출력:

- 워커 실행용 `prompt_details` 리스트

### 4-3. `run_llm_parallel(prompt_details, llm_async_fn)`

역할:

- 워커 프롬프트 병렬 실행
- 응답 리스트 반환

출력:

- 워커 응답 문자열 리스트

### 4-4. 워커 응답 파싱 및 wrapper 조립

역할:

- 각 워커 응답을 JSON으로 파싱
- 아래 wrapper 형태로 감싸기

```json
{
  "company_name": "",
  "job_title": "",
  "agent_id": "",
  "payload": {}
}
```

출력:

- Phase 2에 넘길 개별 결과 리스트

## 5. 워커별 책임

### 5-1. `role`

입력:

- `Role` 섹션

목표:

- 실제 업무 역할 구조화
- 역할별 필요 기술 연결
- 질문 유형 정리

wrapper 예시:

```json
{
  "company_name": "삼성전자 DS부문 AI센터",
  "job_title": "SW개발",
  "agent_id": "role",
  "payload": {
    "roles": [
      {
        "role_name": "LLM 기반 추론 구조 및 멀티 Agent 협업 시스템 개발",
        "required_skills": ["LLM", "멀티 Agent", "시스템 설계"],
        "question_type": "기술깊이"
      }
    ]
  }
}
```

### 5-2. `req`

입력:

- `Requirements` 섹션

목표:

- 필수 역량 키워드 추출
- 중요도와 근거 정리

주의:

- 입력에 없는 `Role` 기반 추론은 최소화
- 현재 단계에서는 `Requirements`에서 직접 읽히는 내용 위주로 정리

wrapper 예시:

```json
{
  "company_name": "삼성전자 DS부문 AI센터",
  "job_title": "SW개발",
  "agent_id": "req",
  "payload": {
    "requirements": [
      {
        "keyword": "Python",
        "type": "must",
        "weight": 0.9,
        "evidence": "소프트웨어 개발 역량"
      }
    ]
  }
}
```

### 5-3. `plus`

입력:

- `Pluses` 섹션

목표:

- 우대사항 키워드 추출
- 카테고리, appeal, 질문 힌트 정리

wrapper 예시:

```json
{
  "company_name": "삼성전자 DS부문 AI센터",
  "job_title": "SW개발",
  "agent_id": "plus",
  "payload": {
    "pluses": [
      {
        "keyword": "LLM/RAG/Agent 설계 경험",
        "category": "기술",
        "appeal": "high",
        "question_hint": "직접 설계한 구조와 성능 개선 경험"
      }
    ]
  }
}
```

### 5-4. `biz`

입력:

- 첫 줄 기업/직무 정보 + `Career Vision`

목표:

- 사업 방향 키워드
- 최근 이니셔티브
- 지원동기 문장 씨앗

wrapper 예시:

```json
{
  "company_name": "삼성전자 DS부문 AI센터",
  "job_title": "SW개발",
  "agent_id": "biz",
  "payload": {
    "biz_direction": {
      "strategy_keywords": ["Autonomous Fab", "반도체 생산 지능화"],
      "recent_initiatives": [],
      "why_company_seeds": ["실시간 AI 서빙 안정성 기여"]
    }
  }
}
```

### 5-5. `corp`

입력:

- 첫 줄 기업/직무 정보 + `Career Vision`

목표:

- 기업 현황
- 문화 키워드
- 차별점 정리

wrapper 예시:

```json
{
  "company_name": "삼성전자 DS부문 AI센터",
  "job_title": "SW개발",
  "agent_id": "corp",
  "payload": {
    "company_info": {
      "recent_news": [],
      "culture_keywords": ["문제 해결", "협업", "실행력"],
      "differentiators": ["반도체 도메인과 AI 시스템의 결합"]
    }
  }
}
```

## 6. 지금 코드에 반영해야 할 수정 사항

### 6-1. `run_llm_parallel()`에서 모델 인자 전달

현재 문제:

- `llm_async_fn(item["user_prompt"])`로 호출하고 있음
- 실제 시그니처는 `llm_async_fn(prompt, model)`

수정 방향:

- `llm_async_fn(item["user_prompt"], item["model"])`로 변경

### 6-2. `build_prompt_details()` 모델 분기

현재 문제:

- 모든 워커가 `"gpt-4o"`로 고정됨

수정 방향:

- `role`, `req`, `plus`는 `"gpt-4o"`
- `biz`, `corp`는 `"gpt-4.1"` 또는 검색 가능한 모델

### 6-3. `build_tasks()` 안전화

현재 문제:

- `sections[anchor]` 접근 시 `KeyError` 가능

수정 방향:

- `sections.get(anchor, "")` 사용
- 누락 섹션에 대한 fallback 처리 추가

### 6-4. `import json` 추가

현재 문제:

- 드라이런 하단에서 `json.loads`, `json.dumps`를 사용하지만 import가 없음

수정 방향:

- 상단 import에 `json` 추가

### 6-5. 공통 JSON 정리 함수 추가

현재 문제:

- 워커 응답이 코드블록 또는 부가 텍스트와 섞이면 파싱이 흔들릴 수 있음

수정 방향:

- `clean_json_response()` 추가
- fenced code block 제거
- 파싱 실패 시 `agent_id`와 함께 로그 출력

### 6-6. wrapper 조립 단계 추가

현재 문제:

- 워커 응답을 받은 뒤 Phase 2용 공통 wrapper로 감싸는 단계가 없음

수정 방향:

- `company_name`, `job_title`, `agent_id`, `payload` 구조로 조립
- `run_jd_workers()` 또는 별도 함수에서 최종 리스트 반환

## 7. 구현 우선순위

현재 목표 기준 우선순위는 아래와 같다.

1. `import json` 추가
2. `run_llm_parallel()` 수정
3. `build_prompt_details()` 모델 분기 수정
4. `build_tasks()` 안전화
5. `clean_json_response()` 추가
6. 워커 응답 JSON 파싱 안정화
7. 공통 wrapper 조립 단계 추가
8. Phase 2 입력 리스트 형태로 반환

## 8. 테스트 계획

### 8-1. 태스크 생성 테스트

대상:

- `build_tasks(JD_TEXT)`

확인 항목:

- `role`, `req`, `plus`, `biz`, `corp` 5개 태스크가 생성되는지
- 각 태스크의 `content`가 비어 있지 않은지

### 8-2. 프롬프트 조립 테스트

대상:

- `build_prompt_details(tasks)`

확인 항목:

- `agent_id`, `user_prompt`, `model`이 모두 들어가는지
- `biz`, `corp`에 검색용 모델이 들어가는지

### 8-3. 병렬 실행 테스트

대상:

- `run_llm_parallel(prompt_details, llm_async_fn)`

확인 항목:

- 응답 개수가 태스크 수와 같은지
- 순서가 유지되는지

### 8-4. JSON 파싱 테스트

대상:

- 워커 응답 파싱 단계

확인 항목:

- 모든 워커 응답이 `json.loads()` 가능한지
- 실패 시 어느 `agent_id`가 문제인지 바로 확인 가능한지

### 8-5. wrapper 조립 테스트

대상:

- 파싱 완료된 워커 결과

확인 항목:

- 모든 결과가 아래 구조를 가지는지

```json
{
  "company_name": "",
  "job_title": "",
  "agent_id": "",
  "payload": {}
}
```

- `payload` 내부는 워커별 shape를 유지하는지

## 9. 리스크와 대응

### 리스크 1. 앵커 기반 파싱 실패

문제:

- 실제 JD의 섹션명이 정확히 `Role`, `Requirements`, `Pluses`가 아닐 수 있음

대응:

- 앵커 확장
- 유사어 대응
- fallback 처리

### 리스크 2. 워커 프롬프트와 입력 범위 불일치

문제:

- 입력에 없는 정보를 억지로 추론하게 하면 JSON 품질이 흔들림

대응:

- 프롬프트 책임과 입력 범위를 맞춤
- 교차 추론은 현재 단계에서 최소화

### 리스크 3. JSON 파싱 실패

문제:

- 코드블록, 설명 문장, 포맷 흔들림으로 파싱 실패 가능

대응:

- 공통 정리 함수 추가
- 실패 워커만 재시도 가능하게 설계

### 리스크 4. 너무 이른 통합 시도

문제:

- 지금 단계에서 결과를 억지로 합치면 Phase 2 병렬 실행 구조와 충돌할 수 있음

대응:

- 통합보다 wrapper 표준화에 집중
- 각 워커 결과는 독립된 입력으로 유지

## 10. 완료 기준

이번 목표 기준 Phase 1 1차 완료 조건은 아래와 같다.

- `build_tasks()`가 안정적으로 워커 태스크를 만든다
- `build_prompt_details()`가 워커별 모델을 올바르게 세팅한다
- `run_llm_parallel()`이 모델 인자를 포함해 병렬 실행된다
- 각 워커 응답이 JSON으로 파싱된다
- 모든 워커 결과가 아래 구조로 감싸진다

```json
{
  "company_name": "",
  "job_title": "",
  "agent_id": "",
  "payload": {}
}
```

- Phase 2가 이 결과를 워커별로 독립 실행 가능한 입력으로 사용할 수 있다

## 11. 바로 다음 할 일

지금 바로 하면 좋은 순서는 아래와 같다.

1. `import json` 추가
2. `run_llm_parallel()` 수정
3. `build_prompt_details()` 모델 분기 수정
4. `build_tasks()` 안전화
5. `clean_json_response()` 추가
6. wrapper 조립 함수 추가

이 단계가 끝나면, Phase 1은 "통합 분석기"가 아니라 "Phase 2에 넘길 표준 워커 결과 생성기"로서 역할을 수행할 수 있다.
