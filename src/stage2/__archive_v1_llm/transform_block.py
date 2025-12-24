from __future__ import annotations
from typing import Dict, Any, List, Optional

from ..stage1.stage1_parse import ParsedBlock
from ..utils.llm_client_realtime import LLMClientRealtime

# ---------- Stage 2A ----------
from pathlib import Path
from .aggregate.aggregate_by_header import aggregate_blocks_by_header
from .structure.stage2A1_units import build_semantic_units
from .structure.stage2A2_units import assign_final_units

# ---------- Stage 2B ----------
from .structure.stage2B_pack import stage2B_pack_units

# ---------- Stage 2C+ ----------
from .engage.extract_engage import extract_engage_data
from .engage2.extract_engage2 import extract_engage2
from .bullets.extract_bullets import extract_bullets
from .labels.generate_labels import generate_labels
from .images.select_images import select_images
from .quiz.generate_quiz import generate_quiz
from .merge.merge_stage2 import merge_stage2


# -----------------------------------------------------------
# Main Stage 2 Orchestrator (FIXED)
# -----------------------------------------------------------
def transform_block(
    parsed_block: ParsedBlock,
    llm: LLMClientRealtime,
    image_catalog: Optional[List[Dict[str, Any]]] = None,
    return_all: bool = False,
) -> Dict[str, Any]:

    if image_catalog is None:
        image_catalog = []

    header = parsed_block.header

    # -------------------------------------------------------
    # 🚨 GUARD: skip non-instructional / empty-header blocks
    # -------------------------------------------------------
    if not header:
        return {
            "header": "",
            "skipped": True,
            "reason": "Empty header in Stage 1 block",
        }

    # ---------- Stage 2A0: aggregate ALL blocks under this header ----------
    stage1_dir = Path(__file__).resolve().parents[2] / "data/processed/stage1_blocks"

    aggregated_all = aggregate_blocks_by_header(
        header=parsed_block.header,
        stage1_dir=stage1_dir,
    )

    if header not in aggregated_all:
        raise ValueError(f"No aggregated blocks found for header: {header}")

    aggregated = aggregated_all[header]

    paragraphs = [p["text"] for p in aggregated["paragraphs"]]

    # -------------------------------------------------------
    # Stage 2A1 — semantic grouping (LLM)
    # -------------------------------------------------------
    semantic_units = build_semantic_units(
        header=header,
        paragraphs=paragraphs,
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2A2 — assign final instructional roles (LLM)
    # -------------------------------------------------------
    unit_plan = assign_final_units(
        header=header,
        paragraphs=paragraphs,
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2B — deterministic page packing (NO LLM)
    # -------------------------------------------------------
    packed_units = stage2B_pack_units(
        unit_plan=unit_plan,
        paragraphs=paragraphs,
    )

    # 🔒 STRUCTURE IS NOW FROZEN 🔒
    final_units = packed_units["units"]

    # -------------------------------------------------------
    # Stage 2C — Engage extraction
    # -------------------------------------------------------
    engage_data = extract_engage_data(
        header=header,
        paragraphs=paragraphs,
        units=final_units,
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2C.1 — Engage2 extraction
    # -------------------------------------------------------
    engage2_data = extract_engage2(
        header=header,
        paragraphs=paragraphs,
        units=final_units,
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2D — Bullet extraction
    # -------------------------------------------------------
    bullet_data = extract_bullets(
        header=header,
        paragraphs=paragraphs,
        units=final_units,
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2E — Button labels
    # -------------------------------------------------------
    labels_data = generate_labels(
        header=header,
        engage_items=engage_data.get("engage_items", []),
        engage2_items=engage2_data.get("engage2_items", []),
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2F — Images
    # -------------------------------------------------------
    images_data = select_images(
        header=header,
        pages=final_units,
        image_catalog=image_catalog,
        llm=llm,
    )

    # -------------------------------------------------------
    # Stage 2G — Quiz
    # -------------------------------------------------------
    quiz_full = generate_quiz(
        {
            "header": header,
            "units": final_units,
        },
        llm,
    )

    # -------------------------------------------------------
    # Stage 2H — Merge final output
    # -------------------------------------------------------
    merged_block = merge_stage2(
        header=header,
        paragraphs=paragraphs,
        units=final_units,
        engage_data=engage_data,
        engage2_data=engage2_data,
        labels_data=labels_data,
        images_data=images_data,
        quiz_data=quiz_full,
        bullet_data=bullet_data,
        notes=None,
    )

    if return_all:
        return {
            "semantic_units": semantic_units,
            "unit_plan": unit_plan,
            "packed_units": packed_units,
            "engage": engage_data,
            "engage2": engage2_data,
            "bullets": bullet_data,
            "labels": labels_data,
            "images": images_data,
            "quiz": quiz_full,
            "merged": merged_block,
        }

    return merged_block



