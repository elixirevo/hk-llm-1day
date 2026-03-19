def generate_answer(question: str, job_category: str, feedback_history: str = None) -> str:
    """
    면접 질문에 대한 모범 답안을 생성합니다.

    Args:
        question: 면접 질문
        job_category: 직무 카테고리 (백엔드/프론트엔드/데이터)
        feedback_history: 이전 평가 피드백 기록 (선택)
    Returns:
        모범 답안 문자열
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