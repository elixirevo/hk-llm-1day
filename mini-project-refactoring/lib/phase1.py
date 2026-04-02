import asyncio
import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Callable

@dataclass
class AgentTask:
    agent_id: str
    content:  str
    model: str = "gpt-4o"


# ── 경계 탐지용 앵커 (슬라이싱 기준점) ──────────────────────────
ANCHORS = [
    "Role",
    "Recommended Subject",
    "Requirements",
    "Pluses",
    "Career Vision",
]

# ── 에이전트에 실제로 전달할 섹션 ────────────────────────────────
AGENT_MAP = {
    "Role":          "role",
    "Requirements":  "req",
    "Pluses":        "plus",
}

def parse_header_info(jd_text: str) -> tuple[str, str]:
    """
    JD 원문을 받아 회사명과 직무명을 추출합니다.
    반환값: (company_name, job_title)
    """
    lines = jd_text.strip().splitlines()
    if not lines:
        return "Unknown Company", "Unknown Job"
    
    first_line = lines[0].replace("#", "").strip()
    first_line = first_line.replace("Job Description", "").strip()
    parts = first_line.split()
    
    if len(parts) >= 2:
        company_name = " ".join(parts[:-1])
        job_title = parts[-1]
    else:
        company_name = first_line
        job_title = "Unknown Job"
    
    doc_company = company_name
    doc_job = job_title
    
    for line in lines:
        line = line.strip()
        if "* **직무**:" in line or "* 직무:" in line:
            doc_job = line.split(":", 1)[1].strip()
            
    return doc_company, doc_job

# JD 앵커 별 text 파싱
def build_tasks(jd_text: str) -> List[AgentTask]:
    """
    JD 원문을 받아 워커별 입력 단위로 분해한 AgentTask 리스트를 생성합니다.
    반환값: AgentTask 객체 리스트
    """
    # 1) 첫 줄 추출 (기업 / 부서 / 직무)
    lines = jd_text.strip().splitlines()
    first_line = lines[0] if lines else ""

    # 2) 모든 앵커 위치 탐색
    positions = {}
    for anchor in ANCHORS:
        m = re.search(rf'#+\s*[^\n]*{re.escape(anchor)}', jd_text)
        if m:
            positions[anchor] = m.start()

    # 3) 위치순 정렬
    ordered = sorted(positions.items(), key=lambda x: x[1])

    # 4) 인접 앵커 사이 슬라이싱
    sections = {}
    for i, (name, start) in enumerate(ordered):
        end = ordered[i + 1][1] if i + 1 < len(ordered) else None
        sections[name] = jd_text[start:end].strip()

    # 5) AgentTask 조립 (sections.get 으로 KeyError 방지 및 fallback 처리)
    tasks = []
    for anchor, agent_id in AGENT_MAP.items():
        content = sections.get(anchor, f"No {anchor} section found.")
        tasks.append(AgentTask(agent_id=agent_id, content=content, model="gpt-4o"))

    biz_corp_content = f"{first_line}\n\n{sections.get('Career Vision', 'No Career Vision section found.')}"
    
    # biz, corp 는 gpt-4.1 로 모델 분기
    tasks.append(AgentTask(agent_id="biz", content=biz_corp_content, model="gpt-4.1"))
    tasks.append(AgentTask(agent_id="corp", content=biz_corp_content, model="gpt-4.1"))

    return tasks

# Agent 1 — 직무 요건 키워드 추출 (req)
def get_req_prompt(content: str) -> str:
    """
    Requirements 섹션 텍스트를 받아 req 워커용 프롬프트를 생성합니다.
    반환값: 필수 역량 추출용 프롬프트 문자열
    """
    return f"""
당신은 직무기술서의 Requirements 섹션을 분석하는 전문가입니다.
아래 Requirements 섹션을 읽고 필수 역량 키워드를 추출하여 JSON으로 반환하세요.

반환 형식:
{{
    "requirements": [
        {{
            "keyword":  "역량 키워드 (예: LLM/Agent 설계)",
            "type":     "must | preferred",
            "weight":   0.0~1.0,
            "evidence": "근거 문장 요약 (15자 이내)"
        }}
    ]
}}

규칙:
- type must      : Requirements 섹션에 명시된 항목
- type preferred : Role 섹션에서 유추되는 역량
- weight         : 키워드 반복 등장 시 0.1씩 가산, 최대 1.0

JSON 외 다른 텍스트 출력 금지.

Requirements 섹션:
{content}
"""

# Agent 2 — 우대사항 추출 (plus)
def get_plus_prompt(content: str) -> str:
    """
    Pluses 섹션 텍스트를 받아 plus 워커용 프롬프트를 생성합니다.
    반환값: 우대사항 추출용 프롬프트 문자열
    """
    return f"""
당신은 직무기술서의 Pluses 섹션을 분석하는 전문가입니다.
아래 Pluses 섹션을 읽고 우대사항을 분석하여 JSON으로 반환하세요.

반환 형식:
{{
    "pluses": [
        {{
            "keyword":       "우대사항 키워드",
            "category":      "기술 | 경험 | 자격증 | 어학 중 하나",
            "appeal":        "high | mid | low",
            "question_hint": "이 항목 보유 시 예상되는 면접 질문 유형"
        }}
    ]
}}

appeal 기준:
- high : 직무 핵심 기술 직결, 보유 시 강력한 차별화
- mid  : 보유하면 좋지만 없어도 결격 아님
- low  : 일반적 우대사항 (공모전, 자격증 등)

JSON 외 다른 텍스트 출력 금지.

Pluses 섹션:
{content}
"""

# Agent 3 — 직무 역할 구조화 (role)
def get_role_prompt(content: str) -> str:
    """
    Role 섹션 텍스트를 받아 role 워커용 프롬프트를 생성합니다.
    반환값: 업무 역할 구조화용 프롬프트 문자열
    """
    return f"""
당신은 직무기술서의 Role 섹션을 분석하는 전문가입니다.
아래 Role 섹션을 읽고 실제 업무 역할을 구조화하여 JSON으로 반환하세요.

반환 형식:
{{
    "roles": [
        {{
            "role_name":       "업무명",
            "required_skills": ["필요 기술1", "필요 기술2"],
            "question_type":   "기술깊이 | 경험검증 | 의사결정 | 직무적합 중 하나"
        }}
    ]
}}

question_type 판단 기준:
- 기술깊이  : 구체적 기술 구현이 명시된 역할
- 경험검증  : 프로젝트·협업 경험이 필요한 역할
- 의사결정  : 설계·기획·선택이 포함된 역할
- 직무적합  : 도메인 이해·비즈니스 연계 역할

JSON 외 다른 텍스트 출력 금지.

Role 섹션:
{content}
"""

# Agent 4 — 사업 방향·조직 문화 (biz) · web_search
def get_biz_prompt(content: str) -> str:
    """
    기업·직무 정보와 Career Vision 텍스트를 받아 biz 워커용 프롬프트를 생성합니다.
    반환값: 사업 방향 분석용 프롬프트 문자열
    """
    return f"""
당신은 기업의 사업 방향을 분석하는 전문가입니다.
아래 기업·직무 정보와 Career Vision을 바탕으로
web_search를 실행해 최신 사업 전략을 조사하고 JSON으로 반환하세요.

반환 형식:
{{
    "biz_direction": {{
        "strategy_keywords":  ["키워드1", "키워드2"],
        "recent_initiatives": [
            {{"topic": "이니셔티브명", "summary": "한 줄 요약"}}
        ],
        "why_company_seeds": ["지원 동기 문장1", "문장2"]
    }}
}}

JSON 외 다른 텍스트 출력 금지.

기업·직무 정보:
{content}
"""

# Agent 5 — 기업 분석 (corp) · web_search
def get_corp_prompt(content: str) -> str:
    """
    기업·직무 정보와 Career Vision 텍스트를 받아 corp 워커용 프롬프트를 생성합니다.
    반환값: 기업 현황 분석용 프롬프트 문자열
    """
    return f"""
당신은 기업 정보를 조사하는 전문가입니다.
아래 기업·직무 정보를 바탕으로 web_search를 실행해
기업 현황을 조사하고 JSON으로 반환하세요.

반환 형식:
{{
    "company_info": {{
        "recent_news":      [{{"title": "제목", "summary": "한 줄 요약", "source": "URL"}}],
        "culture_keywords": ["문화 키워드1", "키워드2"],
        "differentiators":  ["경쟁사 대비 강점1", "강점2"]
    }}
}}

JSON 외 다른 텍스트 출력 금지.

기업·직무 정보:
{content}
"""

# 워커 프롬프트 생성 맵
PROMPT_FN_MAP = {
    "role": get_role_prompt,
    "req":  get_req_prompt,
    "plus": get_plus_prompt,
    "biz":  get_biz_prompt,
    "corp": get_corp_prompt,
}

def get_worker_prompt(agent_id: str, content: str) -> str:
    """
    agent_id와 섹션 내용을 받아 해당 워커의 프롬프트를 생성합니다.
    반환값: 워커별 프롬프트 문자열
    """
    return PROMPT_FN_MAP[agent_id](content)

# prompt_details 조립 함수
def build_prompt_details(tasks: List[AgentTask]) -> list:
    """
    AgentTask 리스트를 받아 LLM 병렬 실행용 prompt_details 형식으로 변환합니다.
    반환값: agent_id, user_prompt, model 정보를 담은 딕셔너리 리스트
    """
    return [
        {
            "agent_id":    task.agent_id,
            "user_prompt": get_worker_prompt(task.agent_id, task.content),
            "model":       task.model,
        }
        for task in tasks
    ]

# LLM 병렬 실행 (명시적으로 model 인자 전달)
async def run_llm_parallel(prompt_details: list, llm_async_fn: Callable) -> list:
    """
    prompt_details 리스트와 비동기 LLM 호출 함수를 받아 워커들을 병렬 실행합니다.
    반환값: prompt_details와 같은 순서의 응답 문자열 리스트
    """
    tasks = [
        llm_async_fn(item["user_prompt"], item["model"])
        for item in prompt_details
    ]
    responses = await asyncio.gather(*tasks)
    return responses

# 공통 JSON 파서 및 클리너
def clean_json_response(response: str, agent_id: str) -> dict:
    """
    워커 응답 문자열을 받아 코드블록을 제거하고 JSON 파싱을 수행합니다.
    반환값: 파싱된 JSON 딕셔너리, 실패 시 에러 정보를 담은 딕셔너리
    """
    try:
        clean = re.sub(r'```json\s*|\s*```', '', response).strip()
        # Fallback: find the outermost brackets just in case
        start_idx = clean.find('{')
        end_idx = clean.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean = clean[start_idx:end_idx+1]
        
        parsed = json.loads(clean)
        return parsed
    except json.JSONDecodeError as e:
        print(f"❌ [{agent_id}] 파싱 실패: {e}")
        return {"error": "parsing_failed", "raw": response}

# Phase 1 메인 실행 파이프라인
async def run_jd_workers(jd_text: str, llm_async_fn: Callable) -> List[Dict[str, Any]]:
    """
    JD 원문과 비동기 LLM 호출 함수를 받아 Phase 1 전체 파이프라인을 실행합니다.
    반환값: company_name, job_title, agent_id, payload 구조의 wrapper JSON 리스트
    """
    # 1. 태스크 분해
    tasks = build_tasks(jd_text)

    # 2. 프롬프트 디테일 조립
    worker_prompt_details = build_prompt_details(tasks)

    # 3. 워커 병렬 실행
    worker_responses = await run_llm_parallel(worker_prompt_details, llm_async_fn)

    # 4. 회사명, 직무명 파싱
    company_name, job_title = parse_header_info(jd_text)

    # 5. 응답 JSON 파싱 및 공통 wrapper 조립
    final_results = []
    for detail, response_text in zip(worker_prompt_details, worker_responses):
        agent_id = detail["agent_id"]
        parsed_payload = clean_json_response(response_text, agent_id)
        
        wrapper = {
            "company_name": company_name,
            "job_title": job_title,
            "agent_id": agent_id,
            "payload": parsed_payload
        }
        final_results.append(wrapper)

    return final_results

def phase1():
    """
    Phase 1 모듈이 정상적으로 로드되었는지 확인하기 위한 진입 함수입니다.
    반환값: 없음
    """
    print("Phase 1 implementation loaded. Use run_jd_workers() asynchronously.")
