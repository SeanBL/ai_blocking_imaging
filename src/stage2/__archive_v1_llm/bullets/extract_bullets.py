from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List

from ...utils.llm_client_realtime import LLMClientRealtime


# -----------------------------------------------------------
# Load bullet prompt from src/config
# -----------------------------------------------------------

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]     # => src/
    / "config"
    / "prompt_bullet_extract.txt"
)

if not PROMPT_PATH.exists():
    raise FileNotFoundError(f"Bullet prompt not found: {PROMPT_PATH}")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    BULLET_PROMPT = f.read()


# -----------------------------------------------------------
# Build prompt (unchanged)
# -----------------------------------------------------------

def build_prompt(header: str, text: str, p_idx: int) -> str:
    return (
        BULLET_PROMPT
        .replace("<<<HEADER>>>", header)
        .replace("<<<INDEX>>>", str(p_idx))
        .replace("<<<TEXT>>>", text)
    )


# -----------------------------------------------------------
# Extract bullets (FINAL UNITS ONLY)
# -----------------------------------------------------------

def extract_bullets(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
    llm: LLMClientRealtime,
) -> Dict[str, Any]:
    """
    Produces:
    {
      "header": "...",
      "bullet_blocks": [
        {
          "unit_id": "u01",
          "page_index": 0,
          "paragraph_index": 2,
          "bullet_points": [...]
        }
      ]
    }
    """

    bullet_blocks: List[Dict[str, Any]] = []

    for unit in units:
        if unit.get("unit_type") != "page":
            continue

        pages = unit.get("pages", [])
        if not isinstance(pages, list):
            raise ValueError(
                f"[extract_bullets] page unit missing pages: {unit}"
            )

        for page_idx, page in enumerate(pages):
            p_indices = page.get("paragraph_indices", [])
            if not isinstance(p_indices, list):
                raise ValueError(
                    f"[extract_bullets] page missing paragraph_indices: {page}"
                )

            for p_idx in p_indices:
                text = paragraphs[p_idx]

                prompt = build_prompt(header, text, p_idx)
                result = llm.call_json(prompt)

                bullet_points = result.get("bullet_points", [])

                bullet_blocks.append({
                    "unit_id": unit.get("unit_id"),
                    "page_index": page_idx,
                    "paragraph_index": p_idx,
                    "bullet_points": bullet_points,
                })

    return {
        "header": header,
        "bullet_blocks": bullet_blocks,
    }
