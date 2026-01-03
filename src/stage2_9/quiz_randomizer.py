# src/stage2_9/quiz_randomizer.py
from __future__ import annotations

import random
from typing import Dict, Any


def randomize_mcq(
    *,
    question: Dict[str, Any],
    seed: str,
) -> Dict[str, Any]:
    """
    Randomize MCQ options while preserving correctness.
    """

    options = question["options"]
    correct_letter = question["correct_answer"]

    items = list(options.items())
    correct_text = options[correct_letter]

    rng = random.Random(seed)
    rng.shuffle(items)

    new_options = {}
    new_correct = None

    for idx, (old_key, text) in enumerate(items):
        new_key = chr(ord("A") + idx)
        new_options[new_key] = text
        if text == correct_text:
            new_correct = new_key

    if new_correct is None:
        raise ValueError("Correct answer lost during randomization")

    question["options"] = new_options
    question["correct_answer"] = new_correct
    question["_meta"] = {
        "randomized": True,
        "seed": seed,
    }

    return question
