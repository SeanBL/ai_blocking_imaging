from __future__ import annotations

from typing import Any, Dict, Tuple
import re

from .validators import word_count, sentence_count, button_label_invalid
from .schemas import (
    PANEL_LENGTH_ANALYSIS_ACTIONS,
    ENGAGE_ITEM_STATUS,
    BUTTON_TARGETS,
    REQUIRED_SAFETY_KEYS,
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _fail(reason: str) -> Tuple[bool, Dict[str, Any]]:
    return False, {"rejected": True, "reason": reason}


def _ok(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    return True, data


# --------------------------------------------------
# Safety block (shared)
# --------------------------------------------------

def validate_safety(obj: Any) -> Tuple[bool, Dict[str, Any]]:
    if not isinstance(obj, dict):
        return _fail("safety must be an object")

    missing = REQUIRED_SAFETY_KEYS - set(obj.keys())
    if missing:
        return _fail(f"safety missing keys: {sorted(missing)}")

    for k in REQUIRED_SAFETY_KEYS:
        if not isinstance(obj.get(k), bool):
            return _fail(f"safety.{k} must be boolean")

    return _ok(obj)


# --------------------------------------------------
# Panel block split (unchanged)
# --------------------------------------------------

def validate_panel_length_analysis(obj: Any) -> Tuple[bool, Dict[str, Any]]:
    if not isinstance(obj, dict):
        return _fail("panel_length_analysis must be an object")

    pla = obj.get("panel_length_analysis")
    if not isinstance(pla, dict):
        return _fail("missing panel_length_analysis object")

    action = pla.get("action")
    if action not in PANEL_LENGTH_ANALYSIS_ACTIONS:
        return _fail("invalid panel_length_analysis.action")

    reason = pla.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return _fail("panel_length_analysis.reason must be non-empty")

    suggested_panels = pla.get("suggested_panels", [])

    if action == "split":
        if not isinstance(suggested_panels, list) or len(suggested_panels) < 2:
            return _fail("split requires >= 2 suggested_panels")

        for i, p in enumerate(suggested_panels):
            if not isinstance(p, dict):
                return _fail(f"suggested_panels[{i}] must be object")

            content = p.get("content")
            if not isinstance(content, list) or not all(isinstance(x, str) for x in content):
                return _fail(f"suggested_panels[{i}].content must be list[str]")

            text = " ".join(content)
            wc = word_count(text)
            sc = sentence_count(text)

            if wc < 30 or wc > 70:
                return _fail(f"suggested_panels[{i}] violates 30–70 words")
            if sc > 3:
                return _fail(f"suggested_panels[{i}] exceeds 3 sentences")

    ok, safety = validate_safety(obj.get("safety"))
    if not ok:
        return ok, safety

    return _ok(obj)


# --------------------------------------------------
# STRICT sentence boundary validation (NEW)
# --------------------------------------------------

def validate_sentence_boundaries(obj: Any, original_text: str) -> Tuple[bool, Dict[str, Any]]:
    if not isinstance(obj, dict):
        return _fail("sentence_boundaries must be object")

    sb = obj.get("sentence_boundaries")
    if not isinstance(sb, dict):
        return _fail("missing sentence_boundaries object")

    if sb.get("action") != "reflow":
        return _fail("sentence_boundaries.action must be 'reflow'")

    indexes = sb.get("indexes")
    if not isinstance(indexes, list):
        return _fail("sentence_boundaries.indexes must be list")

    text_len = len(original_text)

    for idx in indexes:
        if not isinstance(idx, int):
            return _fail("sentence boundary index must be integer")
        if idx <= 0 or idx >= text_len:
            return _fail("sentence boundary index out of range")

    if len(indexes) > 2:
        return _fail("maximum of 3 sentences allowed")

    ok, safety = validate_safety(obj.get("safety"))
    if not ok:
        return ok, safety

    return _ok(obj)


# --------------------------------------------------
# Engage + button validators (unchanged)
# --------------------------------------------------

def validate_engage1_item_review(obj: Any) -> Tuple[bool, Dict[str, Any]]:
    review = obj.get("engage1_item_review")
    if not isinstance(review, list):
        return _fail("missing engage1_item_review list")

    for i, r in enumerate(review):
        if not isinstance(r, dict):
            return _fail(f"engage1_item_review[{i}] must be object")
        if not isinstance(r.get("item_index"), int):
            return _fail("item_index must be int")
        if not isinstance(r.get("word_count"), int):
            return _fail("word_count must be int")
        if r.get("status") not in ENGAGE_ITEM_STATUS:
            return _fail("invalid engage item status")

    ok, safety = validate_safety(obj.get("safety"))
    if not ok:
        return ok, safety

    return _ok(obj)


def validate_button_label_suggestions(obj: Any) -> Tuple[bool, Dict[str, Any]]:
    bls = obj.get("button_label_suggestions")
    if not isinstance(bls, list):
        return _fail("missing button_label_suggestions list")

    for s in bls:
        if not isinstance(s, dict):
            return _fail("button_label_suggestion must be object")
        if s.get("target") not in BUTTON_TARGETS:
            return _fail("invalid button_label target")

        label = s.get("suggested_label")
        if not isinstance(label, str) or button_label_invalid(label):
            return _fail("invalid button label")

    ok, safety = validate_safety(obj.get("safety"))
    if not ok:
        return ok, safety

    return _ok(obj)

def validate_strict_sentence_boundaries(
    obj: Any,
    *,
    original_text: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    STRICT validator:
    - LLM may ONLY return character indexes
    - Text must reconstruct IDENTICALLY
    - No wording changes allowed
    """

    if not isinstance(obj, dict):
        return _fail("strict_sentence_boundaries must be an object")

    reflow = obj.get("sentence_reflow")
    if not isinstance(reflow, dict):
        return _fail("missing sentence_reflow object")

    if reflow.get("action") != "reflow":
        return _fail("sentence_reflow.action must be 'reflow'")

    indexes = reflow.get("indexes")
    if not isinstance(indexes, list) or not indexes:
        return _fail("indexes must be a non-empty list")

    if not all(isinstance(i, int) for i in indexes):
        return _fail("indexes must be integers")

    if indexes != sorted(indexes):
        return _fail("indexes must be sorted")

    if indexes[0] != 0:
        return _fail("first index must be 0")

    text_len = len(original_text)
    if any(i < 0 or i >= text_len for i in indexes):
        return _fail("index out of bounds")

    # ------------------------------------
    # STRICT RECONSTRUCTION CHECK
    # ------------------------------------
    chunks = []
    for i, start in enumerate(indexes):
        end = indexes[i + 1] if i + 1 < len(indexes) else text_len
        chunks.append(original_text[start:end])

    reconstructed = "".join(chunks)
    if reconstructed != original_text:
        return _fail("STRICT MODE VIOLATION: text mismatch")

    # ------------------------------------
    # SAFETY
    # ------------------------------------
    ok, safety = validate_safety(obj.get("safety"))
    if not ok:
        return ok, safety

    return _ok(obj)


