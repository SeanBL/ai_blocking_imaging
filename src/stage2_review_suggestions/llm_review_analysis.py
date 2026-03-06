# src/stage2_review_suggestions/llm_review_analysis.py
from __future__ import annotations

from typing import Dict, List, Optional

from .logger import logger
from src.utils.llm_client_realtime import LLMClientRealtime

SYSTEM_PROMPT = """
You are a clinical and editorial reviewer for licensed health education content.

Your task is to ANALYZE the provided text and flag potential issues.

STRICT RULES:
- DO NOT rewrite or rephrase the text.
- DO NOT suggest alternative wording.
- DO NOT add new medical facts.
- DO NOT infer intent beyond the text.
- ONLY identify potential issues, ambiguities, or concerns.

Focus on:
- Clinical accuracy
- Scope appropriateness (e.g., CHW vs clinician roles)
- Pedagogical clarity
- Ambiguous or potentially misleading phrasing

If no issues are found, return empty flags and notes.
"""

USER_PROMPT_TEMPLATE = """
TEXT TYPE: {unit_type}
SLIDE ID: {slide_id}

TEXT:
{content}

Return JSON with:
- flags: list of short issue statements
- notes: brief explanation (optional)
"""


def analyze_text_unit(
    *,
    unit_type: str,
    slide_id: str,
    content: str,
) -> Dict[str, Optional[List[str] | str]]:
    """
    Returns:
    {
      "flags": list[str] | [],
      "notes": str | None
    }
    """

    logger.info(f"Analyzing {unit_type} — slide={slide_id}")

    llm = LLMClientRealtime()

    prompt = USER_PROMPT_TEMPLATE.format(
        unit_type=unit_type,
        slide_id=slide_id,
        content=content,
    )

    response = llm.call_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        required_keys={"flags", "notes"},
    )

    flags = response.get("flags") or []
    notes = response.get("notes")

    # Defensive normalization
    if not isinstance(flags, list):
        flags = []

    return {
        "flags": flags,
        "notes": notes,
    }
