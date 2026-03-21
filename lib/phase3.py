from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from openai import OpenAI

from lib.tools import _dedupe_keep_order, _structured_call


SUBTASK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "경험검증",
                            "기술깊이",
                            "직무적합성",
                            "기업 핏 문화정합",
                            "꼬리,인성",
                        ],
                    },
                    "priority": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["category", "priority", "reason"],
            }
        }
    },
    "required": ["subtasks"],
}


QUESTION_WORKER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 4,
            "maxItems": 4,
        }
    },
    "required": ["questions"],
}


def _build_orchestrator_payload(phase2_result: Dict[str, Any]) -> Dict[str, Any]:
    target = phase2_result.get("target", {})
    global_context = phase2_result.get("global_context", {})

    return {
        "target": target,
        "global_context": global_context,
        "items": phase2_result.get("items", []),
    }


def _generate_subtasks(
    client: OpenAI,
    phase2_result: Dict[str, Any],
    *,
    model: str,
) -> List[Dict[str, Any]]:
    target = phase2_result.get("target", {})
    company = target.get("company", "해당 기업")
    role = target.get("role", "지원 직무")

    system_prompt = f"""
너는 {company} {role} 채용 전략가이자 면접 설계자다.
전달받은 자소서 분석 데이터를 바탕으로 이번 면접에서 검증이 가장 시급한 5개 카테고리를 우선순위화하라.

카테고리 후보:
- 경험검증
- 기술깊이
- 직무적합성
- 기업 핏 문화정합
- 꼬리,인성

규칙:
- 5개 카테고리를 모두 한 번씩만 사용한다.
- priority는 1~5 정수다.
- reason은 이 카테고리에서 왜 지금 검증해야 하는지 한 문장으로 쓴다.
- global_context의 missing_jd_ids, global_risks, priority_question_topics를 적극 활용한다.
- JSON만 반환한다.
""".strip()

    response = _structured_call(
        client,
        model=model,
        schema_name="phase3_orchestrator_subtasks",
        schema=SUBTASK_SCHEMA,
        system_prompt=system_prompt,
        user_payload=_build_orchestrator_payload(phase2_result),
    )

    return sorted(response["subtasks"], key=lambda item: item["priority"])


def _generate_questions_for_subtask(
    client: OpenAI,
    phase2_result: Dict[str, Any],
    subtask: Dict[str, Any],
    *,
    model: str,
) -> Dict[str, Any]:
    target = phase2_result.get("target", {})
    company = target.get("company", "해당 기업")
    role = target.get("role", "지원 직무")
    category = subtask.get("category", "공통 역량")
    reason = subtask.get("reason", "전반적인 실무 역량 검증")

    system_prompt = f"""
너는 {company} {role} 면접의 기술 압박 면접관이다.

검증 전략:
- 집중 검증 카테고리: {category}
- 검증 의도 및 이유: {reason}

수행 지침:
1. phase2_result의 items 중 검증 의도와 가장 맞는 소재를 고른다.
2. 그 소재를 바탕으로 심층 질문 4개를 만든다.
3. 질문 구성은 아래 흐름을 따른다.
   - 질문 1: 경험의 사실 관계와 본인 기여도 확인
   - 질문 2: 사용한 기술/방법론의 선택 근거와 작동 원리
   - 질문 3: 실패/변수/트레이드오프 대응
   - 질문 4: 회사 비즈니스나 최신 기술 트렌드와 결합한 실무 적용
4. 질문은 자기소개서와 JD 맥락에서 답할 수 있어야 한다.
5. 같은 표현을 반복하지 말고 실제 면접관 문장처럼 쓴다.
6. JSON만 반환한다.
""".strip()

    payload = {
        "target": target,
        "subtask": subtask,
        "items": phase2_result.get("items", []),
        "global_context": phase2_result.get("global_context", {}),
    }

    response = _structured_call(
        client,
        model=model,
        schema_name="phase3_worker_questions",
        schema=QUESTION_WORKER_SCHEMA,
        system_prompt=system_prompt,
        user_payload=payload,
    )

    return {
        "category": category,
        "priority": subtask.get("priority", 99),
        "reason": reason,
        "questions": response["questions"],
    }


def generate_interview_questions(
    phase2_result: Dict[str, Any],
    *,
    client: Optional[OpenAI] = None,
    orchestrator_model: str = "gpt-4o",
    worker_model: str = "gpt-4o",
    max_workers: int = 5,
) -> Dict[str, Any]:
    """
    Phase 2 결과를 바탕으로 질문 생성용 서브태스크를 만들고, 카테고리별 심층 질문을 생성합니다.
    """
    client = client or OpenAI()
    subtasks = _generate_subtasks(client, phase2_result, model=orchestrator_model)

    worker_results: List[Optional[Dict[str, Any]]] = [None] * len(subtasks)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _generate_questions_for_subtask,
                client,
                phase2_result,
                subtask,
                model=worker_model,
            ): idx
            for idx, subtask in enumerate(subtasks)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            worker_results[idx] = future.result()

    all_questions: List[str] = []
    for worker_result in worker_results:
        all_questions.extend(worker_result["questions"])

    return {
        "target": phase2_result.get("target", {}),
        "subtasks": subtasks,
        "worker_results": worker_results,
        "questions": _dedupe_keep_order(all_questions),
    }

