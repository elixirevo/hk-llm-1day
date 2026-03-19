def phase5():
    print("Phase 5")


import json
import re
from typing import Any
import concurrent.futures


def llm_call(prompt: str) -> str:
    raise NotImplementedError("llm_call 을 주입해주세요.")


def _safe_parse_json(text: str, label: str = "") -> dict:
    """```json … ``` 펜스를 제거하고 JSON 파싱, 실패 시 raw 보존."""
    clean = re.sub(r"```json\s*|\s*```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"⚠️  [{label}] JSON 파싱 실패: {e}")
        return {"error": "parsing_failed", "raw": text}



# 1.  질문 유형 오케스트레이션

QUESTION_TYPES = ["경험검증", "기술깊이", "직무적합", "기업_문화정합", "꼬리"]

ORCHESTRATOR_PROMPT = """
당신은 면접 질문 전략가입니다.
Phase1(JD 분석)과 Phase2(자소서 분석) 결과를 읽고,
아래 5가지 유형에 대해 각각 어떤 소재·키워드에 집중해야 하는지 전략을 JSON으로 반환하세요.

유형:
- 경험검증  : 자소서의 경험이 JD 역할에 실제로 부합하는지 검증
- 기술깊이  : JD 필수 기술에 대한 실제 이해도·구현 경험
- 직무적합  : JD 요건 대비 지원자의 적합도 종합 판단
- 기업_문화정합: 기업 문화·사업 방향과 지원자 가치관 일치 여부
- 꼬리      : 자소서·예상 답변에서 추가 검증이 필요한 약점·모순

반환 형식:
{{
  "strategies": {{
    "경험검증":     {{"focus_keywords": [], "source_hint": ""}},
    "기술깊이":     {{"focus_keywords": [], "source_hint": ""}},
    "직무적합":     {{"focus_keywords": [], "source_hint": ""}},
    "기업_문화정합":{{"focus_keywords": [], "source_hint": ""}},
    "꼬리":         {{"focus_keywords": [], "source_hint": ""}}
  }}
}}

JSON 외 출력 금지.

[Phase1 결과]
{phase1_result}

[Phase2 결과]
{phase2_result}
"""


def orchestrate_question_types(
    phase1_results: list[dict],
    phase2_results: dict,
) -> dict:
    """5가지 질문 유형별 전략을 LLM으로 수립."""
    prompt = ORCHESTRATOR_PROMPT.format(
        phase1_result=json.dumps(phase1_results, ensure_ascii=False, indent=2),
        phase2_result=json.dumps(phase2_results, ensure_ascii=False, indent=2),
    )
    response = llm_call(prompt)
    return _safe_parse_json(response, "orchestrator")



# 2.  Generator - 유형별 면접 질문 생성

GENERATOR_PROMPT = """
당신은 시니어 면접관입니다.
아래 전략과 지원자 정보를 바탕으로 [{question_type}] 유형의 면접 질문을 생성하세요.
피드백이 있으면 반드시 반영해 이전보다 개선된 질문을 작성하세요.

반환 형식:
{{
  "question_type": "{question_type}",
  "questions": [
    {{
      "question":      "면접 질문 (한 문장, 명확하고 구체적)",
      "intent":        "이 질문을 하는 이유 (15자 이내)",
      "answer_guide":  "STAR/PREP 기반 답변 방향 힌트",
      "keyword_tags":  ["태그1", "태그2"]
    }}
  ]
}}

JSON 외 출력 금지.

[질문 유형]
{question_type}

[전략 힌트]
{strategy}

[Phase1 JD 분석 결과]
{phase1_result}

[Phase2 자소서 분석 결과]
{phase2_result}

{feedback_section}
"""

FEEDBACK_TEMPLATE = """
[이전 생성 기록 및 피드백] — 아래를 반드시 반영하세요
{history}
"""


def generate_questions(
    question_type: str,
    strategy: dict,
    phase1_results: list[dict],
    phase2_results: dict,
    feedback_history: str = "",
) -> str:
    """질문을 생성하는 Generator. 피드백이 있으면 함께 전달."""
    feedback_section = (
        FEEDBACK_TEMPLATE.format(history=feedback_history)
        if feedback_history
        else ""
    )
    prompt = GENERATOR_PROMPT.format(
        question_type=question_type,
        strategy=json.dumps(strategy, ensure_ascii=False, indent=2),
        phase1_result=json.dumps(phase1_results, ensure_ascii=False, indent=2),
        phase2_result=json.dumps(phase2_results, ensure_ascii=False, indent=2),
        feedback_section=feedback_section,
    )
    return llm_call(prompt)


# 3.  Evaluator - 생성된 질문 품질 평가

EVALUATOR_PROMPT = """
당신은 면접 질문 품질 심사관입니다.
아래 기준으로 생성된 [{question_type}] 면접 질문을 평가하고 JSON으로 반환하세요.

[평가 기준]

1. 구체성 (specificity)
   - PASS: 질문에 특정 경험·기술·상황이 명시됨
   - FAIL: "경험이 있나요?" 처럼 추상적·일반적

2. 직무연계 (relevance)
   - PASS: JD 필수 요건 또는 자소서 핵심 경험과 직접 연결
   - FAIL: JD·자소서와 무관한 일반 인성 질문

3. 직무적합 (job_fit)
   - PASS: 해당 유형({question_type})의 목적에 부합
   - FAIL: 유형 목적과 어긋남 (예: 기술깊이 유형인데 가치관 질문)

4. 기업_문화정합 (culture_fit)
   - PASS: 기업 문화·사업 방향 키워드 반영 또는 직무적합 질문이면 N/A 허용
   - FAIL: 기업_문화정합 유형임에도 기업 정보 미반영

위 기준을 모두 충족(또는 N/A 처리 적절)하면 PASS.

반환 형식:
{{
  "specificity":   {{"result": "PASS|FAIL", "reason": "..."}},
  "relevance":     {{"result": "PASS|FAIL", "reason": "..."}},
  "job_fit":       {{"result": "PASS|FAIL", "reason": "..."}},
  "culture_fit":   {{"result": "PASS|FAIL|N/A", "reason": "..."}},
  "final_result":  "PASS|FAIL",
  "improvement":   "FAIL 항목 개선 방향 (PASS이면 빈 문자열)"
}}

JSON 외 출력 금지.

[질문 유형]
{question_type}

[생성된 질문]
{generated_questions}

[Phase1 JD 분석 결과]
{phase1_result}

[Phase2 자소서 분석 결과]
{phase2_result}
"""


def evaluate_questions(
    question_type: str,
    generated_questions: str,
    phase1_results: list[dict],
    phase2_results: dict,
) -> str:
    """생성된 질문을 평가하는 Evaluator."""
    prompt = EVALUATOR_PROMPT.format(
        question_type=question_type,
        generated_questions=generated_questions,
        phase1_result=json.dumps(phase1_results, ensure_ascii=False, indent=2),
        phase2_result=json.dumps(phase2_results, ensure_ascii=False, indent=2),
    )
    return llm_call(prompt)



# 4.  단일 유형 평가-최적화 루프

def run_question_loop(
    question_type: str,
    strategy: dict,
    phase1_results: list[dict],
    phase2_results: dict,
    max_retries: int = 5,
) -> dict:
    """
    한 가지 질문 유형에 대해 PASS가 나올 때까지 생성-평가를 반복.

    Returns:
        {
            "question_type": str,
            "questions_raw":  str,          # 최종 생성 결과 (raw)
            "questions":      dict,          # 파싱된 JSON
            "passed":         bool,
            "attempts":       int,
        }
    """
    feedback_history = ""

    for attempt in range(1, max_retries + 1):
        print(f"\n{'='*55}")
        print(f"🔄  [{question_type}] 시도 {attempt}/{max_retries}")
        print(f"{'='*55}")

        # ── Generator ────────────────────────────────────────
        generated_raw = generate_questions(
            question_type=question_type,
            strategy=strategy,
            phase1_results=phase1_results,
            phase2_results=phase2_results,
            feedback_history=feedback_history,
        )
        print(f"\n📝 생성된 질문:\n{generated_raw}")

        # ── Evaluator ─────────────────────────────────────────
        evaluation_raw = evaluate_questions(
            question_type=question_type,
            generated_questions=generated_raw,
            phase1_results=phase1_results,
            phase2_results=phase2_results,
        )
        print(f"\n🔍 평가 결과:\n{evaluation_raw}")

        evaluation = _safe_parse_json(evaluation_raw, f"{question_type}-eval")

        # ── PASS 판정 ──────────────────────────────────────────
        if evaluation.get("final_result") == "PASS":
            print(f"\n✅  [{question_type}] {attempt}회 만에 PASS!")
            return {
                "question_type": question_type,
                "questions_raw": generated_raw,
                "questions":     _safe_parse_json(generated_raw, question_type),
                "evaluation":    evaluation,
                "passed":        True,
                "attempts":      attempt,
            }

        # ── FAIL → 피드백 누적 ────────────────────────────────
        print(f"\n❌  FAIL — 피드백 누적 후 재시도...")
        feedback_history += (
            f"\n[시도 {attempt}]\n"
            f"- 생성된 질문:\n{generated_raw}\n"
            f"- 평가 피드백:\n{evaluation_raw}\n"
        )

    # max_retries 초과
    print(f"\n⚠️  [{question_type}] {max_retries}회 시도 후 미통과. 마지막 결과 반환.")
    return {
        "question_type": question_type,
        "questions_raw": generated_raw,
        "questions":     _safe_parse_json(generated_raw, question_type),
        "evaluation":    evaluation,
        "passed":        False,
        "attempts":      max_retries,
    }



# 5.  최종 출력
FINAL_OUTPUT_PROMPT = """
당신은 면접 준비 리포트 작성 전문가입니다.
아래 5가지 유형의 면접 질문 결과를 통합해 지원자를 위한 최종 리포트 JSON을 작성하세요.

반환 형식:
{{
  "company_name": "{company_name}",
  "job_title":    "{job_title}",
  "report": {{
    "question_list": [
      {{
        "type":         "질문 유형",
        "question":     "면접 질문",
        "intent":       "질문 의도",
        "answer_guide": "답변 방향 가이드",
        "keyword_tags": [],
        "priority_scores": {{
          "difficulty":      "난이도 (예: 상/중/하)",
          "frequency":       "빈출도 (예: 상/중/하)",
          "job_relevance":   "직무 연관도 (예: 상/중/하)",
          "overall_priority": 1
        }}
      }}
    ],
    "answer_strategy": {{
      "star_based":        ["STAR 기반 답변 포인트1", "..."],
      "keyword_guide":     ["강조할 키워드1", "..."],
      "job_fit_summary":   "직무 적합도 한 줄 요약"
    }}
  }},
  "meta": {{
    "total_questions": 0,
    "passed_types":    [],
    "failed_types":    []
  }}
}}

JSON 외 출력 금지.

[기업 정보]
기업명: {company_name}
직무명: {job_title}

[유형별 질문 결과]
{all_results}
"""


def format_final_output(
    all_loop_results: list[dict],
    company_name: str,
    job_title: str,
) -> dict:
    """모든 유형의 루프 결과를 통합해 최종 리포트를 생성."""
    prompt = FINAL_OUTPUT_PROMPT.format(
        company_name=company_name,
        job_title=job_title,
        all_results=json.dumps(all_loop_results, ensure_ascii=False, indent=2),
    )
    response = llm_call(prompt)
    result = _safe_parse_json(response, "final_output")

    # meta 자동 보정
    if "meta" in result:
        passed = [r["question_type"] for r in all_loop_results if r.get("passed")]
        failed = [r["question_type"] for r in all_loop_results if not r.get("passed")]
        total  = sum(
            len(r.get("questions", {}).get("questions", []))
            for r in all_loop_results
        )
        result["meta"]["total_questions"] = total
        result["meta"]["passed_types"]    = passed
        result["meta"]["failed_types"]    = failed

    return result


# ─────────────────────────────────────────────
# 6.  Phase 5 메인 진입점
# ─────────────────────────────────────────────
def run_phase5(
    phase1_results: list[dict],
    phase2_results: dict,
    max_retries: int = 5,
) -> dict:
    """
    Phase 5 전체 파이프라인 실행.

    Args:
        phase1_results : Phase1 run_jd_workers() 의 반환값
        phase2_results : Phase2 분석 결과 dict
        max_retries    : 유형별 최대 재시도 횟수 (기본 5)

    Returns:
        최종 리포트 dict
    """
    # ── 기업명·직무명 추출 (Phase1 wrapper 공통 필드) ──────────
    company_name = phase1_results[0].get("company_name", "Unknown") if phase1_results else "Unknown"
    job_title    = phase1_results[0].get("job_title",    "Unknown") if phase1_results else "Unknown"

    print(f"\n{'#'*60}")
    print(f"  Phase 5 시작 | {company_name} / {job_title}")
    print(f"{'#'*60}")

    # ── Step 1: 질문 유형 오케스트레이션 ──────────────────────
    print("\n🗂️  Step 1: 질문 유형 전략 수립 중...")
    orchestration = orchestrate_question_types(phase1_results, phase2_results)
    strategies    = orchestration.get("strategies", {})

    # ── Step 2: 유형별 평가-최적화 루프 (병렬 처리) ────────────────
    all_loop_results: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(QUESTION_TYPES)) as executor:
        futures = []
        for q_type in QUESTION_TYPES:
            strategy = strategies.get(q_type, {})
            futures.append(
                executor.submit(
                    run_question_loop,
                    q_type,
                    strategy,
                    phase1_results,
                    phase2_results,
                    max_retries,
                )
            )
        
        for future in concurrent.futures.as_completed(futures):
            all_loop_results.append(future.result())

    # ── Step 3: 최종 통합 리포트 생성 ─────────────────────────
    print(f"\n{'='*55}")
    print("📋  Step 3: 최종 리포트 통합 중...")
    print(f"{'='*55}")

    final_report = format_final_output(
        all_loop_results=all_loop_results,
        company_name=company_name,
        job_title=job_title,
    )

    print("\n✅  Phase 5 완료!")
    print(json.dumps(final_report, ensure_ascii=False, indent=2))

    return final_report