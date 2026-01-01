from __future__ import annotations

from typing import Any, Dict, List

from .logger import logger
from .quiz_detect import detect_quizzes, QuizState
from .quiz_extract import extract_quiz_source
from .runner import run_quiz_pipeline


def run_stage2_8(
    *,
    module_json: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stage 2.8 orchestration layer.

    Input:
      - module_json: canonical module JSON from Stage 2.7
        (used for quiz marker detection; notes must be preserved)

    Output:
      {
        "inline_quizzes": {
            quiz_id: {
                "insert_after_index": int,
                "questions": [...]
            }
        },
        "final_quizzes": {
            quiz_id: {
                "quiz_id": int,
                "questions": [...]
            }
        }
      }

    NOTE:
    - This function does NOT modify slides
    - This function does NOT build quiz slides
    """

    slides: List[Dict[str, Any]] = module_json.get("slides", [])
    if not slides:
        logger.info("Stage 2.8: no slides found — skipping")
        return {
            "inline_quizzes": {},
            "final_quizzes": {},
        }

    logger.info("Stage 2.8: detecting quizzes")
    quiz_states: Dict[int, QuizState] = detect_quizzes(slides)

    inline_quizzes: Dict[int, Dict[str, Any]] = {}
    final_quizzes: Dict[int, Dict[str, Any]] = {}

    for quiz_id, state in quiz_states.items():
        logger.info(f"Stage 2.8: processing quiz_id={quiz_id}")

        source_paragraphs = extract_quiz_source(
            slides=slides,
            quiz_state=state,
        )

        total_questions = state.immediate_count + state.deferred_count

        quiz_payload = run_quiz_pipeline(
            quiz_id=quiz_id,
            total_questions=total_questions,
            source_paragraphs=source_paragraphs,
        )

        immediate = state.immediate_count
        deferred = state.deferred_count

        if immediate > 0:
            inline_quizzes[quiz_id] = {
                "insert_after_index": state.insert_index,
                "questions": quiz_payload["questions"][:immediate],
            }

        if deferred > 0:
            final_quizzes[quiz_id] = {
                "quiz_id": quiz_id,
                "questions": quiz_payload["questions"][immediate:],
            }

    logger.info("Stage 2.8: orchestration complete")

    return {
        "inline_quizzes": inline_quizzes,
        "final_quizzes": final_quizzes,
    }
