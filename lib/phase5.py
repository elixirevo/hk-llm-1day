import json
import re
from typing import Any
from collections import defaultdict

def llm_call(prompt: str) -> str:
    raise NotImplementedError("llm_call 을 주입해주세요.")

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

분류 결과는 반드시 위 [유형]에 적힌 텍스트(예: "1) 지원동기 / 직무 적합성")로만 정확히 반환하세요.
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
    """질문 하나를 받아 5개 유형 중 하나로 분류"""
    prompt = CATEGORY_CLASSIFIER_PROMPT.format(question=question)
    return llm_call(prompt).strip()


def score_questions_by_category(questions: list[str], job_category: str) -> list[dict]:
    """
    유형 내 질문 목록을 받아 난이도·빈출도·직무연관도 점수를 부여
    - LLM에 질문 목록을 한 번에 전달해 JSON으로 점수를 반환받음
    """
    if not questions:
        return []
        
    questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    prompt = SCORER_PROMPT.format(job_category=job_category, questions=questions_str)
    raw = llm_call(prompt)
    
    cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(cleaned).get("scores", [])
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON 파싱 실패: {e}")
        return []


def get_ranking_reason(category: str, ranked_questions: list[dict], job_category: str) -> str:
    """
    순위가 정해진 질문 목록을 받아 지원자 관점의 순위 해설을 생성
    """
    if not ranked_questions:
        return ""
        
    ranked_str = "\n".join([
        f"{i+1}위. {q.get('question', '')}\n"
        f"   [난이도:{q.get('difficulty', 0)} / 빈출도:{q.get('frequency', 0)} / 직무연관도:{q.get('relevance', 0)} / 합계:{q.get('total', 0)}]\n"
        f"   근거: {q.get('reason', '')}"
        for i, q in enumerate(ranked_questions)
    ])
    prompt = RANKING_REASON_PROMPT.format(
        job_category=job_category,
        category=category,
        ranked_questions=ranked_str,
    )
    return llm_call(prompt).strip()


def phase5(passed_questions: list[str], job_category: str) -> dict:
    """
    Phase 4에서 PASS된 질문들을 받아 최종 출력 데이터를 생성
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
        
        # Step 3. 총점(total) 내림차순 정렬
        ranked = sorted(scored, key=lambda x: x.get("total", 0), reverse=True)
        
        # Step 4. 순위 해설 생성
        reason = get_ranking_reason(category, ranked, job_category)
        
        final_output[category] = {
            "ranked_questions": ranked,
            "ranking_reason": reason,
        }
        
    return final_output


def format_phase5_output(result: dict, top_n: int = 20) -> str:
    """
    phase5() 반환값을 지정된 글로벌 TOP N 포맷으로 출력
    전체 문항 중 합계 점수(total) 순으로 TOP N개를 선출한 후, 각 카테고리별로 정렬하여 반환
    """
    lines = [f"가장 가능성 높은 예상 질문 TOP {top_n}"]
    
    # 1. 모든 카테고리의 질문들을 하나로 통합 (total 기준 정렬용)
    all_questions = []
    for cat, data in result.items():
        for q in data.get("ranked_questions", []):
            all_questions.append((cat, q))
            
    # 전체에서 내림차순 정렬
    all_questions.sort(key=lambda x: x[1].get("total", 0), reverse=True)
    
    # 2. 상위 N개 추출
    top_questions = all_questions[:top_n]
    
    # 3. 출력 순서를 맞추기 위한 카테고리 순서 프리셋
    category_order = [
        "1) 지원동기 / 직무 적합성",
        "2) 프로젝트 경험 검증",
        "3) AI/LLM/Agent 역량 검증",
        "4) 성능 최적화 / 시스템 설계",
        "5) 인성 / 실행력 / 성장 가능성"
    ]
    
    # 카테고리별로 다시 그룹핑
    grouped = {cat: [] for cat in category_order}
    for cat, q in top_questions:
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(q)
        
    final_cats = category_order + [c for c in grouped.keys() if c not in category_order]
    
    # 4. 출력용 텍스트 생성
    global_counter = 1
    for cat in final_cats:
        cat_qs = grouped.get(cat, [])
        if not cat_qs:
            continue
            
        lines.append(f"{cat}")
        
        # 한 카테고리 안에서도 점수 내림차순 정렬 유지
        cat_qs = sorted(cat_qs, key=lambda x: x.get("total", 0), reverse=True)
        for q in cat_qs:
            lines.append(f"{global_counter}. {q.get('question', '')}")
            lines.append(f"   💡 [점수 근거] {q.get('reason', '')}")
            global_counter += 1
            
        if cat in result and "ranking_reason" in result[cat]:
            lines.append(f"   📌 [유형 분석 포인트]\n   {result[cat]['ranking_reason']}\n")
            
    return "\n".join(lines)