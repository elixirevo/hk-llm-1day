from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_utils import llm_call


EVALUATOR_PROMPT = """
당신은 {job_category} 직무 면접관(실무자, 팀장, HR)입니다.

다음 면접 질문을 평가해줘.

[질문]
{question}

평가 기준:
1. 꼬리질문으로 이어질 수 있는가
2. 질문이 구체적인가
3. JD에서 요구하는 역량과 연결되는가
4. 자기소개서 기반으로 답할 수 있는가
5. 실제 면접관이 할 법한 질문인가

판정 기준:
- 모든 평가 기준이 충족되면 PASS
- 하나라도 부족하면 FAIL

응답 양식:
평가 결과: PASS 또는 FAIL
문제점 및 개선 방향:
- PASS면 "없음"
- FAIL이면 부족한 점과 어떻게 고치면 좋을지 구체적으로 작성
"""


IMPROVER_PROMPT = """
당신은 {job_category} 직무 면접관(실무자, 팀장, HR)입니다.

아래 면접 질문은 평가 결과 FAIL입니다.
문제점을 반영해서 PASS 받을 가능성이 높은 질문 1개로 다시 작성해줘.

[원본 질문]
{question}

[직전 평가 결과]
{evaluation}

개선 조건:
1. 꼬리질문으로 이어질 수 있어야 한다
2. 질문이 구체적이어야 한다
3. JD에서 요구하는 역량과 연결되어야 한다
4. 자기소개서/실제 경험 기반으로 답할 수 있어야 한다
5. 실제 면접관이 할 법한 질문이어야 한다

응답 형식:
개선 질문: 한 줄로만 작성
"""


def phase4(question: str, job_category: str) -> str:
    prompt = EVALUATOR_PROMPT.format(
        job_category=job_category,
        question=question,
    )
    return llm_call(prompt)


def improve_question(question: str, evaluation: str, job_category: str) -> str:
    prompt = IMPROVER_PROMPT.format(
        job_category=job_category,
        question=question,
        evaluation=evaluation,
    )
    result = llm_call(prompt).strip()

    if result.startswith("개선 질문:"):
        return result.replace("개선 질문:", "", 1).strip()

    return result


def get_status(evaluation: str) -> str:
    if "평가 결과: PASS" in evaluation:
        return "PASS"
    if "평가 결과: FAIL" in evaluation:
        return "FAIL"
    return "UNKNOWN"


def optimize_question_with_retries(
    question: str,
    job_category: str,
    max_retries: int = 3,
) -> dict:
    initial_evaluation = phase4(question, job_category)
    initial_status = get_status(initial_evaluation)

    item = {
        "original_question": question,
        "initial_status": initial_status,
        "initial_evaluation": initial_evaluation,
        "attempts": [],
        "final_question": question,
        "final_status": initial_status,
        "final_evaluation": initial_evaluation,
    }

    if initial_status == "PASS":
        return item

    current_question = question
    current_evaluation = initial_evaluation
    current_status = initial_status

    for attempt in range(1, max_retries + 1):
        optimized_question = improve_question(
            current_question,
            current_evaluation,
            job_category,
        )
        optimized_evaluation = phase4(optimized_question, job_category)
        optimized_status = get_status(optimized_evaluation)

        item["attempts"].append(
            {
                "attempt": attempt,
                "input_question": current_question,
                "input_evaluation": current_evaluation,
                "optimized_question": optimized_question,
                "optimized_status": optimized_status,
                "optimized_evaluation": optimized_evaluation,
            }
        )

        current_question = optimized_question
        current_evaluation = optimized_evaluation
        current_status = optimized_status

        item["final_question"] = current_question
        item["final_status"] = current_status
        item["final_evaluation"] = current_evaluation

        if current_status == "PASS":
            break

    return item


def optimize_questions_with_retries(
    questions: list[str],
    job_category: str,
    max_retries: int = 3,
) -> list[dict]:
    return [
        optimize_question_with_retries(question, job_category, max_retries)
        for question in questions
    ]


def get_passed_final_questions(results: list[dict]) -> list[str]:
    return [
        item["final_question"]
        for item in results
        if item["final_status"] == "PASS"
    ]


if __name__ == "__main__":
    sample_questions = [
        "AI 데이터 파이프라인 구축 경험에서 본인이 직접 설계하거나 구현한 핵심 컴포넌트와 그 기여도를 수치나 명확한 근거로 상세히 설명해보세요.",
        "실시간 서빙 아키텍처를 최적화할 때 선택한 기술 스택(Caching, Message Queue, Stream Processing 등)의 도입 결정 기준과 각각이 성능 병목을 어떻게 해소하는지 내부 메커니즘까지 구체적으로 말해보세요.",
        "파이프라인 운영 도중 예기치 못한 데이터 스키마 변동이나 대용량 트래픽 처리 실패와 같은 위기 상황을 실제로 겪었을 때, 트레이드오프를 어떻게 판단하고 시스템 신뢰성을 지키기 위해 어떤 조처를 했습니까?",
        "최신 AI Agent 서비스 플랫폼 트렌드를 고려할 때, 삼성전자 DS부문의 제조/반도체 특화 환경에 실시간 서빙 파이프라인을 어떤 방식으로 적용·확장하여 경쟁사 대비 차별화할 수 있다고 생각합니까?",
    ]

    results = optimize_questions_with_retries(
        sample_questions,
        "백엔드개발자",
        max_retries=3,
    )
    print("=== 상세 결과 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    final_questions = [item["final_question"] for item in results]
    print("=== 최종 질문 전체 ===")
    print(json.dumps(final_questions, ensure_ascii=False, indent=2))

    passed_final_questions = get_passed_final_questions(results)
    print("=== 최종 PASS 질문만 ===")
    print(json.dumps(passed_final_questions, ensure_ascii=False, indent=2))
