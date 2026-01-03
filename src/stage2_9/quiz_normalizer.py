# src/stage2_9/quiz_normalizer.py
from __future__ import annotations

from typing import Dict, Any


def normalize_question(question: Dict[str, Any]) -> Dict[str, Any]:
    qtype = question["type"]

    if qtype == "mcq":
        if "options" not in question:
            raise ValueError("MCQ missing options")
        if len(question["options"]) != 4:
            raise ValueError("MCQ must have exactly 4 options")

    elif qtype == "true_false":
        if "options" in question:
            raise ValueError("true_false must not include options")
        if question["correct_answer"] not in (True, False):
            raise ValueError("true_false correct_answer must be boolean")

    else:
        raise ValueError(f"Unknown question type: {qtype}")

    return question
