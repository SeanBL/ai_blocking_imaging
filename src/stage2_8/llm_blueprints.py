# src/stage2_8/llm_blueprints.py
from __future__ import annotations

from typing import Any, Dict

from .logger import logger
from .llm_call import call_llm_json
from .prompts_blueprints import PASS2_SYSTEM_PROMPT, build_pass2_user_prompt


def generate_question_blueprints(
    *,
    quiz_id: int,
    total_questions: int,
    source_claims_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Pass 2: Produce assessment blueprints only (no final wording).
    """

    logger.warning(
        f"[TEST1] Pass2 generate_question_blueprints CALLED — "
        f"quiz_id={quiz_id}, total_questions={total_questions}, "
        f"claims={len(source_claims_payload.get('source_claims', []))}"
    )

    user_prompt = build_pass2_user_prompt(
        quiz_id=quiz_id,
        total_questions=total_questions,
        pass1_claims=source_claims_payload,
    )

    prompt = PASS2_SYSTEM_PROMPT + "\n\n" + user_prompt

    logger.info(
        f"[V2] Pass 2 Blueprint LLM invoked — quiz_id={quiz_id}, total_questions={total_questions}"
    )

    parsed = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Blueprint",
    )

    if "blueprints" not in parsed or not isinstance(parsed["blueprints"], list):
        raise ValueError("Blueprint output missing blueprints list")

    parsed["quiz_id"] = quiz_id
    return parsed

