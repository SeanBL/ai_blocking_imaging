from __future__ import annotations

import json
from typing import Any, Dict, List

from .distractor_review_prompts import DISTRACTOR_REVIEW_SYSTEM_PROMPT
from .llm_call import call_llm_json
from .logger import logger


def distractor_review(
    *,
    quiz_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Distractor Quality Reviewer

    Evaluates MCQ distractor quality only:
    - weak distractors
    - conceptual alignment
    - option parallelism
    - trivial elimination
    """

    logger.warning("===== DISTRACTOR REVIEWER EXECUTED =====")
    quiz_id = quiz_payload.get("quiz_id", "UNKNOWN")

    logger.info(f"Distractor reviewer invoked — quiz_id={quiz_id}")

    # -------------------------------------------------
    # Filter MCQ questions only
    # -------------------------------------------------
    questions: List[Dict[str, Any]] = quiz_payload.get("questions", [])

    mcq_questions = [
        q for q in questions
        if isinstance(q, dict) and q.get("type") == "mcq"
    ]

    # If no MCQs, skip reviewer
    if not mcq_questions:
        logger.info(f"No MCQ questions to review — quiz_id={quiz_id}")
        return {"status": "PASS", "issues": []}

    filtered_payload = {
        "quiz_id": quiz_id,
        "questions": mcq_questions,
    }

    # -------------------------------------------------
    # Build prompt
    # -------------------------------------------------
    user_prompt = {
        "quiz": filtered_payload
    }

    prompt = (
        DISTRACTOR_REVIEW_SYSTEM_PROMPT
        + "\n\n"
        + json.dumps(user_prompt, ensure_ascii=False, indent=2)
    )

    # -------------------------------------------------
    # Call LLM reviewer
    # -------------------------------------------------
    result = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Distractor Reviewer",
    )

    status = result.get("status", "UNKNOWN")

    logger.info(
        f"Distractor reviewer completed — quiz_id={quiz_id}, status={status}"
    )

    return result