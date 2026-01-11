# src/stage2_5/apply_splits.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def apply_stage2_5_splits(
    module_stage2: Dict[str, Any],
    stage2_5: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply Stage 2.5 panel split decisions to the module.

    Rules:
    - Preserve slide order
    - Preserve text EXACTLY
    - Preserve notes, images, metadata
    - Apply splits ONLY when panel_final.action == "split"
    - Never touch engage slides
    - Never call LLM
    """

    new_slides: List[Dict[str, Any]] = []

    s25_slides = stage2_5.get("slides", {})

    for slide in module_stage2.get("slides", []):
        slide_id = slide.get("id")
        slide_type = slide.get("slide_type") or slide.get("type")

        s25_entry = s25_slides.get(slide_id)

        # --------------------------------------------------
        # PASS THROUGH: no Stage 2.5 entry
        # --------------------------------------------------
        if not s25_entry:
            if "slide_type" not in slide and "type" in slide:
                slide = dict(slide)
                slide["slide_type"] = slide["type"]
            new_slides.append(slide)
            continue

        panel_final = s25_entry.get("panel_final")

        # --------------------------------------------------
        # PASS THROUGH: no panel_final or keep
        # --------------------------------------------------
        if not panel_final or panel_final.get("action") == "keep":
            new_slides.append(slide)
            continue

        # --------------------------------------------------
        # SAFETY: only panels may be split
        # --------------------------------------------------
        if slide_type != "panel":
            new_slides.append(slide)
            continue

        # --------------------------------------------------
        # APPLY SPLIT
        # --------------------------------------------------
        proposed_panels = panel_final.get("slides", [])
        if not isinstance(proposed_panels, list) or not proposed_panels:
            raise RuntimeError(
                f"Stage 2.5 APPLY ERROR: split requested but no panels provided "
                f"(slide_id={slide_id})"
            )

        for idx, panel in enumerate(proposed_panels):

            raw_content = panel.get("content", [])

            # ----------------------------------
            # 🔒 CANONICALIZE TO PARAGRAPH BLOCKS
            # ----------------------------------
            blocks: List[Dict[str, Any]] = []

            if isinstance(raw_content, str):
                blocks.append({
                    "type": "paragraph",
                    "text": raw_content,
                })

            elif isinstance(raw_content, list):
                for item in raw_content:
                    if isinstance(item, dict):
                        # already a block (rare but safe)
                        blocks.append(item)
                    elif isinstance(item, str):
                        blocks.append({
                            "type": "paragraph",
                            "text": item,
                        })

            new_slide = {
                "id": f"{slide_id}__p{idx + 1}",
                "header": panel.get("header"),
                "slide_type": "panel",
                "image": slide.get("image"),
                "notes": slide.get("notes"),
                "content": {
                    "blocks": blocks,
                },
            }

            new_slides.append(new_slide)


    out = dict(module_stage2)
    out["slides"] = new_slides
    return out


# --------------------------------------------------
# CLI entry
# --------------------------------------------------
def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage:\n"
            "  python -m src.stage2_5.apply_splits "
            "<module_stage2.json> "
            "<stage2_5_suggestions.json> "
            "<out_module_stage2_5_applied.json>\n"
        )
        return 2

    in_module = Path(argv[1])
    in_s25 = Path(argv[2])
    out_path = Path(argv[3])

    module_stage2 = load_json(in_module)
    stage2_5 = load_json(in_s25)

    applied = apply_stage2_5_splits(module_stage2, stage2_5)
    write_json(out_path, applied)

    print(f"✅ Stage 2.5 APPLY complete → {out_path}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv))
