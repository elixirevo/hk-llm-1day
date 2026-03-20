import os
import sys
from llm_utils.utils import llm_call

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def phase4(question: str, job_category: str) -> str:
    prompt = EVALUATOR_PROMPT.format(
        job_category=job_category,
        question=question,
    )
    return llm_call(prompt)


# questions = [
    'AI 데이터 파이프라인 구축 경험에서 본인이 직접 설계하거나 구현한 핵심 컴포넌트와 그 기여도를 수치나 명확한 근거로 상세히 설명해보세요.',
    '실시간 서빙 아키텍처를 최적화할 때 선택한 기술 스택(Caching, Message Queue, Stream Processing 등)의 도입 결정 기준과 각각이 성능 병목을 어떻게 해소하는지 내부 메커니즘까지 구체적으로 말해보세요.',
    '파이프라인 운영 도중 예기치 못한 데이터 스키마 변동이나 대용량 트래픽 처리 실패와 같은 위기 상황을 실제로 겪었을 때, 트레이드오프를 어떻게 판단하고 시스템 신뢰성을 지키기 위해 어떤 조처를 했습니까?',
    '최신 AI Agent 서비스 플랫폼 트렌드를 고려할 때, 삼성전자 DS부문의 제조/반도체 특화 환경에 실시간 서빙 파이프라인을 어떤 방식으로 적용·확장하여 경쟁사 대비 차별화할 수 있다고 생각합니까?',
# ]

def get_pass_questions(questions: list[str], job_category: str) -> list[str]:
    pass_questions = []

    for question in questions:
        result = phase4(question, job_category)
        print(f"[평가 중] {question}")
        print(result)
        print("-" * 80)

        if "평가 결과: PASS" in result:
            pass_questions.append(question)

    return pass_questions


# pass_questions = get_pass_questions(questions, "백엔드개발자")

# print("\nPASS 질문만 추린 결과:")
# for i, question in enumerate(pass_questions, 1):
#     print(f"{i}. {question}")
