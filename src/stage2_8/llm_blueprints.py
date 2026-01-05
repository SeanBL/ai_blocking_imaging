# src/stage2_8/llm_blueprints.py
from __future__ import annotations

from typing import Any, Dict, List

from .logger import logger
from .llm_call import call_llm_json
from .prompts_blueprints import PASS2_SYSTEM_PROMPT, build_pass2_user_prompt


def _validate_blueprint_styles(
    blueprints: List[Dict[str, Any]],
    quiz_id: int,
) -> None:
    """
    Enforce presence and balance of question_style.
    """

    scenario_count = 0
    direct_count = 0

    for idx, bp in enumerate(blueprints, start=1):
        style = bp.get("question_style")

        if style not in ("scenario", "direct"):
            raise ValueError(
                f"Quiz {quiz_id} blueprint q{idx} has invalid or missing "
                f"question_style: {style}"
            )

        if style == "scenario":
            scenario_count += 1
        else:
            direct_count += 1

    total = len(blueprints)
    if total == 0:
        raise ValueError(f"Quiz {quiz_id} returned zero blueprints")

    scenario_ratio = scenario_count / total

    logger.info(
        f"[Pass2] Quiz {quiz_id} blueprint styles — "
        f"scenario={scenario_count}, direct={direct_count}"
    )

    # Soft enforcement: allow reasonable variance
    if not (0.2 <= scenario_ratio <= 0.6):
        raise ValueError(
            f"Quiz {quiz_id} blueprint question_style imbalance: "
            f"{scenario_count}/{total} scenario "
            f"(expected ~40%)"
        )


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
        f"[V2] Pass 2 Blueprint LLM invoked — quiz_id={quiz_id}, "
        f"total_questions={total_questions}"
    )

    parsed = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Blueprint",
    )

    if "blueprints" not in parsed or not isinstance(parsed["blueprints"], list):
        raise ValueError("Blueprint output missing blueprints list")

    # 🔒 NEW: validate question_style presence + balance
    _validate_blueprint_styles(parsed["blueprints"], quiz_id)

    parsed["quiz_id"] = quiz_id
    return parsed


