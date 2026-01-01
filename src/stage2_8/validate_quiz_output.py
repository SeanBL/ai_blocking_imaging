from __future__ import annotations

from typing import Any, Dict, List, Set


ALLOWED_QUESTION_KEYS: Set[str] = {
    "question_id",
    "type",
    "prompt",
    "options",
    "correct_answer",
    "rationale",
}


def validate_quiz_payload(
    payload: Dict[str, Any],
    quiz_id: int,
    expected_count: int,
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Quiz payload must be a JSON object")

    # ------------------------
    # QUIZ ID (INVARIANT)
    # ------------------------
    if payload.get("quiz_id") is None:
        raise ValueError("Quiz payload missing quiz_id (LLM invariant violation)")

    if payload.get("quiz_id") != quiz_id:
        raise ValueError(
            f"quiz_id mismatch: expected {quiz_id}, got {payload.get('quiz_id')}"
        )

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise ValueError("questions must be a list")

    if len(questions) != expected_count:
        raise ValueError(
            f"Expected {expected_count} questions, got {len(questions)}"
        )

    tf_count = 0

    for idx, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            raise ValueError(f"Question {idx} must be an object")

        # ------------------------
        # STRICT SCHEMA
        # ------------------------
        extra = set(q.keys()) - ALLOWED_QUESTION_KEYS
        if extra:
            raise ValueError(
                f"Question {idx} has extra keys: {sorted(extra)}"
            )

        qid = q.get("question_id")
        if qid != f"q{idx}":
            raise ValueError(
                f"Question {idx} must have question_id 'q{idx}', got {qid}"
            )

        qtype = q.get("type")
        if qtype not in ("true_false", "mcq"):
            raise ValueError(
                f"Question {idx} has invalid type: {qtype}"
            )

        prompt = q.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                f"Question {idx} prompt must be non-empty string"
            )

        rationale = q.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(
                f"Question {idx} rationale must be non-empty string"
            )

        # ------------------------
        # TRUE / FALSE
        # ------------------------
        if qtype == "true_false":
            tf_count += 1

            if q.get("options") is not None:
                raise ValueError(
                    f"Question {idx} true_false must not include options"
                )

            ca = q.get("correct_answer")
            if not isinstance(ca, bool):
                raise ValueError(
                    f"Question {idx} true_false correct_answer must be boolean"
                )

        # ------------------------
        # MCQ
        # ------------------------
        if qtype == "mcq":
            options = q.get("options")
            if not isinstance(options, dict):
                raise ValueError(
                    f"Question {idx} mcq options must be an object"
                )

            if set(options.keys()) != {"A", "B", "C", "D"}:
                raise ValueError(
                    f"Question {idx} mcq options must have keys A,B,C,D"
                )

            for k in ("A", "B", "C", "D"):
                if not isinstance(options[k], str) or not options[k].strip():
                    raise ValueError(
                        f"Question {idx} option {k} must be non-empty string"
                    )

            ca = q.get("correct_answer")
            if ca not in ("A", "B", "C", "D"):
                raise ValueError(
                    f"Question {idx} mcq correct_answer must be one of A,B,C,D"
                )

    # ------------------------
    # OPTION B RULE ENFORCEMENT
    # ------------------------
    if tf_count > 1:
        raise ValueError(
            f"At most one true_false question is allowed, got {tf_count}"
        )