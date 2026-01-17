from __future__ import annotations

from typing import Any, Dict, List

from .logger import logger
from .quiz_detect import detect_quizzes, QuizState
from .quiz_extract import extract_quiz_source
from .runner import run_quiz_pipeline


def run_stage2_8(
    *,
    module_json: Dict[str, Any],
    sentence_annotations: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Stage 2.8 orchestration layer.

    Produces quiz payloads ONLY.
    Does not insert slides.
    """

    slides: List[Dict[str, Any]] = module_json.get("slides", [])
    if not slides:
        logger.info("Stage 2.8: no slides found — skipping")
        return {
            "inline_quizzes": {},
            "module_application_quizzes": {},
            "final_quizzes": {},
        }

    logger.info("Stage 2.8: detecting quizzes")
    quiz_states: Dict[int, QuizState] = detect_quizzes(slides)

    inline_quizzes: Dict[int, Dict[str, Any]] = {}
    final_quizzes: Dict[int, Dict[str, Any]] = {}
    module_application_quizzes: Dict[int, Dict[str, Any]] = {}

    if sentence_annotations is not None and not isinstance(sentence_annotations, dict):
            raise TypeError(
                f"sentence_annotations must be dict or None, got {type(sentence_annotations)}"
            )

    for quiz_id, state in quiz_states.items():
        logger.info(f"Stage 2.8: processing quiz_id={quiz_id}")

        source_paragraphs = extract_quiz_source(
            slides=slides,
            quiz_state=state,
            sentence_annotations=sentence_annotations,  # ✅ NEW
        )

        logger.info(
            f"[Stage 2.8] QUIZ:{quiz_id} parsed counts — "
            f"inline={state.immediate_count}, "
            f"final={state.deferred_count}, "
            f"application={state.application_count}"
        )
        
        quiz_payload = run_quiz_pipeline(
            quiz_id=quiz_id,
            inline_direct_questions=state.immediate_count,
            final_direct_questions=state.deferred_count,
            module_application_questions=state.application_count,
            source_paragraphs=source_paragraphs,
        )

        questions = quiz_payload["questions"]

        inline_questions = [
            q for q in questions if q["quiz_role"] == "inline_direct"
        ]

        final_direct_questions = [
            q for q in questions if q["quiz_role"] == "final_direct"
        ]

        application_questions = [
            q for q in questions if q["quiz_role"] == "module_application"
        ]

        if inline_questions:
            inline_quizzes[quiz_id] = {
                "insert_after_index": state.insert_index,
                "questions": inline_questions,
            }

        if final_direct_questions:
            final_quizzes[quiz_id] = {
                "quiz_id": quiz_id,
                "questions": final_direct_questions,
            }

        if application_questions:
            module_application_quizzes[quiz_id] = {
                "quiz_id": quiz_id,
                "questions": application_questions,
            }

    logger.info("Stage 2.8: orchestration complete")

    return {
        "inline_quizzes": inline_quizzes,
        "module_application_quizzes": module_application_quizzes,
        "final_quizzes": final_quizzes,
    }

