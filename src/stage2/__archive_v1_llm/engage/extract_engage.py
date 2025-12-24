from __future__ import annotations
from typing import Dict, Any, List

# ----------------------------------------------------
# MAIN EXTRACTION FUNCTION
# ----------------------------------------------------

def extract_engage_data(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Produces:
    {
      "header": "...",
      "engage_items": [
        { "paragraph_index": 3, "text": "..." },
        ...
      ]
    }

    NOTE:
    - Consumes FINAL UNITS ONLY
    - Processes ONLY unit_type == "engage"
    - engage2 intentionally ignored
    """

    engage_items: List[Dict[str, Any]] = []

    for unit in units:
        if unit.get("unit_type") != "engage":
            continue

        # ----------------------------------
        # Normalize intro paragraph index
        # ----------------------------------
        if "intro" in unit and isinstance(unit["intro"], dict):
            intro_idx = unit["intro"].get("paragraph_index")
        else:
            # No valid intro → skip safely
            continue

        if not isinstance(intro_idx, int):
            continue

        # ----------------------------------
        # Normalize item paragraphs
        # items -> pages -> paragraph_indices
        # ----------------------------------
        for item in unit.get("items", []):
            for page in item.get("pages", []):
                for p_idx in page.get("paragraph_indices", []):
                    if not isinstance(p_idx, int):
                        continue

                    engage_items.append({
                        "paragraph_index": p_idx,
                        "text": paragraphs[p_idx],
                    })

    return {
        "header": header,
        "engage_items": engage_items,
    }

