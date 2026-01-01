# src/stage2_8/apply_reviewer_fixes.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple

from .logger import logger


def _index_questions_by_id(quiz_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    questions = quiz_payload.get("questions", [])
    if not isinstance(questions, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for q in questions:
        if isinstance(q, dict):
            qid = q.get("question_id")
            if isinstance(qid, str):
                out[qid] = q
    return out


def _apply_fix_patch_to_question(question: Dict[str, Any], patch: Dict[str, Any]) -> bool:
    """
    Apply a reviewer suggested_fixes patch to a single question in-place.
    Returns True if something was applied.
    """
    applied = False

    if not isinstance(patch, dict):
        return False

    qtype = question.get("type")

    # -------------------------------------------------
    # correct_answer
    # -------------------------------------------------
    if "correct_answer" in patch:
        ca = patch["correct_answer"]

        # -------- TRUE / FALSE --------
        if qtype == "true_false":
            if isinstance(ca, str):
                ca = ca.lower().strip()
                if ca == "true":
                    ca = True
                elif ca == "false":
                    ca = False
                else:
                    return False

            if isinstance(ca, bool):
                question["correct_answer"] = ca
                applied = True
            return applied

        # -------- MCQ --------
        if qtype == "mcq" and isinstance(ca, str):
            ca = ca.strip()

            # Clean A/B/C/D
            if ca in ("A", "B", "C", "D"):
                question["correct_answer"] = ca
                applied = True
                return applied

            # Reviewer-style: "B (explanation...)"
            if ca and ca[0] in ("A", "B", "C", "D"):
                letter = ca[0]
                explanation = ca[1:].strip(" ():-")

                question["correct_answer"] = letter
                applied = True

                if explanation:
                    existing = question.get("rationale", "")
                    question["rationale"] = (
                        f"{existing} {explanation}".strip()
                    )

                return applied

            # Invalid MCQ correct_answer → ignore
            return False

    # -------------------------------------------------
    # prompt
    # -------------------------------------------------
    if "prompt" in patch and isinstance(patch["prompt"], str) and patch["prompt"].strip():
        question["prompt"] = patch["prompt"].strip()
        applied = True

    # -------------------------------------------------
    # rationale
    # -------------------------------------------------
    if "rationale" in patch and isinstance(patch["rationale"], str) and patch["rationale"].strip():
        question["rationale"] = patch["rationale"].strip()
        applied = True

    # -------------------------------------------------
    # options
    # -------------------------------------------------
    if "options" in patch and isinstance(patch["options"], dict):
        if not isinstance(question.get("options"), dict):
            question["options"] = {}

        for k, v in patch["options"].items():
            if k in ("A", "B", "C", "D") and isinstance(v, str) and v.strip():
                question["options"][k] = v.strip()
                applied = True

    return applied


def apply_reviewer_fixes(
    *,
    quiz_payload: Dict[str, Any],
    review_result: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """
    Deterministically apply reviewer suggested fixes.

    Returns:
      (fixed_quiz_payload, applied_fix_count)
    """

    fixed = deepcopy(quiz_payload)
    quiz_id = fixed.get("quiz_id", "UNKNOWN")

    issues = review_result.get("issues", [])
    if not isinstance(issues, list) or not issues:
        logger.info(f"Deterministic fixer: no issues to apply — quiz_id={quiz_id}")
        return fixed, 0

    qmap = _index_questions_by_id(fixed)

    applied_count = 0
    skipped: List[str] = []

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        qid = issue.get("question_id")
        patch = issue.get("suggested_fixes")

        if not isinstance(qid, str) or qid not in qmap:
            skipped.append(str(qid))
            continue

        if not isinstance(patch, dict) or not patch:
            skipped.append(qid)
            continue

        did_apply = _apply_fix_patch_to_question(qmap[qid], patch)
        if did_apply:
            applied_count += 1
        else:
            skipped.append(qid)

    logger.info(
        f"Deterministic fixer applied — quiz_id={quiz_id}, applied={applied_count}, skipped={len(skipped)}"
    )

    if skipped:
        logger.warning(
            f"Deterministic fixer skipped issues — quiz_id={quiz_id}, skipped={skipped}"
        )

    return fixed, applied_count
