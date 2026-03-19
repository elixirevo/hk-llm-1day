import json

def parse_md_json(text: str) -> dict:
    """
    마크다운 형식의 JSON 문자열을 파싱합니다.
    """
    return json.loads(text.replace("```json", '').replace("```", "").strip())
