from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

from .llm_review import review_text_unit
from .llm_review_analysis import analyze_text_unit
from .schema import ReviewPayload
from .logger import logger
from .llm_engage_intro_bridge import propose_engage_intro_bridge

DEFAULT_INPUT = Path("data/processed/module_stage2.json")
DEFAULT_OUTPUT = Path("data/review/module_review_suggestions.json")

# -------------------------------------------------
# Canonical unit types for review prompts
# -------------------------------------------------
UNIT_TYPES = {
    "PANEL_PARAGRAPH": "panel_paragraph",
    "PANEL_BULLETS": "panel_bullets",
    "ENGAGE_INTRO": "engage1_intro",
    "ENGAGE_ITEM": "engage1_item",
    "ENGAGE2": "engage2",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_review(input_path: Path, output_path: Path) -> None:
    module = load_json(input_path)

    review: ReviewPayload = {
        "review_version": "v1",
        "source_stage": "pre_llm_pipeline",
        "slides": [],
    }

    for slide in module.get("slides", []):
        slide_id = slide.get("uuid")
        slide_type = slide.get("type")
        content = slide.get("content", {})

        blocks: List[Dict[str, Any]] = []

        # -------------------------------------------------
        # PANEL SLIDES
        # -------------------------------------------------
        if slide_type == "panel":
            for idx, block in enumerate(content.get("blocks", [])):
                block_type = block.get("type")

                if block_type == "paragraph":
                    original = block.get("text", "").strip()
                    if not original:
                        continue

                    result = review_text_unit(
                        unit_type=UNIT_TYPES["PANEL_PARAGRAPH"],
                        slide_id=slide_id,
                        content=original,
                    )

                    analysis = analyze_text_unit(
                        unit_type=UNIT_TYPES["PANEL_PARAGRAPH"],
                        slide_id=slide_id,
                        content=original,
                    )

                    blocks.append({
                        "block_id": f"{slide_id}_panel_paragraph_{idx}",
                        "type": "paragraph",
                        "original": original,
                        "suggested": result["suggested"],
                        "notes": result["notes"],
                        "analysis": analysis if analysis["flags"] else None,
                    })

                elif block_type == "bullets":
                    items = block.get("items", [])
                    if not items:
                        continue

                    original = "\n".join(f"• {item}" for item in items)

                    result = review_text_unit(
                        unit_type=UNIT_TYPES["PANEL_BULLETS"],
                        slide_id=slide_id,
                        content=original,
                    )

                    analysis = analyze_text_unit(
                        unit_type=UNIT_TYPES["PANEL_BULLETS"],
                        slide_id=slide_id,
                        content=original,
                    )

                    blocks.append({
                        "block_id": f"{slide_id}_panel_bullets_{idx}",
                        "type": "bullets",
                        "original": original,
                        "suggested": result["suggested"],
                        "notes": result["notes"],
                        "analysis": analysis if analysis["flags"] else None,
                    })

        # -------------------------------------------------
        # ENGAGE 1 SLIDES
        # -------------------------------------------------
        elif slide_type == "engage":
            if "items" not in slide:
                logger.warning(
                    f"[REVIEW] Engage slide {slide_id} has no 'items' key — nothing to review"
                )

            # ---- Intro text
            intro = slide.get("intro", {})
            intro_text = intro.get("text", "").strip()
            if intro_text:
                result = review_text_unit(
                    unit_type=UNIT_TYPES["ENGAGE_INTRO"],
                    slide_id=slide_id,
                    content=intro_text,
                )

                analysis = analyze_text_unit(
                    unit_type=UNIT_TYPES["ENGAGE_INTRO"],
                    slide_id=slide_id,
                    content=intro_text,
                )

                blocks.append({
                    "block_id": f"{slide_id}_engage1_intro",
                    "type": "paragraph",
                    "original": intro_text,
                    "suggested": result["suggested"],
                    "notes": result["notes"],
                    "analysis": analysis if analysis["flags"] else None,
                })

            # ---- OPTIONAL: Intro → Items bridge suggestion (review-only)
            if intro_text:
                item_texts: List[str] = []
                for item in slide.get("items", []):
                    for body in item.get("body", []):
                        txt = body.get("text", "").strip()
                        if txt:
                            item_texts.append(txt)

                if item_texts:
                    bridge = propose_engage_intro_bridge(
                        slide_id=slide_id,
                        intro_text=intro_text,
                        engage_items=item_texts,
                    )

                    if bridge["bridge"]:
                        blocks.append({
                            "block_id": f"{slide_id}_engage1_intro_bridge",
                            "type": "intro_bridge",
                            "original": None,
                            "suggested": bridge["bridge"],
                            "notes": bridge["rationale"]
                                or "Optional bridging sentence to connect intro to engage items.",
                            "analysis": None,
                        })

            # ---- Engage items
            for item_idx, item in enumerate(slide.get("items", [])):
                for body_idx, body in enumerate(item.get("body", [])):
                    original = body.get("text", "").strip()
                    if not original:
                        continue

                    result = review_text_unit(
                        unit_type=UNIT_TYPES["ENGAGE_ITEM"],
                        slide_id=slide_id,
                        content=original,
                    )

                    analysis = analyze_text_unit(
                        unit_type=UNIT_TYPES["ENGAGE_ITEM"],
                        slide_id=slide_id,
                        content=original,
                    )

                    blocks.append({
                        "block_id": f"{slide_id}_engage1_item_{item_idx}_{body_idx}",
                        "type": body.get("type"),
                        "original": original,
                        "suggested": result["suggested"],
                        "notes": result["notes"],
                        "analysis": analysis if analysis["flags"] else None,
                    })

        # -------------------------------------------------
        # ENGAGE 2 SLIDES
        # -------------------------------------------------
        elif slide_type == "engage2":
            for idx, block in enumerate(content.get("blocks", [])):
                original = block.get("text", "").strip()
                if not original:
                    continue

                result = review_text_unit(
                    unit_type=UNIT_TYPES["ENGAGE2"],
                    slide_id=slide_id,
                    content=original,
                )

                analysis = analyze_text_unit(
                    unit_type=UNIT_TYPES["ENGAGE2"],
                    slide_id=slide_id,
                    content=original,
                )

                blocks.append({
                    "block_id": f"{slide_id}_engage2_{idx}",
                    "type": block.get("type"),
                    "original": original,
                    "suggested": result["suggested"],
                    "notes": result["notes"],
                    "analysis": analysis if analysis["flags"] else None,
                })

        # -------------------------------------------------
        # SAVE SLIDE REVIEW
        # -------------------------------------------------
        if blocks:
            review["slides"].append({
                "slide_id": slide_id,
                "slide_type": slide_type,
                "blocks": blocks,
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, indent=2), encoding="utf-8")

    logger.info(f"Review suggestions written to {output_path}")


if __name__ == "__main__":
    run_review(DEFAULT_INPUT, DEFAULT_OUTPUT)
