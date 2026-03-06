from __future__ import annotations

from typing import Dict, List, Any, Set

from .logger import logger
from .llm_quiz import generate_quiz_questions
from .validate_quiz_output import validate_quiz_payload
from .quiz_quality_review import review_quiz_quality
from .apply_reviewer_fixes import apply_reviewer_fixes
from .editor_llm import run_editor_llm_single_question
from .distractor_review import distractor_review
from .duplicate_correct_guard import detect_duplicate_correct_answers


REVIEWERS = [
    ("clinical_review", review_quiz_quality),
    ("distractor_review", distractor_review),
]

# Must match what validate_quiz_payload expects to exist per question
REQUIRED_QUESTION_KEYS: Set[str] = {
    "question_id",
    "type",
    "prompt",
    "correct_answer",
    "rationale",
    "quiz_role",
    "question_style",
    "cognitive_level",
    "claim_ids",
    # "options" is conditionally required (mcq) and forbidden (true_false),
    # so we do NOT include it in this unconditional set.
}


def run_quiz_pipeline(
    *,
    quiz_id: int,
    inline_direct_questions: int,
    final_direct_questions: int,
    module_application_questions: int,
    source_paragraphs: List[str],
) -> Dict[str, Any]:
    """
    Runs Stage 2.8 quiz generation with:
    Author → Reviewer → Deterministic Fixer → Single-question Editor (one pass) → Re-review → Hard stop
    """

    logger.info(f"Stage 2.8 quiz pipeline started — quiz_id={quiz_id}")

    # -------------------------------------------------
    # Question count invariants
    # -------------------------------------------------
    total_questions = (
        inline_direct_questions
        + final_direct_questions
        + module_application_questions
    )

    max_allowed = max(1, len(source_paragraphs) * 2)
    if total_questions > max_allowed:
        raise ValueError(
            f"Requested quiz questions exceed content capacity — "
            f"quiz_id={quiz_id}, requested={total_questions}, allowed={max_allowed}"
        )

    # -------------------------------------------------
    # 1) AUTHOR
    # -------------------------------------------------
    quiz = generate_quiz_questions(
        quiz_id=quiz_id,
        source_paragraphs=source_paragraphs,
        inline_direct_questions=inline_direct_questions,
        final_direct_questions=final_direct_questions,
        module_application_questions=module_application_questions,
    )

    # -------------------------------------------------
    # 1.5) DUPLICATE CORRECT ANSWER GUARD
    # -------------------------------------------------

    dup_issues = detect_duplicate_correct_answers(quiz)

    if dup_issues:
        logger.warning(f"Duplicate-correct guard triggered — quiz_id={quiz_id}")

        review_stub = {
            "status": "FAIL",
            "issues": dup_issues
        }

        quiz, applied = apply_reviewer_fixes(
            quiz_payload=quiz,
            review_result=review_stub,
        )

        if applied > 0:
            validate_quiz_payload(
                payload=quiz,
                quiz_id=quiz_id,
                expected_count=total_questions,
            )

            logger.info(
                f"Duplicate guard fixes applied — quiz_id={quiz_id}, applied={applied}"
            )

    if "questions" not in quiz or not isinstance(quiz["questions"], list):
        raise ValueError(f"Author returned invalid quiz schema — quiz_id={quiz_id}")

    if len(quiz["questions"]) != total_questions:
        raise ValueError(
            f"Author question count mismatch — quiz_id={quiz_id}, "
            f"expected={total_questions}, actual={len(quiz['questions'])}"
        )

    validate_quiz_payload(
        payload=quiz,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )
    logger.info(f"Structural validation passed — quiz_id={quiz_id}")

    # -------------------------------------------------
    # 2) REVIEWERS PIPELINE
    # -------------------------------------------------
    collected_issues = []

    for name, reviewer in REVIEWERS:
        logger.warning(f"Running reviewer: {name}")

        if reviewer == review_quiz_quality:
            review = reviewer(
                quiz_payload=quiz,
                source_paragraphs=source_paragraphs,
            )
        else:
            review = reviewer(
                quiz_payload=quiz,
            )

        if review.get("status") == "PASS":
            continue

        issues = review.get("issues", []) or []
        collected_issues.extend(issues)

        logger.warning(f"{name} issues — quiz_id={quiz_id}: {issues}")

        quiz, applied = apply_reviewer_fixes(
            quiz_payload=quiz,
            review_result=review,
        )
        logger.warning(f"{name} issues — quiz_id={quiz_id}: {issues}")

        quiz, applied = apply_reviewer_fixes(
            quiz_payload=quiz,
            review_result=review,
        )

        validate_quiz_payload(
            payload=quiz,
            quiz_id=quiz_id,
            expected_count=total_questions,
        )

        if applied > 0:
            logger.info(
                f"{name} deterministic fixes applied — quiz_id={quiz_id}, applied={applied}"
            )

    # -------------------------------------------------
    # If reviewers produced fixes, continue with editor
    # -------------------------------------------------
    issues = collected_issues

    # -------------------------------------------------
    # 3) DETERMINISTIC FIXER
    # -------------------------------------------------
    fixed_quiz, applied = apply_reviewer_fixes(
        quiz_payload=quiz,
        review_result=review,
    )

    validate_quiz_payload(
        payload=fixed_quiz,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )

    if applied > 0:
        logger.info(f"Deterministic fixes applied — quiz_id={quiz_id}, applied={applied}")
        return fixed_quiz

    # -------------------------------------------------
    # 4) SINGLE-QUESTION EDITOR (ONE PASS ONLY)
    # -------------------------------------------------
    logger.warning(f"Invoking editor (single-question) — quiz_id={quiz_id}")

    for issue in issues:
        qid = issue.get("question_id")
        if not qid:
            continue

        idx = next(
            (i for i, q in enumerate(fixed_quiz["questions"]) if q.get("question_id") == qid),
            None,
        )
        if idx is None:
            raise RuntimeError(
                f"Reviewer referenced missing question_id={qid} — quiz_id={quiz_id}"
            )

        original_q = fixed_quiz["questions"][idx]

        # Editor returns a FULL question object (not a patch)
        edited = run_editor_llm_single_question(
            question=original_q,
            issue=issue,
            quiz_id=quiz_id,
        )

        if not isinstance(edited, dict):
            raise RuntimeError(
                f"Editor returned invalid question (non-dict) for {qid} — quiz_id={quiz_id}"
            )

        # Disallow quiz-level keys
        illegal_keys = {"quiz", "quiz_id", "questions"}
        bad = sorted(set(edited.keys()) & illegal_keys)
        if bad:
            raise RuntimeError(
                f"Editor returned illegal keys for {qid} — quiz_id={quiz_id}, keys={bad}"
            )

        # 🔒 RE-INJECT HARD INVARIANTS (editor may NOT change these)
        edited["question_id"] = original_q.get("question_id")
        edited["quiz_role"] = original_q.get("quiz_role")
        edited["question_style"] = original_q.get("question_style")
        edited["cognitive_level"] = original_q.get("cognitive_level")
        edited["claim_ids"] = original_q.get("claim_ids")

        # Required key presence check
        missing = REQUIRED_QUESTION_KEYS - set(edited.keys())
        if missing:
            raise RuntimeError(
                f"Editor returned incomplete question for {qid} — quiz_id={quiz_id}, missing={sorted(missing)}"
            )

        # Conditional schema checks (save time before full validator)
        qtype = edited.get("type")
        if qtype == "mcq":
            opts = edited.get("options")
            if not isinstance(opts, dict) or set(opts.keys()) != {"A", "B", "C", "D"}:
                raise RuntimeError(
                    f"Editor returned invalid MCQ options for {qid} — quiz_id={quiz_id}"
                )
            ca = edited.get("correct_answer")
            if ca not in ("A", "B", "C", "D"):
                raise RuntimeError(
                    f"Editor returned invalid MCQ correct_answer for {qid} — quiz_id={quiz_id}"
                )

        elif qtype == "true_false":
            if "options" in edited and edited["options"] is not None:
                raise RuntimeError(
                    f"Editor returned forbidden options for true_false {qid} — quiz_id={quiz_id}"
                )
            ca = edited.get("correct_answer")
            if ca not in (True, False):
                raise RuntimeError(
                    f"Editor returned invalid true_false correct_answer for {qid} — quiz_id={quiz_id}"
                )

        else:
            raise RuntimeError(
                f"Editor returned invalid question type for {qid} — quiz_id={quiz_id}, type={qtype}"
            )

        fixed_quiz["questions"][idx] = edited
        logger.info(f"Editor applied — quiz_id={quiz_id}, question={qid}")

    # -------------------------------------------------
    # Re-validate after editor
    # -------------------------------------------------
    validate_quiz_payload(
        payload=fixed_quiz,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )

    final_review = review_quiz_quality(
        quiz_payload=fixed_quiz,
        source_paragraphs=source_paragraphs,
    )

    if final_review.get("status") == "PASS":
        logger.info(f"Stage 2.8 quiz pipeline completed — quiz_id={quiz_id}")
        return fixed_quiz

    # -------------------------------------------------
    # 4.5) SELF-HEAL: APPLY REVIEWER FIXES ONCE, RE-REVIEW
    # -------------------------------------------------
    logger.warning(
        f"Reviewer failed after editor — attempting deterministic self-heal — quiz_id={quiz_id}"
    )

    healed_quiz, healed_applied = apply_reviewer_fixes(
        quiz_payload=fixed_quiz,
        review_result=final_review,
    )

    if healed_applied > 0:
        validate_quiz_payload(
            payload=healed_quiz,
            quiz_id=quiz_id,
            expected_count=total_questions,
        )

        healed_review = review_quiz_quality(
            quiz_payload=healed_quiz,
            source_paragraphs=source_paragraphs,
        )

        if healed_review.get("status") == "PASS":
            logger.info(
                f"Stage 2.8 quiz pipeline completed after self-heal — quiz_id={quiz_id}"
            )
            return healed_quiz

    # -------------------------------------------------
    # 5) HARD STOP (NO MORE RETRIES)
    # -------------------------------------------------
    logger.error(f"Quiz failed after editor + self-heal — quiz_id={quiz_id}")
    logger.warning(f"Reviewer issues — {final_review.get('issues')}")

    raise RuntimeError(f"Quiz {quiz_id} failed quality review after editor")

