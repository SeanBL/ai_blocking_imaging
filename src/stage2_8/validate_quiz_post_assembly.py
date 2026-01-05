from __future__ import annotations
from typing import Dict, Any, List


def validate_quiz_post_assembly(
    *,
    quiz_payload: Dict[str, Any],
) -> None:
    """
    Defensive validation AFTER quiz assembly.
    Catches issues that single-question validation cannot.
    """

    questions: List[Dict[str, Any]] = quiz_payload.get("questions", [])

    for q in questions:
        qid = q["question_id"]
        prompt = q["prompt"].strip()
        qtype = q["type"]

        # --------------------------------------------------
        # 1️⃣ Prompt must not contain full correct option
        # --------------------------------------------------
        if qtype == "mcq":
            options = q["options"]
            correct_key = q["correct_answer"]
            correct_text = options[correct_key].strip()

            # exact containment = leakage
            if correct_text in prompt:
                raise ValueError(
                    f"[POST] Correct option text leaked into prompt — {qid}"
                )

        # --------------------------------------------------
        # 2️⃣ Prompt should not explicitly restate answer
        # --------------------------------------------------
        lower_prompt = prompt.lower()
        if "best fits this model" in lower_prompt and qtype == "mcq":
            # heuristic example — expandable later
            pass

        # --------------------------------------------------
        # 3️⃣ Duplicate meaning across options (light check)
        # --------------------------------------------------
        if qtype == "mcq":
            option_texts = [v.strip().lower() for v in q["options"].values()]
            if len(set(option_texts)) < 4:
                raise ValueError(
                    f"[POST] Duplicate or near-duplicate options — {qid}"
                )
