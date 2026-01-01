# src/stage2_8/llm_quiz.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .logger import logger
from .llm_call import call_llm_json

def choose_tf_mcq_split(total_questions: int) -> Dict[str, int]:
    """
    Conditional T/F strategy (Option B):

    - Prefer 1 True/False question if total_questions >= 3
    - Otherwise, use all MCQ
    - ALWAYS return both tf_count and mcq_count
    """
    if total_questions < 1:
        raise ValueError("total_questions must be >= 1")

    if total_questions >= 3:
        tf_count = 1
    else:
        tf_count = 0

    mcq_count = total_questions - tf_count

    return {
        "tf_count": tf_count,
        "mcq_count": mcq_count,
    }

def generate_quiz_questions(
    *,
    quiz_id: int,
    total_questions: int,
    source_paragraphs: List[str],
) -> Dict[str, Any]:
    """
    Returns parsed JSON object matching the schema defined in prompts.py.

    IMPORTANT:
    - This function does NOT insert slides.
    - source_paragraphs must contain ALL panel text between
      the quiz start and insertion markers.
    """
    split = choose_tf_mcq_split(total_questions)

    user_prompt = build_user_prompt(
        quiz_id=quiz_id,
        total_questions=total_questions,
        tf_count=split["tf_count"],
        mcq_count=split["mcq_count"],
        source_paragraphs=source_paragraphs,
    )

    logger.info(
        f"Author LLM invoked — quiz_id={quiz_id}, total_questions={total_questions}"
    )

    prompt = SYSTEM_PROMPT + "\n\n" + user_prompt

    parsed = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Author",
    )

    logger.info(
        f"Author LLM completed — quiz_id={quiz_id}"
    )

    return parsed
