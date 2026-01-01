from __future__ import annotations

import json
from typing import Dict, Any

from .editor_prompts import EDITOR_SYSTEM_PROMPT
from .llm_call import call_llm_json
from .logger import logger


def run_editor_llm(
    *,
    quiz_payload: Dict[str, Any],
    review_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Uses an LLM to fix non-deterministic quiz issues (e.g., MCQ ambiguity).

    IMPORTANT:
    - Editor is NOT allowed to change quiz_id or question ordering
    - Invariants are re-injected after LLM call
    """

    quiz_id = quiz_payload.get("quiz_id")

    if quiz_id is None:
        raise ValueError("Editor invoked with missing quiz_id")

    prompt_payload = {
        "quiz": quiz_payload,
        "review_issues": review_result.get("issues", []),
    }

    logger.warning(
        f"Editor LLM invoked — quiz_id={quiz_id}, issues={len(prompt_payload['review_issues'])}"
    )

    prompt = (
        EDITOR_SYSTEM_PROMPT
        + "\n\n"
        + json.dumps(prompt_payload, ensure_ascii=False)
    )

    edited = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Editor",
    )

    # -------------------------------------------------
    # 🔒 ENFORCE PIPELINE INVARIANTS
    # -------------------------------------------------
    edited["quiz_id"] = quiz_id

    # Ensure questions list exists
    if "questions" not in edited or not isinstance(edited["questions"], list):
        raise ValueError("Editor output missing valid questions list")

    # Ensure question_id order is preserved
    for idx, q in enumerate(edited["questions"], start=1):
        q["question_id"] = f"q{idx}"

    logger.info(
        f"Editor LLM completed — quiz_id={quiz_id}"
    )

    return edited
