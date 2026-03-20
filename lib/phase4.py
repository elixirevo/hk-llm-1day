from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_utils import llm_call


# 면접 질문이 적절한지 PASS / FAIL로 평가하는 프롬프트
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


# FAIL 판정을 받은 질문을 더 좋은 질문으로 다시 작성하게 하는 프롬프트
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


# 질문 1개를 평가해서 LLM 응답 문자열을 반환한다.
def phase4(question: str, job_category: str) -> str:
    prompt = EVALUATOR_PROMPT.format(
        job_category=job_category,
        question=question,
    )
    return llm_call(prompt)


# FAIL 평가 결과를 바탕으로 질문을 더 나은 형태로 다시 생성한다.
def improve_question(question: str, evaluation: str, job_category: str) -> str:
    prompt = IMPROVER_PROMPT.format(
        job_category=job_category,
        question=question,
        evaluation=evaluation,
    )
    result = llm_call(prompt).strip()

    # "개선 질문: ..." 형식으로 왔으면 질문 본문만 추출한다.
    if result.startswith("개선 질문:"):
        return result.replace("개선 질문:", "", 1).strip()

    return result


# 평가 결과 문자열에서 PASS / FAIL / UNKNOWN 상태만 추출한다.
def get_status(evaluation: str) -> str:
    if "평가 결과: PASS" in evaluation:
        return "PASS"
    if "평가 결과: FAIL" in evaluation:
        return "FAIL"
    return "UNKNOWN"


# 질문 1개에 대해
# 1. 최초 평가
# 2. FAIL이면 질문 개선
# 3. 개선 질문 재평가
# 를 최대 max_retries번 반복한다
def optimize_question_with_retries(
    question: str,
    job_category: str,
    max_retries: int = 3,
) -> dict:
    # 원본 질문 최초 평가
    initial_evaluation = phase4(question, job_category)
    initial_status = get_status(initial_evaluation)

    # 질문별 처리 이력을 담을 결과 객체
    item = {
        "original_question": question,
        "initial_status": initial_status,
        "initial_evaluation": initial_evaluation,
        "attempts": [],
        "final_question": question,
        "final_status": initial_status,
        "final_evaluation": initial_evaluation,
    }

    # 처음부터 PASS면 개선 없이 종료
    if initial_status == "PASS":
        return item

    # 개선 반복에 사용할 현재 질문/평가 상태
    current_question = question
    current_evaluation = initial_evaluation
    current_status = initial_status

    # FAIL이면 최대 max_retries번까지 개선/재평가를 반복
    for attempt in range(1, max_retries + 1):
        optimized_question = improve_question(
            current_question,
            current_evaluation,
            job_category,
        )

        # 개선된 질문을 다시 평가
        optimized_evaluation = phase4(optimized_question, job_category)
        optimized_status = get_status(optimized_evaluation)

        # 각 시도의 입력/출력/평가 결과를 기록
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

        # 다음 반복을 위해 현재 상태 갱신
        current_question = optimized_question
        current_evaluation = optimized_evaluation
        current_status = optimized_status

        # 마지막으로 생성된 질문과 평가 상태를 최종값으로 저장
        item["final_question"] = current_question
        item["final_status"] = current_status
        item["final_evaluation"] = current_evaluation

        # 중간에 PASS가 나오면 반복 종료
        if current_status == "PASS":
            break

    return item

# 질문 리스트 전체에 대해 optimize_question_with_retries를 적용한다.
def optimize_questions_with_retries(
    questions: list[str],
    job_category: str,
    max_retries: int = 3,
) -> list[dict]:
    return [
        optimize_question_with_retries(question, job_category, max_retries)
        for question in questions
    ]


# 최종 결과 중 PASS 판정을 받은 질문만 추출한다.
def get_passed_final_questions(results: list[dict]) -> list[str]:
    return [
        item["final_question"]
        for item in results
        if item["final_status"] == "PASS"
    ]


# 파일을 직접 실행했을 때 동작하는 샘플 코드
if __name__ == "__main__":
    sample_questions = [
        "AI 데이터 파이프라인 구축 경험에서 본인이 직접 설계하거나 구현한 핵심 컴포넌트와 그 기여도를 수치나 명확한 근거로 상세히 설명해보세요.",
        "실시간 서빙 아키텍처를 최적화할 때 선택한 기술 스택(Caching, Message Queue, Stream Processing 등)의 도입 결정 기준과 각각이 성능 병목을 어떻게 해소하는지 내부 메커니즘까지 구체적으로 말해보세요.",
        "파이프라인 운영 도중 예기치 못한 데이터 스키마 변동이나 대용량 트래픽 처리 실패와 같은 위기 상황을 실제로 겪었을 때, 트레이드오프를 어떻게 판단하고 시스템 신뢰성을 지키기 위해 어떤 조처를 했습니까?",
        "최신 AI Agent 서비스 플랫폼 트렌드를 고려할 때, 삼성전자 DS부문의 제조/반도체 특화 환경에 실시간 서빙 파이프라인을 어떤 방식으로 적용·확장하여 경쟁사 대비 차별화할 수 있다고 생각합니까?",
    ]

    # 전체 질문 평가 + 개선 반복 결과
    results = optimize_questions_with_retries(
        sample_questions,
        "백엔드개발자",
        max_retries=3,
    )
    print("=== 상세 결과 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # 모든 질문의 최종 버전
    final_questions = [item["final_question"] for item in results]
    print("=== 최종 질문 전체 ===")
    print(json.dumps(final_questions, ensure_ascii=False, indent=2))


    # 최종적으로 PASS된 질문만 추출
    passed_final_questions = get_passed_final_questions(results)
    print("=== 최종 PASS 질문만 ===")
    print(json.dumps(passed_final_questions, ensure_ascii=False, indent=2))
