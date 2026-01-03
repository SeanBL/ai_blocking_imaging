# src/stage2_8/llm_concepts.py
from __future__ import annotations

from typing import Any, Dict, List

from .logger import logger
from .llm_call import call_llm_json
from .prompts_concepts import PASS1_SYSTEM_PROMPT, build_pass1_user_prompt


def generate_source_claims(
    *,
    quiz_id: int,
    source_paragraphs: List[str],
    concept_count: int = 8,
) -> Dict[str, Any]:
    """
    Pass 1: Produce source-locked claims, allowable inferences,
    and common misconceptions based strictly on the source text.
    """

    logger.warning(
        f"[TEST1] Pass 1 generate_source_claims CALLED — "
        f"quiz_id={quiz_id}, paragraphs={len(source_paragraphs)}"
    )

    user_prompt = build_pass1_user_prompt(
        quiz_id=quiz_id,
        source_paragraphs=source_paragraphs,
    )

    prompt = PASS1_SYSTEM_PROMPT + "\n\n" + user_prompt

    logger.info(
        f"[V2] Pass 1 Concept LLM invoked — quiz_id={quiz_id}, concept_count={concept_count}"
    )

    parsed = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Pass1 (Concepts)",
        max_tokens=2200,   # ← KEY FIX
    )

    # Minimal sanity checks (strict but not overbearing)
    if "source_claims" not in parsed or not isinstance(parsed["source_claims"], list):
        raise ValueError("Pass 1 output missing required 'source_claims' list")

    parsed["quiz_id"] = quiz_id
    return parsed

