from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

from openai import OpenAI

from lib.phase1 import run_jd_workers
from lib.phase2 import (
    aggregate_phase2_results,
    analyze_and_match_essay,
    build_question_context,
    classify_personal_statement_sections,
)
from lib.phase3 import generate_interview_questions
from lib.phase4 import get_passed_final_questions, optimize_questions_with_retries
from lib.phase5 import format_phase5_output, phase5
from llm_utils import llm_call_async, llm_search_async


async def default_phase1_llm_async_fn(prompt: str, model: str) -> str:
    if model == "gpt-4.1":
        return await llm_search_async(prompt, model=model)
    return await llm_call_async(prompt, model=model)


async def run_interview_question_pipeline_async(
    jd_text: str,
    essay_text: str,
    *,
    client: Optional[OpenAI] = None,
    phase1_llm_async_fn: Optional[Callable[[str, str], Any]] = None,
    analysis_model: str = "gpt-4o-mini",
    phase3_orchestrator_model: str = "gpt-4o",
    phase3_worker_model: str = "gpt-4o",
    question_max_retries: int = 3,
) -> Dict[str, Any]:
    client = client or OpenAI()
    phase1_llm_async_fn = phase1_llm_async_fn or default_phase1_llm_async_fn

    phase1_results = await run_jd_workers(jd_text, phase1_llm_async_fn)
    personal_statement_list = classify_personal_statement_sections(essay_text)

    analyzed_result = analyze_and_match_essay(
        js_list=phase1_results,
        personal_statement_list=personal_statement_list,
        client=client,
        model=analysis_model,
    )
    context_result = build_question_context(
        analyzed_result=analyzed_result,
        client=client,
        model=analysis_model,
    )
    phase2_result = aggregate_phase2_results(
        js_list=phase1_results,
        contextualized_result=context_result,
        client=client,
        model=analysis_model,
    )

    phase3_result = generate_interview_questions(
        phase2_result,
        client=client,
        orchestrator_model=phase3_orchestrator_model,
        worker_model=phase3_worker_model,
    )

    job_category = phase2_result.get("target", {}).get("role", "백엔드개발자")
    phase4_results = optimize_questions_with_retries(
        phase3_result["questions"],
        job_category,
        max_retries=question_max_retries,
    )
    phase4_pass_questions = get_passed_final_questions(phase4_results)

    phase5_result = phase5(phase4_pass_questions, job_category)

    return {
        "phase1": phase1_results,
        "personal_statement_list": personal_statement_list,
        "phase2_analysis": analyzed_result,
        "phase2_context": context_result,
        "phase2": phase2_result,
        "phase3": phase3_result,
        "phase4": phase4_results,
        "phase4_pass_questions": phase4_pass_questions,
        "phase5": phase5_result,
        "phase5_report": format_phase5_output(phase5_result),
    }


def run_interview_question_pipeline(
    jd_text: str,
    essay_text: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    return asyncio.run(run_interview_question_pipeline_async(jd_text, essay_text, **kwargs))

