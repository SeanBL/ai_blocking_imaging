from __future__ import annotations
from typing import Dict, Any, List
import logging

from ....utils.llm_client_realtime import LLMClientRealtime
from ....utils.config_loader import load_prompt


# ------------------------------------------------------------
# Build Quiz Prompt (FINAL UNITS ONLY)
# ------------------------------------------------------------

def _build_quiz_prompt(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
) -> str:
    """
    Build the prompt for quiz generation.

    SOURCE TEXT is assembled from:
      - page units → page paragraph text
      - engage2 units → engage2_steps (if present)
    """

    text_chunks: List[str] = []

    for unit in units:
        unit_type = unit.get("unit_type")

        # -----------------------
        # PAGE CONTENT
        # -----------------------
        if unit_type == "page":
            for page in unit.get("pages", []):
                for p_idx in page.get("paragraph_indices", []):
                    text_chunks.append(paragraphs[p_idx])

        # -----------------------
        # ENGAGE2 STEPS
        # -----------------------
        elif unit_type == "engage2":
            for step in unit.get("engage2_steps", []) or []:
                text_chunks.append(step)

    combined_text = "\n".join(t.strip() for t in text_chunks if t.strip())

    base_prompt = load_prompt("prompt_quiz.txt")

    return (
        f"{base_prompt}\n\n"
        f"SOURCE TEXT (use ONLY this text to construct questions):\n"
        f"{combined_text}"
    )


# ------------------------------------------------------------
# Validation Helpers (UNCHANGED)
# ------------------------------------------------------------

def _validate_question_structure(q: Dict[str, Any], header: str) -> None:
    if "question" not in q or not isinstance(q["question"], str):
        raise ValueError(f"Invalid question in '{header}': missing or malformed 'question'")

    if "options" not in q or not isinstance(q["options"], list):
        raise ValueError(f"Invalid quiz question in '{header}': missing 'options' list")

    if "correct_answers" not in q or not isinstance(q["correct_answers"], list):
        raise ValueError(f"Invalid quiz question in '{header}': missing 'correct_answers' list")

    if q.get("type") not in ("single", "multiple", "true_false"):
        raise ValueError(f"Invalid question type in '{header}': {q.get('type')}")


def _enforce_reserve_rule(quiz: List[Dict[str, Any]], header: str) -> None:
    finals = [q for q in quiz if q.get("reserve_for_final_exam") is True]

    if len(finals) == 1:
        return

    logging.warning(
        f"⚠ Quiz for '{header}' has {len(finals)} reserve questions (expected exactly 1). "
        f"Automatically correcting."
    )

    for q in quiz:
        q["reserve_for_final_exam"] = False

    if quiz:
        quiz[-1]["reserve_for_final_exam"] = True


def _enforce_question_count_rules(quiz: List[Dict[str, Any]], header: str) -> None:
    inline = [q for q in quiz if not q.get("reserve_for_final_exam")]
    reserves = [q for q in quiz if q.get("reserve_for_final_exam")]

    if len(inline) > 5:
        logging.warning(
            f"⚠ Too many inline questions ({len(inline)}) for '{header}'. Truncating to 5."
        )
        inline = inline[:5]

    if len(inline) < 3:
        logging.warning(
            f"⚠ Too few inline questions ({len(inline)}) for '{header}'. Duplicating last."
        )
        while len(inline) < 3 and inline:
            inline.append(inline[-1].copy())

    if len(reserves) == 0:
        logging.warning(
            f"⚠ No reserve question found for '{header}'. Creating one."
        )
        new_reserve = inline[-1].copy()
        new_reserve["reserve_for_final_exam"] = True
        reserves = [new_reserve]

    elif len(reserves) > 1:
        logging.warning(
            f"⚠ Multiple reserve questions in '{header}'. Keeping last."
        )
        reserves = [reserves[-1]]

    quiz[:] = inline + reserves


# ------------------------------------------------------------
# Stage 2F — Quiz Generation (FINAL UNITS ONLY)
# ------------------------------------------------------------

def generate_quiz(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
    llm: LLMClientRealtime,
) -> Dict[str, Any]:
    """
    Generate quiz questions for a header using FINAL UNITS.
    """

    logging.info(f"Generating quiz for header: {header}")

    prompt = _build_quiz_prompt(header, paragraphs, units)
    result = llm.call_json(prompt)

    if "quiz" not in result or not isinstance(result["quiz"], list):
        raise ValueError(f"Quiz JSON for '{header}' must contain a list under 'quiz'")

    quiz: List[Dict[str, Any]] = result["quiz"]

    for q in quiz:
        _validate_question_structure(q, header)

    _enforce_reserve_rule(quiz, header)
    _enforce_question_count_rules(quiz, header)

    result["quiz"] = quiz
    return result
