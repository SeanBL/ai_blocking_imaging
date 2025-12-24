from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any

from ...utils.llm_client_realtime import LLMClientRealtime


# -----------------------------------------------------------
# Load prompt from src/config
# -----------------------------------------------------------

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]     # → src/
    / "config"
    / "prompt_button_labels.txt"
)

if not PROMPT_PATH.exists():
    raise FileNotFoundError(f"Button label prompt not found: {PROMPT_PATH}")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    BUTTON_LABEL_PROMPT = f.read()


# -----------------------------------------------------------
# Build prompt helpers (unchanged)
# -----------------------------------------------------------

def _build_engage_label_prompt(header: str, text: str, p_idx: int) -> str:
    return (
        BUTTON_LABEL_PROMPT
        .replace("<<<HEADER>>>", header)
        .replace("<<<INDEX>>>", str(p_idx))
        .replace("<<<TEXT>>>", text)
        .replace("<<<TYPE>>>", "engage")
    )


def _build_engage2_label_prompt(header: str, combined_text: str) -> str:
    return (
        BUTTON_LABEL_PROMPT
        .replace("<<<HEADER>>>", header)
        .replace("<<<INDEX>>>", "0")
        .replace("<<<TEXT>>>", combined_text)
        .replace("<<<TYPE>>>", "engage2")
    )


# -----------------------------------------------------------
# Main label generator (FINAL UNITS ONLY)
# -----------------------------------------------------------

def generate_labels(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
    llm: LLMClientRealtime,
) -> Dict[str, Any]:
    """
    Produces:
    {
      "header": "...",
      "engage_labels": [...],
      "engage2_labels": [...]
    }
    """

    engage_labels: List[Dict[str, Any]] = []
    engage2_labels: List[Dict[str, Any]] = []

    for unit in units:
        unit_type = unit.get("unit_type")

        # ----------------------------
        # ENGAGE: one label per item
        # ----------------------------
        if unit_type == "engage":
            for p_idx in unit.get("item_paragraphs", []):
                text = paragraphs[p_idx]

                prompt = _build_engage_label_prompt(header, text, p_idx)
                result = llm.call_json(prompt)

                label = (result.get("button_label") or "").strip()

                if not label:
                    words = text.split()
                    label = " ".join(words[:4]).rstrip(",.;")

                engage_labels.append({
                    "unit_id": unit.get("unit_id"),
                    "paragraph_index": p_idx,
                    "button_label": label,
                })

        # ----------------------------
        # ENGAGE2: one label per unit
        # ----------------------------
        elif unit_type == "engage2":
            p_indices = unit.get("paragraph_indices", [])
            combined_text = " ".join(paragraphs[i] for i in p_indices).strip()

            prompt = _build_engage2_label_prompt(header, combined_text)
            result = llm.call_json(prompt)

            label = (result.get("button_label") or "").strip()

            if not label:
                words = combined_text.split()
                label = " ".join(words[:4]).rstrip(",.;")

            engage2_labels.append({
                "unit_id": unit.get("unit_id"),
                "paragraph_indices": p_indices,
                "button_label": label,
            })

    return {
        "header": header,
        "engage_labels": engage_labels,
        "engage2_labels": engage2_labels,
    }
