import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils.utils import llm_call

# 1. 자기소개서 각 항목 분류하는 함수

def classify_personal_statement_sections(personal_statement_text: str) -> dict:
    JSON_STRUCTURE = {
        "question": "질문 내용",
        "answer": "답변 내용"
    }

    system_prompt = f"""
    [원문] = {personal_statement_text}

    [지시사항]
    위 [원문]을 항목별로 분류 해.

    [출력 형식]
    {JSON_STRUCTURE}
    """

    response = llm_call(system_prompt)
    return response

# 2. 자기소개서 문항별 질문 의도 (실제 평가 포인트)를 파악하는 함수

# 3. 각 JD와 자기소개서 항목을 비교해서 매칭하는 함수 (질문, 답안과 함께 매칭)
# 왜 매칭했는지 이유가 들어가 있으면 좋을듯.

# 4. 매칭된 JD로 자기소개서 본문 세분화 혹은 요약

# 5. 본문 구조화 (STAR, PREP, PAR 등등) 함수

# 6. JSON Parsing 함수

