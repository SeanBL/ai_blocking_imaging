# src/stage2_review_suggestions/llm_engage_intro_bridge.py
from __future__ import annotations

from typing import Dict, Optional, List

from .logger import logger
from src.utils.llm_client_realtime import LLMClientRealtime


SYSTEM_PROMPT = """
You are reviewing licensed medical education content.

CRITICAL RULES (DO NOT VIOLATE):
- You MUST NOT rewrite the existing intro text.
- You MUST NOT add new medical facts.
- You MUST NOT reinterpret or expand clinical meaning.
- You MUST NOT introduce pedagogy or learning objectives.
- You MUST use ONLY the provided intro and engage items.
- You MUST propose AT MOST ONE bridging sentence.
- If a bridge is unnecessary or already present, return bridge = null.

Definition:
A "bridging sentence" is a short neutral sentence that helps transition
from the existing intro paragraph into the engage items that follow.

This output is OPTIONAL and reviewer-facing only.
"""

USER_PROMPT_TEMPLATE = """
Slide ID: {slide_id}

Existing intro paragraph:
{intro_text}

Engage items:
{items}

Return JSON:
{{
  "bridge": string OR null,
  "rationale": short explanation OR null
}}
"""


def propose_engage_intro_bridge(
    *,
    slide_id: str,
    intro_text: str,
    engage_items: List[str],
) -> Dict[str, Optional[str]]:
    """
    Returns:
    {
      "bridge": str | None,
      "rationale": str | None
    }
    """

    if not intro_text or not engage_items:
        return {"bridge": None, "rationale": None}

    items_text = "\n".join(f"- {item}" for item in engage_items)

    prompt = USER_PROMPT_TEMPLATE.format(
        slide_id=slide_id,
        intro_text=intro_text.strip(),
        items=items_text,
    )

    logger.info(f"[INTRO-BRIDGE] Evaluating engage intro bridge — slide={slide_id}")

    llm = LLMClientRealtime()

    response = llm.call_json_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        required_keys={"bridge", "rationale"},
    )

    bridge = response.get("bridge")
    rationale = response.get("rationale")

    if not bridge:
        return {"bridge": None, "rationale": None}

    return {
        "bridge": bridge.strip(),
        "rationale": rationale.strip() if isinstance(rationale, str) else None,
    }
