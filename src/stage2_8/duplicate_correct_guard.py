from __future__ import annotations

from typing import Dict, Any, List
import re


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return set(words)


def _similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)

    if not ta or not tb:
        return 0.0

    return len(ta & tb) / len(ta | tb)


def detect_duplicate_correct_answers(
    quiz_payload: Dict[str, Any],
    threshold: float = 0.65,
) -> List[Dict[str, Any]]:
    """
    Detect distractors that are too similar to the correct answer.
    Returns reviewer-style issues so the existing fixer/editor can handle them.
    """

    issues = []

    for q in quiz_payload.get("questions", []):
        if q.get("type") != "mcq":
            continue

        correct_key = q.get("correct_answer")
        options = q.get("options", {})

        correct_text = options.get(correct_key)
        if not correct_text:
            continue

        for key, text in options.items():
            if key == correct_key:
                continue

            sim = _similarity(correct_text, text)

            if sim >= threshold:
                issues.append({
                    "question_id": q.get("question_id"),
                    "problem": "Distractor too similar to the correct answer",
                    "suggested_fixes": {
                        f"options.{key}": f"Rewrite distractor so it is clearly incorrect but still plausible."
                    }
                })

    return issues