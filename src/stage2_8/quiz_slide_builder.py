from __future__ import annotations

from typing import Dict, Any, List


def build_inline_quiz_slide(
    *,
    quiz_id: int,
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Builds an inline quiz slide object.

    This slide is inserted immediately after the marker slide.
    """

    return {
        "id": f"quiz_{quiz_id}_inline",
        "slide_type": "quiz",
        "quiz_id": quiz_id,
        "placement": "inline",
        "questions": questions,
    }


def build_final_quiz_slide(
    *,
    quiz_id: int,
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Builds a final quiz slide object.

    This slide is appended to the end of the module.
    """

    return {
        "id": f"quiz_{quiz_id}_final",
        "slide_type": "quiz",
        "quiz_id": quiz_id,
        "placement": "final",
        "questions": questions,
    }
