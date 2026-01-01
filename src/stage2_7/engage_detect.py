import re
from typing import Dict, Optional


# -----------------------------
# Regex for Engage intent
# -----------------------------
ENGAGE1_RE = re.compile(r"slide\s*type\s*=\s*engage\s*1", re.I)
ENGAGE2_RE = re.compile(r"slide\s*type\s*=\s*engage\s*2", re.I)


def _norm(text: Optional[str]) -> str:
    return " ".join((text or "").split()).strip()


def _find_engage_block(slide: Dict, engage_type: str) -> Optional[Dict]:
    """
    In Stage 2 output, engage blocks live at the TOP LEVEL of the slide.
    """
    if slide.get("type") == engage_type:
        return slide
    return None



def _engage1_is_complete(block: Dict) -> bool:
    """
    Engage 1 is considered authored ONLY if:
    - items exists and is non-empty
    - each item has button_label
    - each item has image key (even if null)
    - each item has content/text
    """
    items = block.get("items")
    if not items or not isinstance(items, list):
        return False

    for item in items:
        if not isinstance(item, dict):
            return False

        if not _norm(item.get("button_label")):
            return False

        if "image" not in item:
            return False

        # Support both legacy 'content' and newer 'text' shapes
        if not item.get("content") and not _norm(item.get("text")):
            return False

    return True


def detect_engage_need(slide: Dict) -> Optional[Dict]:
    """
    Decide whether this slide needs Engage synthesis.

    Returns:
      None → pass-through
      { engage_type, reason } → synthesize
    """
    notes = _norm(slide.get("notes") or slide.get("notes_raw"))

    if not notes:
        return None

    if ENGAGE2_RE.search(notes):
        engage_type = "engage2"
    elif ENGAGE1_RE.search(notes):
        engage_type = "engage"
    else:
        return None

    block = _find_engage_block(slide, engage_type)

    # --- Engage 1 logic ---
    if engage_type == "engage":
        # No engage block at all → synthesize
        if block is None:
            return {
                "engage_type": "engage",
                "reason": "missing_engage_block"
            }

        # Engage block exists but is incomplete (Stage 2 artifact) → synthesize
        if not _engage1_is_complete(block):
            return {
                "engage_type": "engage",
                "reason": "incomplete_engage1"
            }

        # Fully authored → do nothing
        return None

    # --- Engage 2 logic (conservative for now) ---
    if engage_type == "engage2":
        # If no engage2 block exists, allow synthesis
        if block is None:
            return {
                "engage_type": "engage2",
                "reason": "missing_engage2_block"
            }

        # If it exists, assume authored for now
        return None

    return None
