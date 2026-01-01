from __future__ import annotations

from typing import Dict, List


def insert_quiz_slides(
    slides: List[dict],
    inline_quizzes: Dict[int, dict],
    final_quizzes: Dict[int, dict],
) -> List[dict]:
    """
    Returns a NEW slides list with quiz slides inserted.
    """

    new_slides: List[dict] = []
    insert_map = {
        q["insert_after_index"]: q
        for q in inline_quizzes.values()
    }

    for idx, slide in enumerate(slides):
        new_slides.append(slide)

        if idx in insert_map:
            new_slides.append(insert_map[idx]["slide"])

    # Append final quizzes in quiz_id order
    for quiz_id in sorted(final_quizzes.keys()):
        new_slides.append(final_quizzes[quiz_id])

    return new_slides
