from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from .quiz_randomizer import randomize_mcq
from .quiz_normalizer import normalize_question


INPUT_PATH = Path("data/processed/module_stage2_8.json")
OUTPUT_PATH = Path("data/processed/module_stage2_9.json")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_quiz_slide(slide: Dict[str, Any]) -> None:
    """
    Normalize + randomize questions inside an existing quiz slide.
    """
    quiz_id = slide.get("quiz_id")

    if not quiz_id:
        raise ValueError("Quiz slide missing quiz_id")

    for q in slide.get("questions", []):
        if "questions" not in slide:
            raise RuntimeError(f"Quiz slide {quiz_id} missing questions array")
        
        qid = q.get("question_id")

        normalize_question(q)

        if q["type"] == "mcq":
            seed = f"{quiz_id}_{qid}"
            randomize_mcq(question=q, seed=seed)


def main() -> None:
    module = load_json(INPUT_PATH)

    quiz_slides = [
        s for s in module.get("slides", [])
        if s.get("slide_type") == "quiz"
    ]

    if not quiz_slides:
        raise RuntimeError(
            "Stage 2.9 invariant violated: "
            "no quiz slides found in module_stage2_8.json"
        )

    application_seen = False

    for slide in quiz_slides:
        if slide.get("placement") == "application":
            application_seen = True
        process_quiz_slide(slide)

    # 🔒 HARD ASSERTION
    if not application_seen:
        raise RuntimeError(
            "Stage 2.9 invariant violated: "
            "no application quiz slide found. "
            "Stage 2.8 MAIN failed to insert it."
        )

    write_json(OUTPUT_PATH, module)
    print(f"[Stage 2.9] Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

