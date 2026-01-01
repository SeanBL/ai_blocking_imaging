from __future__ import annotations

import json
from typing import Any, Dict, List

from .review_prompts import REVIEW_SYSTEM_PROMPT
from .logger import logger
from .llm_call import call_llm_json


def review_quiz_quality(
    *,
    quiz_payload: Dict[str, Any],
    source_paragraphs: List[str],
) -> Dict[str, Any]:
    """
    Reviewer LLM:
    - Evaluates quiz quality
    - Returns PASS / FAIL with suggested fixes
    """

    quiz_id = quiz_payload.get("quiz_id", "UNKNOWN")

    logger.info(
        f"Reviewer LLM invoked — quiz_id={quiz_id}"
    )

    user_prompt = {
        "quiz": quiz_payload,
        "source_text": source_paragraphs,
    }

    prompt = (
        REVIEW_SYSTEM_PROMPT
        + "\n\n"
        + json.dumps(user_prompt, ensure_ascii=False, indent=2)
    )

    result = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Reviewer",
    )

    status = result.get("status", "UNKNOWN")

    logger.info(
        f"Reviewer LLM completed — quiz_id={quiz_id}, status={status}"
    )

    return result
