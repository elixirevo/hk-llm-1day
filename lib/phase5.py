import os
import sys
import json
import re
from typing import Any
from collections import defaultdict

# Root 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils.utils import llm_call

# --- PROMPTS ---

CATEGORY_CLASSIFIER_PROMPT = """
다음 면접 질문을 아래 5가지 유형 중 가장 적합한 하나로 분류하세요.

[유형]
1) 지원동기 / 직무 적합성
2) 프로젝트 경험 검증
3) AI/LLM/Agent 역량 검증
4) 성능 최적화 / 시스템 설계
5) 인성 / 실행력 / 성장 가능성

[질문]
{question}

분류 결과는 반드시 위 [유형]에 순서대로 반환하세요.
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

# --- CORE FUNCTIONS (Original Logic) ---

def classify_question(question: str) -> str:
    """질문 하나를 받아 5개 유형 중 하나로 분류"""
    prompt = CATEGORY_CLASSIFIER_PROMPT.format(question=question)
    return llm_call(prompt).strip()

def score_questions_by_category(questions: list[str], job_category: str) -> list[dict]:
    """유형 내 질문 목록을 받아 개별 점수 부여"""
    if not questions:
        return []
        
    questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    prompt = SCORER_PROMPT.format(job_category=job_category, questions=questions_str)
    raw = llm_call(prompt)
    
    cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(cleaned).get("scores", [])
    except json.JSONDecodeError:
        return []

def get_ranking_reason(category: str, ranked_questions: list[dict], job_category: str) -> str:
    """순위가 정해진 질문 목록을 받아 순위 해설 생성"""
    if not ranked_questions:
        return ""
        
    ranked_str = "\n".join([
        f"{i+1}위. {q.get('question', '')} (합계:{q.get('total', 0)})"
        for i, q in enumerate(ranked_questions)
    ])
    prompt = RANKING_REASON_PROMPT.format(
        job_category=job_category,
        category=category,
        ranked_questions=ranked_str,
    )
    return llm_call(prompt).strip()

# --- OUTPUT LOGIC (Streamlined) ---

def phase5(passed_questions: list[str], job_category: str) -> dict:
    """
    1. 분류 (Atomic)
    2. 카테고리별 채점 및 점수 정렬
    3. 카테고리별 해설 생성
    """
    # Step 1. 유형별 분류
    categorized = defaultdict(list)
    for question in passed_questions:
        category = classify_question(question)
        categorized[category].append(question)

    final_output = {}
    for category, questions in categorized.items():
        # Step 2. 점수 부여
        scored = score_questions_by_category(questions, job_category)
        
        # Step 3. 카테고리 내 점수 내림차순 정렬
        ranked = sorted(scored, key=lambda x: x.get("total", 0), reverse=True)
        
        # Step 4. 순위 해설 생성
        reason = get_ranking_reason(category, ranked, job_category)
        
        final_output[category] = {
            "ranked_questions": ranked,
            "ranking_reason": reason,
        }
        
    return final_output

def format_phase5_output(result: dict) -> str:
    """
    phase5 결과를 받아서 지정된 카테고리 순서대로 텍스트 출력만 담당
    (개별 분석 내용 제거 및 카테고리별 독립 순위 표시)
    """
    if not result:
        return "표시할 예상 질문이 없습니다."

    category_order = [
        "1) 지원동기 / 직무 적합성",
        "2) 프로젝트 경험 검증",
        "3) AI/LLM/Agent 역량 검증",
        "4) 성능 최적화 / 시스템 설계",
        "5) 인성 / 실행력 / 성장 가능성"
    ]
    
    lines = ["🏆 직무별 핵심 예상 질문 리포트\n"]
    
    # 1. 정해진 순서대로 카테고리 필터링
    sorted_cats = [c for c in category_order if c in result]
    # 2. 혹시 카테고리 목록에 없는 분류가 있다면 뒤에 추가
    sorted_cats += [c for c in result if c not in category_order]
    
    for cat in sorted_cats:
        data = result[cat]
        lines.append(f"■ {cat}")
        
        # 카테고리 내에서 1위부터 순위 매김 (이미 점수순 정렬된 상태)
        for i, q in enumerate(data.get("ranked_questions", [])):
            rank = i + 1
            lines.append(f"  {rank}위. {q.get('question', '')}")
            
    return "\n".join(lines).strip()


if __name__ == "__main__":
    def main():
        # 1. 테스트용 데이터 준비 (Phase 4를 통과했다고 가정한 질문들)
        test_questions = [
            "LLM 기반의 멀티 에이전트 시스템 설계 경험이 있으신가요?",
            "RAG(Retrieval-Augmented Generation) 성능을 높이기 위해 어떤 기법을 사용하셨나요?",
            "대규모 트래픽이 발생하는 환경에서 추론 속도를 개선한 사례가 있나요?",
            "협업하는 과정에서 의견 차이가 발생했을 때 어떻게 해결하셨나요?",
            "우리 회사의 AI 엔지니어 포지션에 지원하게 된 가장 큰 동기는 무엇인가요?",
            "향후 3년 내 AI 분야에서 본인의 성장 계획은 무엇인가요?"
        ]
        
        # 2. 직무 카테고리 설정
        job_category = "AI 에이전트 개발자"
        
        print(f"🚀 [테스트 실행] '{job_category}' 직무의 예상 질문 분석 중...\n")
        
        try:
            # 3. Phase 5 실행 (분류, 채점, 정렬, 요약)
            # ※ 실제 LLM API 호출이 발생하므로 시간이 약간 소요될 수 있습니다.
            result_data = phase5(test_questions, job_category)
            
            # 4. 결과 포맷팅 및 출력
            report_text = format_phase5_output(result_data)
            
            print("=" * 50)
            print(report_text)
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 실행 중 오류 발생: {e}")

    main()












import os
from lib.phase5 import phase5, format_phase5_output

def main():
    # 1. 테스트용 데이터 준비 (Phase 4를 통과했다고 가정한 질문들)
    test_questions = [
        "LLM 기반의 멀티 에이전트 시스템 설계 경험이 있으신가요?",
        "RAG(Retrieval-Augmented Generation) 성능을 높이기 위해 어떤 기법을 사용하셨나요?",
        "대규모 트래픽이 발생하는 환경에서 추론 속도를 개선한 사례가 있나요?",
        "협업하는 과정에서 의견 차이가 발생했을 때 어떻게 해결하셨나요?",
        "우리 회사의 AI 엔지니어 포지션에 지원하게 된 가장 큰 동기는 무엇인가요?",
        "향후 3년 내 AI 분야에서 본인의 성장 계획은 무엇인가요?"
    ]
    
    # 2. 직무 카테고리 설정
    job_category = "AI 에이전트 개발자"
    
    print(f"🚀 [테스트 실행] '{job_category}' 직무의 예상 질문 분석 중...\n")
    
    try:
        # 3. Phase 5 실행 (분류, 채점, 정렬, 요약)
        # ※ 실제 LLM API 호출이 발생하므로 시간이 약간 소요될 수 있습니다.
        result_data = phase5(test_questions, job_category)
        
        # 4. 결과 포맷팅 및 출력
        report_text = format_phase5_output(result_data)
        
        print("=" * 50)
        print(report_text)
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
