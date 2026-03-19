EVALUATOR_PROMPT = """
당신은 {job_category} 직무 면접관(실무자, 팀장, HR)입니다,

다음 면접 질문을 평가하세요.

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
- 평가 결과: PASS / FAIL
- 문제점 및 개선 방향: (FAIL인 경우 구체적으로)

개선 방향:
- (구체적으로 작성)
"""


def phase4(question: str, job_category: str) -> str:
    """
    면접 질문의 품질을 평가합니다.

    Args:
        question: 면접 질문
        job_category: 직무 카테고리
    Returns:
        평가 결과 문자열 (PASS/FAIL 포함)
    """

    prompt = (
        f"{EVALUATOR_PROMPT.format}\n\n"
        f"<직무>\n{job_category}\n\n"
        f"<질문>\n{question}\n\n"
    )

    return llm_call(prompt)