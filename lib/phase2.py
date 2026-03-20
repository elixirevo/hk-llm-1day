import os
import sys
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils.utils import llm_call
from tools import parse_md_json, _normalize_js_list, _normalize_personal_statements, _dedupe_keep_order, _safe_output_text, _structured_call

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

# -----------------------------
# 1) analyze_and_match_essay
# -----------------------------

def _analyze_single_statement(
    client: OpenAI,
    model: str,
    jd_items: List[Dict[str, Any]],
    statement_item: Dict[str, str],
) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question_id": {"type": "string"},
            "question_text": {"type": "string"},
            "answer_text": {"type": "string"},
            "item_type": {
                "type": "string",
                "enum": [
                    "motivation_vision",
                    "personal_narrative",
                    "issue_analysis",
                    "job_fit",
                    "mixed"
                ]
            },
            "question_intent": {
                "type": "array",
                "items": {"type": "string"}
            },
            "matched_jd": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "jd_id": {"type": "string"},
                        "jd_label": {"type": "string"},
                        "match_score": {"type": "number"},
                        "reason": {"type": "string"}
                    },
                    "required": ["jd_id", "jd_label", "match_score", "reason"]
                }
            },
            "key_points": {
                "type": "array",
                "items": {"type": "string"}
            },
            "possible_risks": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": [
            "question_id",
            "question_text",
            "answer_text",
            "item_type",
            "question_intent",
            "matched_jd",
            "key_points",
            "possible_risks"
        ]
    }

    system_prompt = """
너는 JD-자기소개서 매칭 분석기다.

입력:
- JD 핵심 항목 목록
- 자기소개서 질문/답변 1개

해야 할 일:
1. 이 문항의 성격(item_type)을 분류한다.
2. 이 문항이 실제로 평가하려는 포인트(question_intent)를 추론한다.
3. 답변을 JD 핵심 항목과 매칭한다.
4. 왜 매칭했는지 reason을 근거 중심으로 쓴다.
5. 면접관이 바로 물을 만한 핵심 포인트(key_points)를 추출한다.
6. 약점, 설명 부족, 과장 가능성, 도메인 미스매치 등을 possible_risks에 적는다.

규칙:
- matched_jd는 상위 3개까지만 넣는다.
- match_score는 0.0~1.0 범위다.
- 입력에 없는 사실은 만들지 않는다.
- 짧고 실무적으로 쓴다.
- JSON만 반환한다.
""".strip()

    payload = {
        "jd_items": jd_items,
        "statement_item": statement_item
    }

    return _structured_call(
        client,
        model=model,
        schema_name="analyze_and_match_essay_single",
        schema=schema,
        system_prompt=system_prompt,
        user_payload=payload,
    )


def analyze_and_match_statement(
    js_list: Dict[str, Any],
    personal_statement_list: List[Dict[str, str]],
    *,
    client: Optional[OpenAI] = None,
    model: str = "gpt-5.4-mini",
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    입력:
        js_list: JD 원본 dict
        personal_statement_list: [{"question": "...", "answer": "..."}, ...]

    출력:
        {
            "target": {...},
        "items": [ ... 분석 결과 ... ]
        }
    """
    client = client or OpenAI()

    jd_bundle = _normalize_js_list(js_list)
    statement_items = _normalize_personal_statements(personal_statement_list)

    results: List[Optional[Dict[str, Any]]] = [None] * len(statement_items)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _analyze_single_statement,
                client,
                model,
                jd_bundle["jd_items"],
                item
            ): idx
            for idx, item in enumerate(statement_items)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()

    return {
        "target": {
            "company": jd_bundle["company"],
            "division": jd_bundle["division"],
            "role": jd_bundle["role"]
        },
        "items": results
    }


# -----------------------------
# 2) build_question_context
# -----------------------------

def _build_single_question_context(
    client: OpenAI,
    model: str,
    analyzed_item: Dict[str, Any],
) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question_id": {"type": "string"},
            "question_context": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "main_topics": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "verification_points": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "risk_points": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "followup_topics": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "main_topics",
                    "verification_points",
                    "risk_points",
                    "followup_topics"
                ]
            }
        },
        "required": ["question_id", "question_context"]
    }

    system_prompt = """
너는 면접 질문 생성 전 단계의 컨텍스트 정리기다.

입력:
- 문항별 JD-자소서 분석 결과 1개

해야 할 일:
1. main_topics: 이 문항에서 면접 질문이 나올 큰 주제를 정리한다.
2. verification_points: 사실 검증, 기술 검증, 경험 검증이 필요한 포인트를 적는다.
3. risk_points: 약점 검증 질문으로 이어질 포인트를 적는다.
4. followup_topics: 꼬리질문으로 확장 가능한 주제를 적는다.

규칙:
- 질문 자체를 만들지 않는다.
- 짧은 명사구/짧은 문장 위주로 쓴다.
- analyzed_item의 key_points, possible_risks, matched_jd를 적극 활용한다.
- JSON만 반환한다.
""".strip()

    payload = {
        "analyzed_item": analyzed_item
    }

    return _structured_call(
        client,
        model=model,
        schema_name="build_question_context_single",
        schema=schema,
        system_prompt=system_prompt,
        user_payload=payload,
    )


def build_question_context(
    analyzed_result: Dict[str, Any],
    *,
    client: Optional[OpenAI] = None,
    model: str = "gpt-5.4-mini",
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    입력:
        analyze_and_match_essay() 결과

    출력:
        {
            "target": {...},
            "items": [
                {
                    ...기존 analyzed item...,
                    "question_context": {...}
                }
            ]
        }
    """
    client = client or OpenAI()
    items = analyzed_result["items"]

    enriched_items: List[Optional[Dict[str, Any]]] = [None] * len(items)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_build_single_question_context, client, model, item): idx
            for idx, item in enumerate(items)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            context_result = future.result()
            merged = dict(items[idx])
            merged["question_context"] = context_result["question_context"]
            enriched_items[idx] = merged

    return {
        "target": analyzed_result["target"],
        "items": enriched_items
    }


# -----------------------------
# 3) aggregate_phase2_results
# -----------------------------

def aggregate_phase2_results(
    js_list,
    contextualized_result,
    *,
    client=None,
    model="gpt-5.4-mini",
):
    client = client or OpenAI()
    jd_bundle = _normalize_js_list(js_list)
    items = contextualized_result["items"]
    jd_items = jd_bundle["jd_items"]

    all_jd_ids = [jd["jd_id"] for jd in jd_items]
    jd_max_scores = {jd_id: 0.0 for jd_id in all_jd_ids}

    merged_risks = []
    for item in items:
        merged_risks.extend(item.get("possible_risks", []))
        qc = item.get("question_context", {})
        merged_risks.extend(qc.get("risk_points", []))

        for matched in item.get("matched_jd", []):
            jd_id = matched["jd_id"]
            score = float(matched.get("match_score", 0.0))
            if jd_id in jd_max_scores:
                jd_max_scores[jd_id] = max(jd_max_scores[jd_id], score)

    strong_match_jd_ids = [jd_id for jd_id, score in jd_max_scores.items() if score >= 0.75]
    weak_match_jd_ids = [jd_id for jd_id, score in jd_max_scores.items() if 0.45 <= score < 0.75]
    missing_jd_ids = [jd_id for jd_id, score in jd_max_scores.items() if score < 0.45]

    merged_risks = _dedupe_keep_order(merged_risks)

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "global_risks": {
                "type": "array",
                "items": {"type": "string"}
            },
            "priority_question_topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "topic": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {"type": "number"}
                    },
                    "required": ["topic", "reason", "priority"]
                }
            }
        },
        "required": ["global_risks", "priority_question_topics"]
    }

    system_prompt = """
너는 Phase2 최종 규합기다.
문항별 결과를 바탕으로 global_risks와 priority_question_topics를 생성하라.
JSON만 반환한다.
    """.strip()

    payload = {
        "target": contextualized_result["target"],
        "jd_items": jd_items,
        "items": items,
        "precomputed": {
            "strong_match_jd_ids": strong_match_jd_ids,
            "weak_match_jd_ids": weak_match_jd_ids,
            "missing_jd_ids": missing_jd_ids,
            "merged_risks": merged_risks
        }
    }

    llm_global = _structured_call(
        client,
        model=model,
        schema_name="aggregate_phase2_results_global",
        schema=schema,
        system_prompt=system_prompt,
        user_payload=payload,
    )

    # 여기서 원문 제거
    slim_items = []
    for item in items:
        slim_items.append({
            "question_id": item["question_id"],
            "item_type": item["item_type"],
            "question_intent": item["question_intent"],
            "matched_jd": item["matched_jd"],
            "key_points": item["key_points"],
            "possible_risks": item["possible_risks"],
            "question_context": item["question_context"],
        })

    return {
        "phase2_output_version": "1.0",
        "target": contextualized_result["target"],
        "items": slim_items,
        "global_context": {
            "strong_match_jd_ids": strong_match_jd_ids,
            "weak_match_jd_ids": weak_match_jd_ids,
            "missing_jd_ids": missing_jd_ids,
            "global_risks": llm_global["global_risks"],
            "priority_question_topics": llm_global["priority_question_topics"]
        }
    }

# -----------------------------
# 실행 예시 코드
# -----------------------------
# if __name__ == "__main__":
#     from pprint import pprint

#     # OpenAI 클라이언트 초기화 (OPENAI_API_KEY 환경변수 필요)
#     client = OpenAI()

#     # 타겟 JD 설정 (sample_jd_list의 첫 번째 요소인 'role' 정보 사용)
#     target_jd = sample_jd_list[0]
    
#     print("=" * 50)
#     print("=== [STEP 1] analyze_and_match_essay ===")
#     print("=" * 50)
#     analyzed_result = analyze_and_match_essay(
#         js_list=target_jd,
#         personal_statement_list=personal_statement_list,
#         client=client,
#         model="gpt-4o-mini"
#     )
#     pprint(analyzed_result)

#     print("\n" + "=" * 50)
#     print("=== [STEP 2] build_question_context ===")
#     print("=" * 50)
#     context_result = build_question_context(
#         analyzed_result=analyzed_result,
#         client=client,
#         model="gpt-4o-mini"
#     )
#     pprint(context_result)

#     print("\n" + "=" * 50)
#     print("=== [STEP 3] aggregate_phase2_results ===")
#     print("=" * 50)
#     final_output = aggregate_phase2_results(
#         js_list=target_jd,
#         contextualized_result=context_result,
#         client=client,
#         model="gpt-4o-mini"
#     )
#     pprint(final_output)

