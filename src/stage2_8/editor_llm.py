from __future__ import annotations

import json
from typing import Dict, Any

from .llm_call import call_llm_json
from .logger import logger


SINGLE_QUESTION_EDITOR_PROMPT = """You are an expert medical educator and assessment editor.

You are fixing ONE quiz question that failed quality review.

STRICT OUTPUT RULES (NON-NEGOTIABLE):
- Return EXACTLY ONE question object.
- DO NOT wrap the output in "questions", "quiz", or any container.
- Return a FLAT JSON object only.
- Do NOT include commentary or explanations outside JSON.

EDITING RULES:
- Modify ONLY the provided question.
- Do NOT change question_id.
- Do NOT change quiz_role.
- Do NOT change claim_ids.
- Do NOT change cognitive_level.
- Resolve ambiguity so EXACTLY ONE correct answer remains.

OUTPUT FORMAT:

For MCQ:
{
  "type": "mcq",
  "prompt": "...",
  "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
  "correct_answer": "A" | "B" | "C" | "D",
  "rationale": "..."
}

For true/false:
{
  "type": "true_false",
  "prompt": "...",
  "correct_answer": true | false,
  "rationale": "..."
}

Return ONLY valid JSON.
"""


def run_editor_llm_single_question(
    *,
    question: Dict[str, Any],
    issue: Dict[str, Any],
    quiz_id: int,
) -> Dict[str, Any]:
    """
    Editor rewrites ONE question and MUST return a COMPLETE flat question object.
    """

    logger.warning(
        f"Editor LLM invoked — quiz_id={quiz_id}, question={question['question_id']}"
    )

    payload = {
        "question": question,
        "issue": issue,
    }

    edited = call_llm_json(
        prompt=SINGLE_QUESTION_EDITOR_PROMPT + "\n\n" + json.dumps(payload, ensure_ascii=False),
        stage_tag="Stage 2.8 Editor (single-question)",
    )

    # -------------------------------------------------
    # 🔒 HARD SHAPE ENFORCEMENT (NOW CONSISTENT)
    # -------------------------------------------------

    if not isinstance(edited, dict):
        raise RuntimeError("Editor returned non-dict")

    if "questions" in edited:
        raise RuntimeError(
            f"Editor returned wrapped questions object for {question['question_id']}"
        )

    forbidden = {"quiz", "quiz_id"}
    leaked = forbidden & set(edited.keys())
    if leaked:
        raise RuntimeError(
            f"Editor returned illegal keys {sorted(leaked)} "
            f"for question {question['question_id']}"
        )

    required = {"type", "prompt", "correct_answer", "rationale"}
    missing = required - set(edited.keys())
    if missing:
        raise RuntimeError(
            f"Editor returned incomplete question for {question['question_id']}: "
            f"missing={sorted(missing)}"
        )

    # Conditional validation
    if edited["type"] == "mcq":
        opts = edited.get("options")
        if not isinstance(opts, dict) or set(opts.keys()) != {"A", "B", "C", "D"}:
            raise RuntimeError("Editor returned invalid MCQ options")
        if edited["correct_answer"] not in {"A", "B", "C", "D"}:
            raise RuntimeError("Editor returned invalid MCQ correct_answer")

    elif edited["type"] == "true_false":
        if "options" in edited:
            raise RuntimeError("Editor illegally included options for true_false")
        if edited["correct_answer"] not in {True, False}:
            raise RuntimeError("Editor returned invalid true_false answer")

    else:
        raise RuntimeError(f"Unknown question type: {edited['type']}")

    logger.info(
        f"Editor LLM completed — quiz_id={quiz_id}, question={question['question_id']}"
    )

    return edited
