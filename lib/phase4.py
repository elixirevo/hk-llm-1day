import re

from llm_utils import llm_call


EVALUATOR_PROMPT = """
당신은 {job_category} 직무 면접관(실무자, 팀장, HR)입니다.

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


QUESTION_RESULT_PATTERN = re.compile(
    r"""
    ^\s*(?:>\s*)?
    \d+\.\s*질문:\s*
    (?P<question>.*?)
    \s*평가\s*결과:\s*
    (?P<result>PASS|FAIL)
    \s*문제점\s*및\s*개선\s*방향:\s*
    (?P<feedback>.*?)
    (?=^\s*(?:>\s*)?\d+\.\s*질문:|\Z)
    """,
    re.DOTALL | re.MULTILINE | re.VERBOSE,
)


def phase4(question: str, job_category: str) -> str:
    """
    면접 질문의 품질을 평가합니다.

    Args:
        question: 면접 질문
        job_category: 직무 카테고리
    Returns:
        평가 결과 문자열 (PASS/FAIL 포함)
    """
    prompt = EVALUATOR_PROMPT.format(
        job_category=job_category,
        question=question,
    )
    return llm_call(prompt)


def filter_pass_questions(questions: list[str], job_category: str) -> list[str]:
    """
    질문 리스트를 평가한 뒤 PASS 판정을 받은 질문만 반환합니다.

    Args:
        questions: 평가할 질문 리스트
        job_category: 직무 카테고리
    Returns:
        PASS 판정을 받은 질문 리스트
    """
    pass_questions = []

    for question in questions:
        result = phase4(question, job_category)
        if "평가 결과: PASS" in result:
            pass_questions.append(question)

    return pass_questions


def extract_pass_questions(evaluation_text: str) -> list[str]:
    """
    phase4 결과 텍스트에서 PASS 판정을 받은 질문만 추출합니다.

    Args:
        evaluation_text: phase4가 반환한 전체 평가 문자열
    Returns:
        PASS 판정을 받은 질문 문자열 리스트
    """
    normalized_text = re.sub(r"^\s*>\s?", "", evaluation_text.strip(), flags=re.MULTILINE)
    pass_questions = []

    for match in QUESTION_RESULT_PATTERN.finditer(normalized_text):
        if match.group("result") == "PASS":
            pass_questions.append(match.group("question").strip())

    return pass_questions
