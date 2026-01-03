# src/stage2_9_2/flatten_quizzes.py
from __future__ import annotations

from typing import Any, Dict, List


def flatten_quizzes(module_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten all quiz questions into row-based records.

    One row = one question
    """

    rows: List[Dict[str, Any]] = []

    slides = module_json.get("slides", [])

    for slide_index, slide in enumerate(slides):
        if slide.get("slide_type") != "quiz":
            continue

        quiz_id = slide.get("quiz_id")
        placement = slide.get("placement", "unknown")

        for q_index, q in enumerate(slide.get("questions", [])):
            row: Dict[str, Any] = {
                "quiz_id": quiz_id,
                "placement": placement,
                "slide_index": slide_index,

                "question_id": q.get("question_id"),
                "question_type": q.get("type"),
                "prompt": q.get("prompt"),

                # MCQ options (may be None for true/false)
                "option_A": q.get("options", {}).get("A"),
                "option_B": q.get("options", {}).get("B"),
                "option_C": q.get("options", {}).get("C"),
                "option_D": q.get("options", {}).get("D"),

                "correct_answer": q.get("correct_answer"),
                "rationale": q.get("rationale"),
            }

            rows.append(row)

    return rows
