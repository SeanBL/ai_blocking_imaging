from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .logger import logger
from .run_stage2_8 import run_stage2_8
from .quiz_slide_builder import build_inline_quiz_slide, build_final_quiz_slide
from .quiz_insert import insert_quiz_slides


# -------------------------------------------------
# File locations (match your repo structure)
# -------------------------------------------------

BASE_DIR = Path("data/processed")

STAGE2_7_PATH = BASE_DIR / "module_stage2_after_2_7.json"
STAGE2_6_PATH = BASE_DIR / "module_stage2_6.json"
OUTPUT_PATH  = BASE_DIR / "module_stage2_8.json"


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -------------------------------------------------
# Main entrypoint
# -------------------------------------------------

def main() -> None:
    logger.info("Stage 2.8 MAIN starting")

    # 1) Load Stage 2.7 (quiz markers + notes)
    logger.info(f"Loading Stage 2.7 canonical: {STAGE2_7_PATH}")
    module_stage2_7 = load_json(STAGE2_7_PATH)

    # 2) Load Stage 2.6 merged (final slide order)
    logger.info(f"Loading Stage 2.6 merged: {STAGE2_6_PATH}")
    module_stage2_6 = load_json(STAGE2_6_PATH)

    slides_container = module_stage2_6.get("slides")

    if isinstance(slides_container, dict):
        # Normalize dict-of-slides → ordered list
        slides = list(slides_container.values())
    elif isinstance(slides_container, list):
        slides = slides_container
    else:
        raise RuntimeError("Stage 2.6 module has invalid slides container")

    if not slides:
        raise RuntimeError("Stage 2.6 module has zero slides")

    # 3) Run Stage 2.8 orchestration (detect/extract/LLM/review)
    result = run_stage2_8(module_json=module_stage2_7)

    inline_quizzes = result.get("inline_quizzes", {})
    final_quizzes = result.get("final_quizzes", {})

    # 4) Build quiz slides
    inline_slide_specs = {}
    for quiz_id, data in inline_quizzes.items():
        inline_slide_specs[int(quiz_id)] = {
            "insert_after_index": data["insert_after_index"],
            "slide": build_inline_quiz_slide(
                quiz_id=int(quiz_id),
                questions=data["questions"],
            ),
        }

    final_slides = {}
    for quiz_id, data in final_quizzes.items():
        final_slides[int(quiz_id)] = build_final_quiz_slide(
            quiz_id=int(quiz_id),
            questions=data["questions"],
        )

    # 5) Insert quiz slides into Stage 2.6 slides
    logger.info("Inserting quiz slides into module")
    new_slides = insert_quiz_slides(
        slides=slides,
        inline_quizzes=inline_slide_specs,
        final_quizzes=final_slides,
    )

    # 6) Write output
    output_module = dict(module_stage2_6)
    output_module["slides"] = new_slides

    write_json(OUTPUT_PATH, output_module)

    logger.info(f"Stage 2.8 MAIN complete — wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
