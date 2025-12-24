from __future__ import annotations
from typing import Dict, Any, List

from .pack_pages import pack_paragraphs


def stage2B_pack_units(
    unit_plan: Dict[str, Any],
    paragraphs: List[str],
) -> Dict[str, Any]:

    output_units = []

    for unit in unit_plan["final_units"]:
        unit_type = unit["unit_type"]

        if unit_type == "page":
            all_indices = [
                idx
                for group in unit["paragraph_groups"]
                for idx in group
            ]

            pages = pack_paragraphs(all_indices, paragraphs)

            output_units.append({
                "unit_id": unit["unit_id"],
                "unit_type": "page",
                "pages": pages,
            })

        elif unit_type == "engage":
            items = []

            for idx in unit["item_paragraphs"]:
                pages = pack_paragraphs([idx], paragraphs)
                items.append({"pages": pages})

            output_units.append({
                "unit_id": unit["unit_id"],
                "unit_type": "engage",
                "intro": {"paragraph_index": unit["intro_paragraph"]},
                "items": items,
            })

        elif unit_type == "engage2":
            step_paragraphs = unit.get("step_paragraphs", [])

            # If no steps, skip safely
            if not step_paragraphs:
                output_units.append({
                    "unit_id": unit["unit_id"],
                    "unit_type": "engage2",
                    "intro": {"paragraph_index": unit["intro_paragraph"]},
                    "pages": [],
                })
                continue

            pages = pack_paragraphs(
                step_paragraphs,
                paragraphs,
            )

            output_units.append({
                "unit_id": unit["unit_id"],
                "unit_type": "engage2",
                "intro": {"paragraph_index": unit["intro_paragraph"]},
                "pages": pages,
            })

    return {
        "header": unit_plan["header"],
        "units": output_units,
    }
