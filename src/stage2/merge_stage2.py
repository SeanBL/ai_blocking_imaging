from __future__ import annotations
from typing import Dict, Any, List


def merge_blocks(
    stage2A: Dict[str, Any],
    stage2B: Dict[str, Any],
    stage2C: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stage 2D:
    Merge:
      - Stage 2A (rewritten pages, engage logic)
      - Stage 2B (image assignments)
      - Stage 2C (quiz generation)

    All structural fields from Stage 2A, including:
      engage_points
      engage_button_labels
      engage2_steps
      engage2_button_label
    MUST be preserved exactly.

    Output:
      {
        "header": ...,
        "pages": [...],
        "quiz": [...],
        "notes": optional
      }
    """

    header = (
        stage2A.get("header")
        or stage2B.get("header")
        or "Untitled Section"
    )

    # Stage 2B contains the pages WITH images applied.
    # All other structural fields (engage, engage2) must remain intact.
    pages_with_images: List[Dict[str, Any]] = stage2B.get("pages") or stage2A.get("pages") or []

    # Quiz items from stage2C
    quiz_items = stage2C.get("quiz", [])

    merged: Dict[str, Any] = {
        "header": header,
        "pages": pages_with_images,
        "quiz": quiz_items,
    }

    # If Stage 2A included notes, preserve them
    if "notes" in stage2A:
        merged["notes"] = stage2A["notes"]

    return merged