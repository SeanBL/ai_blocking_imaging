from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List

from ...utils.llm_client_realtime import LLMClientRealtime


# -----------------------------------------------------------
# Load Engage2 prompt (unchanged)
# -----------------------------------------------------------

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]  # => src/
    / "config"
    / "prompt_engage2_extract.txt"
)

if not PROMPT_PATH.exists():
    raise FileNotFoundError(f"Engage2 prompt not found: {PROMPT_PATH}")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    BASE_PROMPT = f.read()


# -----------------------------------------------------------
# Build Engage2 prompt (NEW CONTRACT)
# -----------------------------------------------------------

def build_prompt(
    header: str,
    paragraphs: List[str],
    paragraph_indices: List[int],
) -> str:
    """
    Engage2 prompt is built from FINAL UNIT paragraph indices only.
    """

    if not paragraph_indices:
        combined = ""
        first_idx = 0
    else:
        texts = [paragraphs[i] for i in paragraph_indices]
        combined = " ".join(texts).strip()
        first_idx = paragraph_indices[0]

    prompt = (
        BASE_PROMPT
        .replace("<<<HEADER>>>", header)
        .replace("<<<INDEX>>>", str(first_idx))
        .replace("<<<TEXT>>>", combined)
    )

    return prompt


# -----------------------------------------------------------
# Main extraction wrapper (FINAL UNITS ONLY)
# -----------------------------------------------------------

def extract_engage2(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
    llm: LLMClientRealtime,
) -> Dict[str, Any]:
    """
    Produces:
    {
      "header": "...",
      "engage2_items": [
        {
          "unit_id": "u07",
          "paragraph_indices": [6,7,8],
          "engage2_steps": [...]
        }
      ]
    }
    """

    engage2_items: List[Dict[str, Any]] = []

    for unit in units:
        if unit.get("unit_type") != "engage2":
            continue

        # engage2 may legitimately have no steps
        paragraph_indices = unit.get("paragraph_indices") or []

        if not paragraph_indices:
            # Skip safely — this is VALID
            continue

        prompt = build_prompt(header, paragraphs, paragraph_indices)
        response = llm.call_json(prompt)

        if "engage2_blocks" not in response:
            raise ValueError(
                "[extract_engage2] LLM output missing key: 'engage2_blocks'"
            )

        for block in response["engage2_blocks"]:
            engage2_items.append({
                "unit_id": unit.get("unit_id"),
                "paragraph_indices": paragraph_indices,
                "engage2_steps": block.get("engage2_steps", []),
            })

    return {
        "header": header,
        "engage2_items": engage2_items,
    }
