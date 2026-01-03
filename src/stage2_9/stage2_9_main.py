# src/stage2_9/stage2_9_main.py
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


def process_quiz(quiz: Dict[str, Any]) -> Dict[str, Any]:
    quiz_id = quiz["quiz_id"]

    for q in quiz["questions"]:
        qid = q["question_id"]

        q = normalize_question(q)

        if q["type"] == "mcq":
            seed = f"{quiz_id}_{qid}"
            randomize_mcq(question=q, seed=seed)

    return quiz


def main() -> None:
    module = load_json(INPUT_PATH)

    for slide in module.get("slides", []):
        if slide.get("slide_type") == "quiz":
            process_quiz(slide)

    write_json(OUTPUT_PATH, module)
    print(f"[Stage 2.9] Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
