from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .logger import logger
from .run_stage2_8 import run_stage2_8
from .quiz_slide_builder import build_inline_quiz_slide, build_final_quiz_slide
from .quiz_insert import insert_quiz_slides


BASE_DIR = Path("data/processed")

STAGE2_5_APPLIED_PATH = BASE_DIR / "module_stage2_after_2_5.json"
STAGE2_6_PATH = BASE_DIR / "module_stage2_6.json"
OUTPUT_PATH  = BASE_DIR / "module_stage2_8.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _insert_application_slides_before_final(
    *,
    slides: list,
    module_application_quizzes: Dict[int, Dict[str, Any]],
) -> list:
    """
    Insert quiz_{id}_application immediately before quiz_{id}_final.
    Hard-assert if application questions exist but no insertion happens.
    """
    inserted = 0

    for quiz_id, payload in module_application_quizzes.items():
        questions = payload.get("questions", [])
        if not questions:
            continue

        app_slide = {
            "id": f"quiz_{quiz_id}_application",
            "slide_type": "quiz",
            "quiz_id": int(quiz_id),
            "placement": "application",
            "questions": questions,
        }

        final_id = f"quiz_{quiz_id}_final"
        final_index = next((i for i, s in enumerate(slides) if s.get("id") == final_id), None)

        if final_index is None:
            # If final slide isn't present for some reason, append application at end.
            slides.append(app_slide)
        else:
            slides.insert(final_index, app_slide)

        inserted += 1

    if module_application_quizzes and inserted == 0:
        raise AssertionError(
            "Stage 2.8 MAIN: module_application_quizzes existed but no application slide was inserted."
        )

    return slides


def main() -> None:
    logger.info("Stage 2.8 MAIN starting")

    logger.info(f"Loading Stage 2.5 canonical (post-split): {STAGE2_5_APPLIED_PATH}")
    logger.info(f"Loading Stage 2.6 annotations: {STAGE2_6_PATH}")
    module_stage2 = load_json(STAGE2_5_APPLIED_PATH)
    stage2_6 = load_json(STAGE2_6_PATH)

    logger.info(
        "DEBUG Stage 2.6 structure | "
        f"type(stage2_6)={type(stage2_6)} | "
        f"type(stage2_6['slides'])="
        f"{type(stage2_6.get('slides')) if isinstance(stage2_6, dict) else 'N/A'}"
    )

    slides = module_stage2.get("slides")
    if not isinstance(slides, list) or not slides:
        raise RuntimeError("Stage 2.5 module has invalid or empty slides")

    # ----------------------------
    # Run Stage 2.8 orchestration
    # ----------------------------
    result = run_stage2_8(
        module_json=module_stage2,
        sentence_annotations=stage2_6,
    )

    inline_quizzes = result.get("inline_quizzes", {})
    final_quizzes = result.get("final_quizzes", {})
    module_application_quizzes = result.get("module_application_quizzes", {})  # ✅ FIX

    # ----------------------------
    # Build inline quiz slide specs
    # ----------------------------
    inline_slide_specs: Dict[int, Dict[str, Any]] = {}
    for quiz_id, data in inline_quizzes.items():
        inline_slide_specs[int(quiz_id)] = {
            "insert_after_index": data["insert_after_index"],
            "slide": build_inline_quiz_slide(
                quiz_id=int(quiz_id),
                questions=data["questions"],
            ),
        }

    # ----------------------------
    # Build final quiz slides
    # ----------------------------
    final_slides: Dict[int, Dict[str, Any]] = {}
    for quiz_id, data in final_quizzes.items():
        final_slides[int(quiz_id)] = build_final_quiz_slide(
            quiz_id=int(quiz_id),
            questions=data["questions"],
        )

    # ----------------------------
    # Insert inline + final slides
    # ----------------------------
    logger.info("Inserting quiz slides into module")
    new_slides = insert_quiz_slides(
        slides=slides,
        inline_quizzes=inline_slide_specs,
        final_quizzes=final_slides,
    )

    # ----------------------------
    # ✅ Insert application slides before final
    # ----------------------------
    if module_application_quizzes:
        logger.info(
            f"Inserting application quiz slides — count={len(module_application_quizzes)}"
        )

        # Ensure quiz_id keys are ints (defensive)
        module_application_quizzes_int: Dict[int, Dict[str, Any]] = {
            int(k): v for k, v in module_application_quizzes.items()
        }

        new_slides = _insert_application_slides_before_final(
            slides=new_slides,
            module_application_quizzes=module_application_quizzes_int,
        )
        
        logger.info(
            "Post-insertion quiz slide order:\n" +
            "\n".join(
                f"{i}: {s.get('id')} ({s.get('placement')})"
                for i, s in enumerate(new_slides)
                if s.get("slide_type") == "quiz"
            )
        )

    # ----------------------------
    # Write output
    # ----------------------------
    output_module = dict(module_stage2)
    output_module["slides"] = new_slides

    write_json(OUTPUT_PATH, output_module)

    logger.info(f"Stage 2.8 MAIN complete — wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

