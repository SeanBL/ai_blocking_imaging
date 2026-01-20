from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Set

from .text_extractors import (
    extract_word_text_fragments,
    extract_stage2_text_fragments,
    extract_stage1_text_fragments,
)
from .errors import FidelityAuditError

IGNORED_FRAGMENTS = {
    "button label",
    "button labels",
    "image",
    "english text",
    "notes and instructions",
}

# -------------------------------------------------
# Core audit
# -------------------------------------------------

def run_fidelity_audit(
    *,
    docx_path: Path,
    stage2_module: Dict[str, Any],
) -> None:
    """
    Run Stage 2.1 fidelity audit.

    Ensures that every meaningful text fragment present in the
    Word document appears somewhere in the Stage 2 output.

    Raises FidelityAuditError on failure.
    """

    word_fragments: List[str] = extract_word_text_fragments(docx_path)
    stage2_fragments: List[str] = extract_stage2_text_fragments(stage2_module)

    # Use set for fast coverage checks
    stage2_set: Set[str] = set(stage2_fragments)

    missing: List[str] = []

    for frag in word_fragments:
        if frag not in stage2_set:
            missing.append(frag)

    if missing:
        raise FidelityAuditError(missing_fragments=missing)

def run_stage2_preservation_audit(
    *,
    stage1_module: Dict[str, Any],
    stage2_module: Dict[str, Any],
) -> None:
    """
    OPTION A — Structural preservation audit.

    Ensures that Stage 2 did not DROP any content units
    produced by Stage 1.

    This audit checks structure and counts, not strings.
    """

    stage1_slides = stage1_module.get("slides", [])
    stage2_slides = stage2_module.get("slides", [])

    if len(stage1_slides) != len(stage2_slides):
        raise FidelityAuditError(
            missing_fragments=[
                f"Slide count mismatch: Stage 1 has {len(stage1_slides)}, "
                f"Stage 2 has {len(stage2_slides)}"
            ]
        )

    missing: list[str] = []

    for idx, (s1, s2) in enumerate(zip(stage1_slides, stage2_slides)):
        s1_type = s1.get("slide_type")
        s2_type = s2.get("type")

        # -------------------------
        # PANEL
        # -------------------------
        if s1_type == "panel" and s2_type == "panel":
            s1_blocks = s1.get("content", {}).get("blocks", [])
            s2_blocks = s2.get("content", {}).get("blocks", [])

            if len(s2_blocks) < len(s1_blocks):
                missing.append(
                    f"Panel slide {idx}: Stage 2 has fewer content blocks "
                    f"({len(s2_blocks)}) than Stage 1 ({len(s1_blocks)})"
                )

        # -------------------------
        # ENGAGE 1
        # -------------------------
        elif s1_type == "engage1" and s2_type == "engage":
            s1_items = s1.get("content", {}).get("items", [])
            s2_items = s2.get("items", [])

            if not s2.get("intro"):
                missing.append(f"Engage slide {idx}: missing intro in Stage 2")

            if len(s2_items) < len(s1_items):
                missing.append(
                    f"Engage slide {idx}: Stage 2 has fewer items "
                    f"({len(s2_items)}) than Stage 1 ({len(s1_items)})"
                )

            for i, item in enumerate(s2_items):
                body = item.get("body", [])
                if not body:
                    missing.append(
                        f"Engage slide {idx}, item {i}: missing body content"
                    )

        # -------------------------
        # ENGAGE 2
        # -------------------------
        elif s1_type == "engage2" and s2_type == "engage2":
            s1_blocks = s1.get("content", {}).get("blocks", [])
            s2_build = s2.get("build", [])

            if len(s2_build) < len(s1_blocks):
                missing.append(
                    f"Engage2 slide {idx}: Stage 2 build has fewer steps "
                    f"({len(s2_build)}) than Stage 1 blocks ({len(s1_blocks)})"
                )

        else:
            missing.append(
                f"Slide {idx}: type mismatch Stage 1={s1_type}, Stage 2={s2_type}"
            )

    if missing:
        raise FidelityAuditError(missing_fragments=missing)

