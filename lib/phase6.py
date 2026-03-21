from __future__ import annotations

from typing import Any, Dict, Optional

from llm_utils import llm_call


def generate_answer(question: str, job_category: str, feedback_history: Optional[str] = None) -> str:
    """
    질문 1개에 대한 모범 답안을 생성합니다.
    """
    if feedback_history:
        prompt = f"""
당신은 {job_category} 직무 면접 코치입니다.

기존 답변의 피드백을 반영하여 더 개선된 답변을 작성하세요.

[질문]
{question}

[이전 피드백]
{feedback_history}

요구사항:
- 부족한 부분 보완
- 더 구체적으로 개선
- STAR 구조(상황-과제-행동-결과) 유지
- 답변 분량이 1분 이내로 나오게 해줘
"""
    else:
        prompt = f"""
당신은 {job_category} 직무 면접 전문가입니다.

다음 질문에 대해 STAR 기법(상황-과제-행동-결과)으로 구조화된 모범 답변을 작성하세요.

[질문]
{question}

요구사항:
- 상황 - 과제 - 행동 - 결과 흐름
- 구체적인 행동 포함
- 실무 중심
- 답변 분량이 1분 이내로 나오게 해줘
"""

    return llm_call(prompt)


def phase6(question: str, job_category: str, feedback_history: Optional[str] = None) -> str:
    """
    기존 단일 질문 답변 생성 인터페이스를 유지합니다.
    """
    return generate_answer(question, job_category, feedback_history)


def generate_answers_from_phase5(
    phase5_result: Dict[str, Any],
    job_category: str,
    *,
    top_n_per_category: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Phase 5 결과를 받아 카테고리별 상위 질문의 모범 답변을 생성합니다.
    """
    final_output: Dict[str, Any] = {}

    for category, category_result in phase5_result.items():
        ranked_questions = category_result.get("ranked_questions", [])
        if top_n_per_category is not None:
            ranked_questions = ranked_questions[:top_n_per_category]

        answered_questions = []
        for idx, item in enumerate(ranked_questions, start=1):
            question = item.get("question", "").strip()
            if not question:
                continue

            answer = generate_answer(question, job_category)
            answered_questions.append({
                "rank": idx,
                "question": question,
                "difficulty": item.get("difficulty"),
                "frequency": item.get("frequency"),
                "relevance": item.get("relevance"),
                "total": item.get("total"),
                "reason": item.get("reason", ""),
                "sample_answer": answer,
            })

        final_output[category] = {
            "ranking_reason": category_result.get("ranking_reason", ""),
            "answers": answered_questions,
        }

    return final_output

