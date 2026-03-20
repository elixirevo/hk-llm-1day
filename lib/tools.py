import json
from typing import Any, Dict, List

from openai import OpenAI


# -----------------------------
# 공통 유틸
# -----------------------------

def parse_md_json(text: str) -> dict:
    """
    마크다운 형식의 JSON 문자열을 파싱합니다.
    """
    return json.loads(text.replace("```json", '').replace("```", "").strip())

def _normalize_js_list(js_list: Dict[str, Any]) -> Dict[str, Any]:
    payload = js_list.get("payload", {})
    roles = payload.get("roles", [])

    normalized_roles = []
    for idx, role in enumerate(roles, start=1):
        normalized_roles.append({
            "jd_id": f"R{idx}",
            "role_name": role.get("role_name", ""),
            "required_skills": role.get("required_skills", []),
            "question_type": role.get("question_type", "")
        })

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
        "jd_items": normalized_roles
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
