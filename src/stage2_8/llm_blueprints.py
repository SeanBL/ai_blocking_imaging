# src/stage2_8/llm_blueprints.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .logger import logger
from .llm_call import call_llm_json
from .prompts_blueprints import PASS2_SYSTEM_PROMPT, build_pass2_user_prompt
from .validate_blueprints_roles import validate_pass2_blueprints


def _extract_role_expectations(
    *,
    inline_direct_questions: Optional[int],
    final_direct_questions: Optional[int],
    module_application_questions: int,
    total_questions: Optional[int],
) -> Dict[str, int]:
    """
    Resolve expected role counts WITHOUT hardcoding.

    Preferred:
      - inline_direct_questions, final_direct_questions (from [[QUIZ:...:QUESTIONS=a,b]])
      - module_application_questions defaults to 1

    Backward-compat:
      - If only total_questions is provided, we cannot reliably infer inline vs final split.
        In that case we validate only total count + per-item constraints that don't require split.
    """
    expected: Dict[str, int] = {
        "inline_direct": 0,
        "final_direct": 0,
        "module_application": max(0, int(module_application_questions)),
        "expected_total": 0,
        "strict_role_counts": 0,  # 1 = enforce exact per-role counts; 0 = don't enforce split
    }

    if inline_direct_questions is not None and final_direct_questions is not None:
        expected["inline_direct"] = int(inline_direct_questions)
        expected["final_direct"] = int(final_direct_questions)
        expected["expected_total"] = (
            expected["inline_direct"]
            + expected["final_direct"]
            + expected["module_application"]
        )
        expected["strict_role_counts"] = 1
        return expected

    # Fallback: total_questions provided (legacy path)
    if total_questions is not None:
        expected["expected_total"] = int(total_questions)
        expected["strict_role_counts"] = 0
        return expected

    raise ValueError(
        "Must provide either (inline_direct_questions and final_direct_questions) "
        "or total_questions."
    )


def _log_role_summary(
    *,
    quiz_id: int,
    role_counts: Dict[str, int],
    expected: Dict[str, int],
) -> None:
    logger.info(
        f"[Pass2] Blueprint role counts — quiz_id={quiz_id} "
        f"counts={role_counts} expected="
        f"{{'inline_direct': {expected.get('inline_direct')}, "
        f"'final_direct': {expected.get('final_direct')}, "
        f"'module_application': {expected.get('module_application')}, "
        f"'total': {expected.get('expected_total')}}} "
        f"(strict_role_counts={bool(expected.get('strict_role_counts'))})"
    )


def _rebalance_blueprint_roles(
    *,
    blueprints: List[Dict[str, Any]],
    expected: Dict[str, int],
) -> bool:
    """
    Deterministically rebalance blueprint roles to satisfy exact role counts.
    Returns True if any changes were made.

    IMPORTANT:
    - We must keep role-specific constraints consistent after changing quiz_role.
      validate_pass2_blueprints enforces, for example:
        - final_direct => question_style='direct' and cognitive_level in {'recall','interpret'}
    """

    def normalize_for_role(bp: Dict[str, Any], role: str) -> None:
        """
        Enforce the minimal role-specific invariants required by validate_pass2_blueprints.
        Only touches fields that the validator ties directly to the role.
        """
        if role in ("inline_direct", "final_direct"):
            # Direct roles must be direct + lower cognitive load
            bp["question_style"] = "direct"
            # Prefer existing allowed value if already compliant; else default deterministically
            cl = bp.get("cognitive_level")
            if cl not in ("recall", "interpret"):
                bp["cognitive_level"] = "recall"
        elif role == "module_application":
            # Keep application as-is; don't force anything extra here
            # (validator rules for module_application may exist elsewhere)
            pass

    def set_role(bp: Dict[str, Any], new_role: str) -> None:
        bp["quiz_role"] = new_role
        normalize_for_role(bp, new_role)

    def count_roles() -> Dict[str, int]:
        counts = {"inline_direct": 0, "final_direct": 0, "module_application": 0}
        for bp in blueprints:
            role = bp.get("quiz_role")
            if role in counts:
                counts[role] += 1
        return counts

    changed = False
    counts = count_roles()

    # -------------------------------------------------
    # If module_application is NOT allowed, downgrade all to final_direct
    # -------------------------------------------------
    if expected.get("module_application", 0) == 0 and counts["module_application"] > 0:
        for bp in blueprints:
            if bp.get("quiz_role") == "module_application":
                set_role(bp, "final_direct")
                changed = True
        counts = count_roles()

    # -------------------------------------------------
    # Rebalance inline_direct <-> final_direct
    # -------------------------------------------------

    while counts["inline_direct"] > expected["inline_direct"]:
        for bp in blueprints:
            if bp.get("quiz_role") == "inline_direct":
                set_role(bp, "final_direct")
                counts["inline_direct"] -= 1
                counts["final_direct"] += 1
                changed = True
                break

    while counts["final_direct"] > expected["final_direct"]:
        for bp in blueprints:
            if bp.get("quiz_role") == "final_direct":
                set_role(bp, "inline_direct")
                counts["final_direct"] -= 1
                counts["inline_direct"] += 1
                changed = True
                break

    return changed

def generate_question_blueprints(
    *,
    quiz_id: int,
    source_claims_payload: Dict[str, Any],
    # ✅ NEW (preferred): derived from the Word marker [[QUIZ:...:QUESTIONS=a,b]]
    inline_direct_questions: Optional[int] = None,
    final_direct_questions: Optional[int] = None,
    module_application_questions: int = 1,
    # ✅ Legacy support (avoid breaking callers immediately)
    total_questions: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pass 2: Produce assessment blueprints only (no final wording).

    Updated behavior:
      - No hardcoded counts.
      - Prefer passing inline_direct_questions and final_direct_questions from the
        parsed marker [[QUIZ:...:QUESTIONS=a,b]].
      - Always expects module_application_questions (default 1).
      - Validates role counts + role constraints via validate_pass2_blueprints().
    """

    expected = _extract_role_expectations(
        inline_direct_questions=inline_direct_questions,
        final_direct_questions=final_direct_questions,
        module_application_questions=module_application_questions,
        total_questions=total_questions,
    )

    # If caller still passes total_questions while also passing split counts, we ignore total_questions.
    if expected["strict_role_counts"] and total_questions is not None:
        logger.warning(
            f"[Pass2] quiz_id={quiz_id} received total_questions={total_questions} "
            f"but using split counts inline={inline_direct_questions}, final={final_direct_questions} "
            f"+ module_application={module_application_questions} => expected_total={expected['expected_total']}"
        )

    resolved_total_questions = expected["expected_total"]

    logger.warning(
        f"[Pass2] generate_question_blueprints CALLED — "
        f"quiz_id={quiz_id}, total_questions={resolved_total_questions}, "
        f"inline_direct={inline_direct_questions}, final_direct={final_direct_questions}, "
        f"module_application={module_application_questions}, "
        f"claims={len(source_claims_payload.get('source_claims', []))}"
    )

    user_prompt = build_pass2_user_prompt(
        quiz_id=quiz_id,
        total_questions=resolved_total_questions,
        pass1_claims=source_claims_payload,
    )

    prompt = PASS2_SYSTEM_PROMPT + "\n\n" + user_prompt

    logger.info(
        f"[Pass2] Blueprint LLM invoked — quiz_id={quiz_id}, total_questions={resolved_total_questions}"
    )

    parsed = call_llm_json(
        prompt=prompt,
        stage_tag="Stage 2.8 Blueprint",
    )

    if not isinstance(parsed, dict):
        raise ValueError("Blueprint output is not a JSON object")

    if "blueprints" not in parsed or not isinstance(parsed["blueprints"], list):
        raise ValueError("Blueprint output missing blueprints list")

    blueprints: List[Dict[str, Any]] = parsed["blueprints"]

    # ---- Strict validation (roles + constraints) ----
    if expected["strict_role_counts"]:
        result = validate_pass2_blueprints(
            payload={"quiz_id": quiz_id, "blueprints": blueprints},
            expected_inline_direct=expected["inline_direct"],
            expected_final_direct=expected["final_direct"],
            expected_module_application=expected["module_application"],
            expected_total=expected["expected_total"],
        )
    else:
        result = validate_pass2_blueprints(
            payload={"quiz_id": quiz_id, "blueprints": blueprints},
            expected_inline_direct=0,
            expected_final_direct=0,
            expected_module_application=expected["module_application"],
            expected_total=expected["expected_total"],
        )

    _log_role_summary(quiz_id=quiz_id, role_counts=result.role_counts, expected=expected)

    if not result.ok and expected["strict_role_counts"]:
        logger.warning(
            f"[Pass2] Attempting deterministic role rebalance — quiz_id={quiz_id}"
        )

        repaired = _rebalance_blueprint_roles(
            blueprints=blueprints,
            expected=expected,
        )

        if repaired:
            # Re-validate after repair
            result = validate_pass2_blueprints(
                payload={"quiz_id": quiz_id, "blueprints": blueprints},
                expected_inline_direct=expected["inline_direct"],
                expected_final_direct=expected["final_direct"],
                expected_module_application=expected["module_application"],
                expected_total=expected["expected_total"],
            )

            _log_role_summary(
                quiz_id=quiz_id,
                role_counts=result.role_counts,
                expected=expected,
            )

            if result.ok:
                logger.info(
                    f"[Pass2] Blueprint role rebalance succeeded — quiz_id={quiz_id}"
                )
            else:
                logger.error(
                    f"[Pass2] Role rebalance failed — quiz_id={quiz_id}"
                )

        if not result.ok:
            top_errors = result.errors[:10]
            raise ValueError(
                f"Pass2 blueprint validation failed for quiz_id={quiz_id}. "
                f"Top errors: {top_errors}"
            )

    # Ensure quiz_id is set (and authoritative)
    parsed["quiz_id"] = quiz_id
    return parsed



