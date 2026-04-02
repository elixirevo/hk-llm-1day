import json
import re
from collections import defaultdict

from llm_utils.utils import llm_call


CATEGORY_LABELS = [
    "지원동기 / 직무 적합성",
    "프로젝트 경험 검증",
    "AI/LLM/Agent 역량 검증",
    "성능 최적화 / 시스템 설계",
    "인성 / 실행력 / 성장 가능성",
]


CATEGORY_CLASSIFIER_PROMPT = """
다음 면접 질문을 아래 5가지 유형 중 가장 적합한 하나로 분류하세요.

[유형]
- 지원동기 / 직무 적합성
- 프로젝트 경험 검증
- AI/LLM/Agent 역량 검증
- 성능 최적화 / 시스템 설계
- 인성 / 실행력 / 성장 가능성

[질문]
{question}

분류 결과는 반드시 위 [유형] 중 하나만 정확히 반환하세요.
다른 설명은 제외하세요.
"""


SCORER_PROMPT = """
당신은 {job_category} 직무 전문 면접관입니다.
아래 질문 목록에 대해 각각 난이도, 빈출도, 직무연관도를 평가하세요.(각 1~5점)
합계 점수(total)를 계산해주세요.

반환 형식:
```json
{{
  "scores": [
    {{
      "question": "질문 내용",
      "difficulty": 4,
      "frequency": 3,
      "relevance": 5,
      "total": 12,
      "reason": "점수 산정 근거 (간략히)"
    }}
  ]
}}
```

[질문 목록]
{questions}

JSON 외 출력 금지.
"""


RANKING_REASON_PROMPT = """
당신은 {job_category} 직무 면접관입니다.
다음은 [{category}] 유형의 질문들을 중요도(합계 점수) 순으로 정렬한 것입니다.

[순위별 질문]
{ranked_questions}

지원자가 이 유형의 질문들에 대비하기 위한 종합적인 핵심 포인트(순위 해설, 합격 팁 등)를 3~4문장으로 요약해주세요.
"""


def classify_question(question: str) -> str:
    prompt = CATEGORY_CLASSIFIER_PROMPT.format(question=question)
    result = llm_call(prompt).strip()
    return result if result in CATEGORY_LABELS else "기타"


def score_questions_by_category(questions: list[str], job_category: str) -> list[dict]:
    if not questions:
        return []

    questions_str = "\n".join(f"{idx + 1}. {question}" for idx, question in enumerate(questions))
    prompt = SCORER_PROMPT.format(job_category=job_category, questions=questions_str)
    raw = llm_call(prompt)

    cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(cleaned).get("scores", [])
    except json.JSONDecodeError:
        return []


def get_ranking_reason(category: str, ranked_questions: list[dict], job_category: str) -> str:
    if not ranked_questions:
        return ""

    ranked_str = "\n".join(
        f"{idx + 1}위. {item.get('question', '')} (합계:{item.get('total', 0)})"
        for idx, item in enumerate(ranked_questions)
    )
    prompt = RANKING_REASON_PROMPT.format(
        job_category=job_category,
        category=category,
        ranked_questions=ranked_str,
    )
    return llm_call(prompt).strip()


def phase5(passed_questions: list[str], job_category: str) -> dict:
    categorized = defaultdict(list)
    for question in passed_questions:
        category = classify_question(question)
        categorized[category].append(question)

    final_output = {}
    for category, questions in categorized.items():
        scored = score_questions_by_category(questions, job_category)
        ranked = sorted(scored, key=lambda item: item.get("total", 0), reverse=True)
        reason = get_ranking_reason(category, ranked, job_category)
        final_output[category] = {
            "ranked_questions": ranked,
            "ranking_reason": reason,
        }

    return final_output


def format_phase5_output(result: dict) -> str:
    if not result:
        return "표시할 예상 질문이 없습니다."

    lines = ["🏆 직무별 핵심 예상 질문 리포트\n"]
    sorted_categories = [category for category in CATEGORY_LABELS if category in result]
    sorted_categories += [category for category in result if category not in sorted_categories]

    for category in sorted_categories:
        data = result[category]
        lines.append(f"■ {category}")
        for idx, item in enumerate(data.get("ranked_questions", []), start=1):
            lines.append(f"  {idx}위. {item.get('question', '')}")

    return "\n".join(lines).strip()


if __name__ == "__main__":
    test_questions = [
        "LLM 기반의 멀티 에이전트 시스템 설계 경험이 있으신가요?",
        "RAG(Retrieval-Augmented Generation) 성능을 높이기 위해 어떤 기법을 사용하셨나요?",
        "대규모 트래픽이 발생하는 환경에서 추론 속도를 개선한 사례가 있나요?",
        "협업하는 과정에서 의견 차이가 발생했을 때 어떻게 해결하셨나요?",
        "우리 회사의 AI 엔지니어 포지션에 지원하게 된 가장 큰 동기는 무엇인가요?",
        "향후 3년 내 AI 분야에서 본인의 성장 계획은 무엇인가요?",
    ]
    job_category = "AI 에이전트 개발자"

    print(f"🚀 [테스트 실행] '{job_category}' 직무의 예상 질문 분석 중...\n")

    try:
        result_data = phase5(test_questions, job_category)
        report_text = format_phase5_output(result_data)
        print("=" * 50)
        print(report_text)
        print("=" * 50)
    except Exception as error:
        print(f"❌ 실행 중 오류 발생: {error}")
