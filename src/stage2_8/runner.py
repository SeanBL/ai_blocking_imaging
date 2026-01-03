from __future__ import annotations

from typing import Dict, List

from .logger import logger
from .llm_quiz import generate_quiz_questions
from .validate_quiz_output import validate_quiz_payload
from .quiz_quality_review import review_quiz_quality
from .apply_reviewer_fixes import apply_reviewer_fixes
from .editor_llm import run_editor_llm


def run_quiz_pipeline(
    *,
    quiz_id: int,
    total_questions: int,
    source_paragraphs: List[str],
) -> Dict[str, any]:
    """
    Runs Stage 2.8 quiz generation with:
    - Author → Reviewer → Deterministic Fixer → (optional) Editor LLM
    - Single retry max
    - Deterministic, logged, schema-validated flow
    """

    logger.info(
        f"Stage 2.8 quiz pipeline started — quiz_id={quiz_id}"
    )

    # -------------------------------------------------
    # Adjust question count based on content volume
    # -------------------------------------------------
    max_allowed = max(1, len(source_paragraphs) * 2)

    if total_questions > max_allowed:
        logger.warning(
            f"Reducing quiz question count due to limited content — "
            f"quiz_id={quiz_id}, requested={total_questions}, allowed={max_allowed}"
        )
        total_questions = max_allowed

    # -------------------------------------------------
    # 1️⃣ AUTHOR — generate quiz
    # -------------------------------------------------
    quiz = generate_quiz_questions(
        quiz_id=quiz_id,
        total_questions=total_questions,
        source_paragraphs=source_paragraphs,
    )

    # -------------------------------------------------
    # Normalize question count if author under-generates
    # -------------------------------------------------
    actual_count = len(quiz.get("questions", []))

    if actual_count < total_questions:
        logger.warning(
            f"Author under-generated questions — "
            f"quiz_id={quiz_id}, requested={total_questions}, actual={actual_count}"
        )
        total_questions = actual_count

    # -------------------------------------------------
    # 2️⃣ STRUCTURAL VALIDATION
    # -------------------------------------------------
    validate_quiz_payload(
        payload=quiz,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )

    logger.info(
        f"Structural validation passed — quiz_id={quiz_id}"
    )

    # -------------------------------------------------
    # 3️⃣ REVIEWER — quality check
    # -------------------------------------------------
    review = review_quiz_quality(
        quiz_payload=quiz,
        source_paragraphs=source_paragraphs,
    )

    if review.get("status") == "PASS":
        logger.info(
            f"Quality review passed on first attempt — quiz_id={quiz_id}"
        )
        logger.info(
            f"Stage 2.8 quiz pipeline completed — quiz_id={quiz_id}"
        )
        return quiz

    logger.warning(
        f"Reviewer issues — quiz_id={quiz_id}: {review.get('issues')}"
    )

    # -------------------------------------------------
    # 4️⃣ DETERMINISTIC FIXER
    # -------------------------------------------------
    logger.warning(
        f"Quality review failed — attempting deterministic fixes — quiz_id={quiz_id}"
    )

    fixed_quiz, applied = apply_reviewer_fixes(
        quiz_payload=quiz,
        review_result=review,
    )

    validate_quiz_payload(
        payload=fixed_quiz,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )

    logger.info(
        f"Structural validation passed after fix — quiz_id={quiz_id}"
    )

    # -------------------------------------------------
    # 5️⃣ ACCEPT IF FIXES WERE APPLIED
    # -------------------------------------------------
    if applied > 0:
        logger.info(
            f"Reviewer issues resolved deterministically — accepting quiz — quiz_id={quiz_id}"
        )
        logger.info(
            f"Stage 2.8 quiz pipeline completed — quiz_id={quiz_id}"
        )
        return fixed_quiz

    # -------------------------------------------------
    # 6️⃣ EDITOR LLM FALLBACK (ONLY IF NOTHING WAS FIXED)
    # -------------------------------------------------
    logger.warning(
        f"No deterministic fix possible — invoking editor LLM — quiz_id={quiz_id}"
    )

    edited_quiz = run_editor_llm(
        quiz_payload=fixed_quiz,
        review_result=review,
    )

    validate_quiz_payload(
        payload=edited_quiz,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )

    logger.info(
        f"Structural validation passed after editor — quiz_id={quiz_id}"
    )

    final_review = review_quiz_quality(
        quiz_payload=edited_quiz,
        source_paragraphs=source_paragraphs,
    )

    if final_review.get("status") == "PASS":
        logger.info(
            f"Quality review passed after editor fallback — quiz_id={quiz_id}"
        )
        logger.info(
            f"Stage 2.8 quiz pipeline completed — quiz_id={quiz_id}"
        )
        return edited_quiz

    # -------------------------------------------------
    # 7️⃣ SECOND (FINAL) EDITOR RETRY WITH REVIEWER GUIDANCE
    # -------------------------------------------------
    logger.warning(
        f"Retrying editor once with explicit reviewer guidance — quiz_id={quiz_id}"
    )

    edited_quiz_2 = run_editor_llm(
        quiz_payload=edited_quiz,
        review_result=final_review,
    )

    validate_quiz_payload(
        payload=edited_quiz_2,
        quiz_id=quiz_id,
        expected_count=total_questions,
    )

    logger.info(
        f"Structural validation passed after second editor — quiz_id={quiz_id}"
    )

    final_review_2 = review_quiz_quality(
        quiz_payload=edited_quiz_2,
        source_paragraphs=source_paragraphs,
    )

    if final_review_2.get("status") == "PASS":
        logger.info(
            f"Quality review passed after second editor fallback — quiz_id={quiz_id}"
        )
        logger.info(
            f"Stage 2.8 quiz pipeline completed — quiz_id={quiz_id}"
        )
        return edited_quiz_2

    # -------------------------------------------------
    # 8️⃣ HARD STOP (INTENTIONAL)
    # -------------------------------------------------
    logger.error(
        f"Stage 2.8 quiz failed quality review after second editor — quiz_id={quiz_id}"
    )
    logger.warning(
        f"Reviewer issues — quiz_id={quiz_id}: {final_review_2.get('issues')}"
    )

    raise RuntimeError(
        f"Quiz {quiz_id} failed quality review after editor retries"
    )
