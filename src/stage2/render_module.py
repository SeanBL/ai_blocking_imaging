# src/stage2/render_module.py

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def render_module(module_stage2, stage2_5, stage2_6):
    output_slides = []

    s25_slides = stage2_5.get("slides", {})
    s26_slides = stage2_6.get("slides", {})

    for slide in module_stage2["slides"]:
        slide_id = slide["id"]
        slide_type = slide["type"]

        # --------------------------------------------------
        # RULE 1 — Engage slides: pass through untouched
        # --------------------------------------------------
        if slide_type in ("engage", "engage2"):
            output_slides.append(slide)
            continue

        s25 = s25_slides.get(slide_id)
        s26 = s26_slides.get(slide_id)

        # --------------------------------------------------
        # RULE 2 — No Stage 2.5 decision → pass through
        # --------------------------------------------------
        if not s25 or "panel_final" not in s25:
            output_slides.append(slide)
            continue

        pf = s25["panel_final"]

        # --------------------------------------------------
        # RULE 3 — Bullet panels → NEVER touched
        # --------------------------------------------------
        if pf.get("reason") == "bullet_panel":
            output_slides.append(slide)
            continue

        # --------------------------------------------------
        # RULE 4 — Stage 2.6 sentence shaping exists
        # --------------------------------------------------
        if s26 and s26.get("sentence_blocks"):
            for idx, sb in enumerate(s26["sentence_blocks"], start=1):
                output_slides.append({
                    "id": sb["block_id"],
                    "type": "panel",
                    "header": (
                        slide["header"]
                        if idx == 1
                        else f"{slide['header']} (continued)"
                    ),
                    "content": sb["sentences"],
                    "content_blocks": sb["sentences"],
                })
            continue

        # --------------------------------------------------
        # RULE 5 — Stage 2.5 split only (no sentence shaping)
        # --------------------------------------------------
        for idx, p in enumerate(pf["slides"], start=1):
            output_slides.append({
                "id": slide_id if idx == 1 else f"{slide_id}_p{idx}",
                "type": "panel",
                "header": p["header"],
                "content": p["content"],
                "content_blocks": [p["content"]],
            })

    return {
        "module_title": module_stage2["module_title"],
        "slides": output_slides,
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "Usage:\n"
            "  python -m src.stage2.render_module "
            "<module_stage2.json> "
            "<stage2_5_suggestions.json> "
            "<stage2_6_suggestions.json> "
            "<out_module_stage2_final.json>"
        )
        return 2

    module_path = Path(argv[1])
    s25_path = Path(argv[2])
    s26_path = Path(argv[3])
    out_path = Path(argv[4])

    module_stage2 = load_json(module_path)
    stage2_5 = load_json(s25_path)
    stage2_6 = load_json(s26_path)

    final_module = render_module(
        module_stage2,
        stage2_5,
        stage2_6,
    )

    write_json(out_path, final_module)
    print(f"Stage 2 final module written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
