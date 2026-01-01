from __future__ import annotations

import json
from typing import Any, Dict

from .fix_prompts import FIX_SYSTEM_PROMPT
from .logger import logger
from .llm_call import call_llm_json



def apply_quiz_fixes(
    *,
    quiz_payload: Dict[str, Any],
    review_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Editor LLM:
    - Applies ONLY reviewer-suggested fixes
    - Does not add, remove, or reinterpret content
    """

    quiz_id = quiz_payload.get("quiz_id", "UNKNOWN")
    issues = review_result.get("issues", [])
    issue_count = len(issues)

    logger.info(
        f"Editor LLM invoked — quiz_id={quiz_id}, issues={issue_count}"
    )

    user_prompt = {
        "quiz": quiz_payload,
        "review_issues": issues,
    }

    prompt = FIX_SYSTEM_PROMPT + "\n\n" + json.dumps(user_prompt)

    fixed_quiz = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Editor",
    )

    # 🔒 HARD GUARANTEE: preserve quiz_id
    fixed_quiz["quiz_id"] = quiz_payload.get("quiz_id")

    if not isinstance(fixed_quiz.get("questions"), list):
        fixed_quiz["questions"] = quiz_payload.get("questions", [])

    logger.info(
        f"Editor LLM completed — quiz_id={quiz_id}"
    )

    return fixed_quiz
