from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path

from ...utils.llm_client_realtime import LLMClientRealtime


# --------------------------------------------------
# Load prompt
# --------------------------------------------------

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "prompt_stage2A2_units.txt"
)

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    PROMPT_TEMPLATE = f.read()


def build_stage2A2_prompt(header: str, paragraphs: List[str]) -> str:
    indexed = ""
    for i, p in enumerate(paragraphs):
        indexed += f"[{i}] {p}\n\n"

    return (
        PROMPT_TEMPLATE
        .replace("<<<HEADER>>>", header)
        .replace("<<<PARAGRAPHS>>>", indexed.strip())
    )


# --------------------------------------------------
# Main Stage 2A2 function
# --------------------------------------------------

def assign_final_units(
    header: str,
    paragraphs: List[str],
    llm: LLMClientRealtime
) -> Dict[str, Any]:
    """
    Returns the FINAL structural plan for this header.
    """

    prompt = build_stage2A2_prompt(header, paragraphs)
    result = llm.call_json(prompt)

    # ---- minimal validation ----
    if result.get("header") != header:
        raise ValueError("Header mismatch in Stage 2A2")

    if "final_units" not in result:
        raise ValueError("Missing final_units in Stage 2A2 output")

    return result
