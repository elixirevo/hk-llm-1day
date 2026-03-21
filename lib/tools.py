import json
import re
from typing import Any, Dict, List

from openai import OpenAI


# -----------------------------
# 공통 유틸
# -----------------------------

def parse_md_json(text: str) -> dict:
    """
    마크다운 형식의 JSON 문자열을 파싱합니다.
    """
    return json.loads(clean_json_text(text))


def clean_json_text(text: str) -> str:
    """
    코드블록이나 앞뒤 설명이 섞인 응답에서 JSON 본문만 추출합니다.
    """
    clean = re.sub(r"```json\s*|\s*```", "", text).strip()
    object_start = clean.find("{")
    object_end = clean.rfind("}")
    if object_start != -1 and object_end != -1 and object_start < object_end:
        return clean[object_start:object_end + 1]

    array_start = clean.find("[")
    array_end = clean.rfind("]")
    if array_start != -1 and array_end != -1 and array_start < array_end:
        return clean[array_start:array_end + 1]

    return clean


def parse_md_json_list(text: str) -> list:
    """
    마크다운 형식의 JSON 배열 문자열을 파싱합니다.
    """
    return json.loads(clean_json_text(text))


def _build_role_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    roles = payload.get("roles", [])
    normalized_roles = []
    for idx, role in enumerate(roles, start=1):
        normalized_roles.append({
            "jd_id": f"R{idx}",
            "jd_label": role.get("role_name", ""),
            "role_name": role.get("role_name", ""),
            "required_skills": role.get("required_skills", []),
            "question_type": role.get("question_type", ""),
            "source": "role",
        })
    return normalized_roles


def _build_requirement_items(payload: Dict[str, Any], start_idx: int) -> List[Dict[str, Any]]:
    requirements = payload.get("requirements", [])
    items = []
    for offset, requirement in enumerate(requirements, start=start_idx):
        keyword = requirement.get("keyword", "")
        label = f"{keyword} ({requirement.get('type', 'must')})".strip()
        items.append({
            "jd_id": f"REQ{offset}",
            "jd_label": label,
            "role_name": label,
            "required_skills": [keyword] if keyword else [],
            "question_type": "직무적합",
            "source": "req",
        })
    return items


def _build_plus_items(payload: Dict[str, Any], start_idx: int) -> List[Dict[str, Any]]:
    pluses = payload.get("pluses", [])
    items = []
    for offset, plus in enumerate(pluses, start=start_idx):
        keyword = plus.get("keyword", "")
        label = f"{keyword} ({plus.get('appeal', 'mid')})".strip()
        items.append({
            "jd_id": f"PLUS{offset}",
            "jd_label": label,
            "role_name": label,
            "required_skills": [keyword] if keyword else [],
            "question_type": "직무적합",
            "source": "plus",
        })
    return items


def merge_phase1_results(phase1_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Phase 1 워커 결과 리스트를 Phase 2 이후 단계에서 쓰기 좋은 단일 컨텍스트로 정규화합니다.
    """
    if not phase1_results:
        return {
            "company_name": "",
            "job_title": "",
            "agent_id": "merged",
            "payload": {},
            "jd_items": [],
        }

    base = phase1_results[0]
    payload_by_agent = {
        item.get("agent_id", ""): item.get("payload", {})
        for item in phase1_results
    }

    role_items = _build_role_items(payload_by_agent.get("role", {}))
    req_items = _build_requirement_items(payload_by_agent.get("req", {}), start_idx=1)
    plus_items = _build_plus_items(payload_by_agent.get("plus", {}), start_idx=1)

    return {
        "company_name": base.get("company_name", ""),
        "job_title": base.get("job_title", ""),
        "agent_id": "merged",
        "payload": {
            "roles": payload_by_agent.get("role", {}).get("roles", []),
            "requirements": payload_by_agent.get("req", {}).get("requirements", []),
            "pluses": payload_by_agent.get("plus", {}).get("pluses", []),
            "biz_direction": payload_by_agent.get("biz", {}).get("biz_direction", {}),
            "company_info": payload_by_agent.get("corp", {}).get("company_info", {}),
        },
        "jd_items": role_items + req_items + plus_items,
    }

def _normalize_js_list(js_list: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(js_list, list):
        js_list = merge_phase1_results(js_list)

    if js_list.get("agent_id") == "merged" and "jd_items" in js_list:
        payload = js_list.get("payload", {})
        company_name = js_list.get("company_name", "")
        job_title = js_list.get("job_title", "")
        parts = company_name.split(" ", 1)
        company = parts[0] if parts else company_name
        division = parts[1] if len(parts) > 1 else ""

        return {
            "company": company,
            "division": division,
            "role": job_title,
            "jd_items": js_list.get("jd_items", []),
            "requirements": payload.get("requirements", []),
            "pluses": payload.get("pluses", []),
            "biz_direction": payload.get("biz_direction", {}),
            "company_info": payload.get("company_info", {}),
        }

    payload = js_list.get("payload", {})
    normalized_roles = _build_role_items(payload)

    company_name = js_list.get("company_name", "")
    job_title = js_list.get("job_title", "")

    # "삼성전자 DS부문 AI센터" -> company="삼성전자", division="DS부문 AI센터"
    parts = company_name.split(" ", 1)
    company = parts[0] if parts else company_name
    division = parts[1] if len(parts) > 1 else ""

    return {
        "company": company,
        "division": division,
        "role": job_title,
        "jd_items": normalized_roles,
        "requirements": payload.get("requirements", []),
        "pluses": payload.get("pluses", []),
        "biz_direction": payload.get("biz_direction", {}),
        "company_info": payload.get("company_info", {}),
    }


def _normalize_personal_statements(personal_statement_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
    normalized = []
    for idx, item in enumerate(personal_statement_list, start=1):
        normalized.append({
            "question_id": f"Q{idx}",
            "question_text": item.get("question", "").strip(),
            "answer_text": item.get("answer", "").strip(),
        })
    return normalized


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for v in values:
        key = v.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _safe_output_text(response: Any) -> str:
    if getattr(response, "output_text", None):
        return response.output_text
    raise RuntimeError("Responses API 응답에서 output_text를 찾지 못했습니다.")


def _structured_call(
    client: OpenAI,
    *,
    model: str,
    schema_name: str,
    schema: Dict[str, Any],
    system_prompt: str,
    user_payload: Dict[str, Any],
) -> Dict[str, Any]:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema
            }
        }
    )
    return json.loads(_safe_output_text(response))
