from __future__ import annotations

from typing import TYPE_CHECKING

from dotenv import load_dotenv
from IPython.display import display, HTML
from openai import AsyncOpenAI, OpenAI

load_dotenv()

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage

# ── OpenAI 클라이언트 생성 ────────────────────────────────────────
sync_client = OpenAI()
async_client = AsyncOpenAI()

# ── LLM 호출 함수 ────────────────────────────────────────────────

def llm_call(prompt: str, model: str = "gpt-4o-mini") -> str:
    messages = [{"role": "user", "content": prompt}]
    chat_completion = sync_client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return chat_completion.choices[0].message.content


async def llm_call_async(prompt: str, model: str = "gpt-4o-mini") -> str:
    messages = [{"role": "user", "content": prompt}]
    chat_completion = await async_client.chat.completions.create(
        model=model,
        messages=messages,
    )
    print(model, "완료")
    return chat_completion.choices[0].message.content


async def llm_search_async(prompt: str, model: str = "gpt-4.1") -> str:
    response = await async_client.responses.create(
        model=model,
        input=prompt,
        tools=[{"type": "web_search_preview"}],
    )
    return response.output_text


# ── 메시지 출력 헬퍼 ──────────────────────────────────────────────

_OPENAI_ROLE_MAP = {
    "system": "system",
    "user": "human",
    "assistant": "ai",
    "tool": "tool",
    "function": "function",
}

_ROLE_STYLES = {
    "system": {"label": "System", "bg": "#f0f0f0", "border": "#999", "color": "#333"},
    "human": {"label": "User", "bg": "#dcf8c6", "border": "#82c45e", "color": "#1a3a0a"},
    "ai": {"label": "Assistant", "bg": "#e3f2fd", "border": "#64b5f6", "color": "#0d2137"},
    "tool": {"label": "Tool", "bg": "#fff3e0", "border": "#ffb74d", "color": "#3e2700"},
    "function": {"label": "Function", "bg": "#fce4ec", "border": "#ef9a9a", "color": "#3e0a0a"},
}

_DEFAULT_STYLE = {"label": "Unknown", "bg": "#f5f5f5", "border": "#bbb", "color": "#333"}


def _render_block(role_key: str, content: str, extra: str = "") -> str:
    style = _ROLE_STYLES.get(role_key, _DEFAULT_STYLE)
    content_html = content.replace("\n", "<br>")
    return (
        f'<div style="margin:8px 0;padding:10px 14px;border-left:4px solid {style["border"]};'
        f'background:{style["bg"]};border-radius:6px;font-family:sans-serif;">'
        f'<div style="font-weight:700;font-size:0.8em;color:{style["border"]};'
        f'margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">{style["label"]}</div>'
        f'<div style="color:{style["color"]};line-height:1.5;white-space:pre-wrap;">{content_html}</div>'
        f"{extra}</div>"
    )


def _render_openai(msg: dict) -> str:
    role_key = _OPENAI_ROLE_MAP.get(msg.get("role", ""), "")
    content = msg.get("content", "") or ""

    extra = ""
    tool_calls = msg.get("tool_calls")
    if tool_calls:
        parts = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            parts.append(f'<code>{fn.get("name", "")}({fn.get("arguments", "")})</code>')
        extra = (
            '<div style="margin-top:6px;padding:6px 8px;background:rgba(0,0,0,0.04);'
            f'border-radius:4px;font-size:0.85em;">Tool Calls: {"  ".join(parts)}</div>'
        )

    return _render_block(role_key, content, extra)


def print_openai_messages(messages: list[dict]) -> None:
    display(HTML("".join(_render_openai(m) for m in messages)))


def print_openai_message(message: dict) -> None:
    display(HTML(_render_openai(message)))