from __future__ import annotations
from typing import Dict, Any, List
import logging

from ..utils.llm_client_realtime import LLMClientRealtime
from ..utils.config_loader import load_prompt


def _build_quiz_prompt(stage2A_block: Dict[str, Any]) -> str:
    """
    Build the full prompt for quiz generation from a Stage 2A block.
    We aggregate all readable text (content, engage_points, engage2_steps).
    """
    header = stage2A_block.get("header", "")
    pages: List[Dict[str, Any]] = stage2A_block.get("pages", [])

    text_chunks: List[str] = []
    for page in pages:
        if page.get("content"):
            text_chunks.append(page["content"])
        for pt in page.get("engage_points", []) or []:
            text_chunks.append(pt)
        for step in page.get("engage2_steps", []) or []:
            text_chunks.append(step)

    combined_text = "\n".join(text_chunks).strip()

    base_prompt = load_prompt("prompt_quiz.txt")

    # Your refined prompt does NOT use <<<CONTENT>>>; we append the text.
    prompt = (
        f"{base_prompt}\n\n"
        f"SECTION HEADER:\n{header}\n\n"
        f"Text:\n{combined_text}"
    )

    return prompt


def generate_quiz(stage2A_block: Dict[str, Any], llm: LLMClientRealtime) -> Dict[str, Any]:
    """
    Stage 2C:
    Generate quiz questions for a given Stage 2A block using the LLM.

    Returns a dict of the form:
      { "quiz": [ ... ] }
    """
    header = stage2A_block.get("header", "")
    logging.info(f"Generating quiz for header: {header}")

    prompt = _build_quiz_prompt(stage2A_block)
    result = llm.call_json(prompt)

    # Basic validation
    if "quiz" not in result or not isinstance(result["quiz"], list):
        raise ValueError(f"Quiz generation failed for '{header}': missing 'quiz' list in response")

    # Check reserve_for_final_exam count (should be exactly 1)
    finals = [q for q in result["quiz"] if q.get("reserve_for_final_exam") is True]
    if len(finals) != 1:
        logging.warning(
            f"Quiz for header '{header}' has {len(finals)} questions marked "
            f"reserve_for_final_exam (expected exactly 1)."
        )

    return result