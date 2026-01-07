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
        # ----------------------------
        # Required keys (defensive)
        # ----------------------------
        required_keys = {"question_id", "prompt", "type", "quiz_role"}
        missing = required_keys - q.keys()
        if missing:
            raise ValueError(
                f"[POST] Missing required keys {missing} in question payload"
            )

        qid = q["question_id"]

        quiz_role = q.get("quiz_role")
        if quiz_role not in ("inline_direct", "final_direct", "module_application"):
            raise ValueError(
                f"[POST] Missing or invalid quiz_role — {qid}: {quiz_role}"
            )

        prompt_raw = q["prompt"]
        if not isinstance(prompt_raw, str) or not prompt_raw.strip():
            raise ValueError(f"[POST] Empty or invalid prompt — {qid}")
        prompt = prompt_raw.strip()

        qtype = q["type"]

        # ----------------------------
        # MCQ structure (defensive)
        # ----------------------------
        if qtype == "mcq":
            if "options" not in q or "correct_answer" not in q:
                raise ValueError(
                    f"[POST] MCQ missing options or correct_answer — {qid}"
                )

            options = q["options"]
            correct_key = q["correct_answer"]
            correct_text = options[correct_key].strip()

            # 1️⃣ Correct option leakage
            if correct_text in prompt:
                raise ValueError(
                    f"[POST] Correct option text leaked into prompt — {qid}"
                )

            # 3️⃣ Duplicate meaning across options
            option_texts = [v.strip().lower() for v in options.values()]
            if len(set(option_texts)) < 4:
                raise ValueError(
                    f"[POST] Duplicate or near-duplicate options — {qid}"
                )

        # ----------------------------
        # 2️⃣ Prompt restatement heuristic
        # ----------------------------
        lower_prompt = prompt.lower()
        if "best fits this model" in lower_prompt and qtype == "mcq":
            pass  # placeholder for future heuristics

        # ----------------------------
        # Role ↔ style ↔ cognitive checks
        # ----------------------------
        question_style = q.get("question_style")
        cognitive_level = q.get("cognitive_level")

        if quiz_role == "module_application":
            if question_style != "scenario":
                raise ValueError(
                    f"[POST] module_application must be scenario — {qid}"
                )
            if cognitive_level != "apply":
                raise ValueError(
                    f"[POST] module_application must be apply — {qid}"
                )

        if quiz_role in ("inline_direct", "final_direct"):
            if question_style != "direct":
                raise ValueError(
                    f"[POST] {quiz_role} must be direct — {qid}"
                )
            if cognitive_level not in ("recall", "interpret"):
                raise ValueError(
                    f"[POST] {quiz_role} must be recall/interpret — {qid}"
                )

        # ----------------------------
        # Claim IDs should survive authoring
        # ----------------------------
        claim_ids = q.get("claim_ids")
        if not isinstance(claim_ids, list) or not claim_ids:
            raise ValueError(f"[POST] Missing or invalid claim_ids — {qid}")

    # ----------------------------
    # Cross-question sanity
    # ----------------------------
    roles = [q["quiz_role"] for q in questions]

    if roles.count("module_application") == 0:
        raise ValueError(
            "[POST] No module_application question present in quiz payload"
        )
