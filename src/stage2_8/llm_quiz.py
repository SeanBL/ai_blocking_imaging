# src/stage2_8/llm_quiz.py
from __future__ import annotations

from typing import Any, Dict, List

from .logger import logger
from .llm_call import call_llm_json

from .llm_concepts import generate_source_claims
from .llm_blueprints import generate_question_blueprints

from .prompts_author_v2 import (
    AUTHOR_V2_SYSTEM_PROMPT,
    build_author_v2_user_prompt,
)

# --------------------------------------------------
# 🚨 HARD INVARIANT: AUTHOR V2 ONLY
# --------------------------------------------------
# This module MUST NOT import or reference:
# - prompts.py (v1)
# - SYSTEM_PROMPT (v1)
# - build_user_prompt
# - config flags
# Any violation is a pipeline error by design.
# --------------------------------------------------


def generate_quiz_questions(
    *,
    quiz_id: int,
    total_questions: int,
    source_paragraphs: List[str],
) -> Dict[str, Any]:
    """
    Gold-standard 3-pass quiz generation (V2 ONLY):
      Pass 1: Source claims (source-locked)
      Pass 2: Question blueprints (assessment design)
      Pass 3: Author v2 writes final items from blueprints
    """

    logger.info(
        f"[V2] 3-pass quiz generation starting — quiz_id={quiz_id}, total_questions={total_questions}"
    )

    # ----------------------------
    # PASS 1 — SOURCE CLAIMS
    # ----------------------------
    claims_payload = generate_source_claims(
        quiz_id=quiz_id,
        source_paragraphs=source_paragraphs,
        concept_count=max(6, total_questions + 2),
    )

    source_claims = claims_payload.get("source_claims", [])
    if not source_claims:
        raise ValueError(
            f"[V2] No source claims generated — quiz_id={quiz_id}"
        )

    logger.info(
        f"[V2] Pass 1 complete — quiz_id={quiz_id}, claims={len(source_claims)}"
    )

    # ----------------------------
    # PASS 2 — BLUEPRINTS
    # ----------------------------
    trimmed_claims = dict(claims_payload)
    trimmed_claims["source_claims"] = trimmed_claims["source_claims"][:total_questions + 2]

    blueprints_payload = generate_question_blueprints(
        quiz_id=quiz_id,
        total_questions=total_questions,
        source_claims_payload=trimmed_claims,
    )

    blueprints = blueprints_payload.get("blueprints", [])
    if len(blueprints) != total_questions:
        raise ValueError(
            f"[V2] Blueprint count mismatch — quiz_id={quiz_id}, "
            f"expected={total_questions}, actual={len(blueprints)}"
        )

    logger.info(
        f"[V2] Pass 2 complete — quiz_id={quiz_id}, blueprints={len(blueprints)}"
    )

    # ----------------------------
    # PASS 3 — AUTHOR V2 WRITING
    # ----------------------------
    user_prompt = build_author_v2_user_prompt(
        quiz_id=quiz_id,
        source_paragraphs=source_paragraphs,
        source_claims=source_claims,
        blueprints=blueprints,
    )

    prompt = AUTHOR_V2_SYSTEM_PROMPT + "\n\n" + user_prompt

    logger.info(
        f"[V2] Pass 3 (Author v2) invoked — quiz_id={quiz_id}, total_questions={total_questions}"
    )

    parsed = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Author V2",
    )

    parsed["quiz_id"] = quiz_id

    logger.info(
        f"[V2] Author v2 completed — quiz_id={quiz_id}"
    )

    return parsed


