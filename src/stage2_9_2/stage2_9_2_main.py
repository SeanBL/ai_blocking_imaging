# src/stage2_9_2/stage2_9_2_main.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .flatten_quizzes import flatten_quizzes


BASE_DIR = Path("data/processed")

INPUT_PATH = BASE_DIR / "module_stage2_9.json"
OUTPUT_PATH = BASE_DIR / "quiz_flattened_stage2_9_2.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    print("[Stage 2.9.2] Loading Stage 2.8 output")
    module_json = load_json(INPUT_PATH)

    print("[Stage 2.9.2] Flattening quizzes")
    rows = flatten_quizzes(module_json)

    print(f"[Stage 2.9.2] Writing {len(rows)} rows → {OUTPUT_PATH}")
    write_json(OUTPUT_PATH, rows)

    print("[Stage 2.9.2] Complete")


if __name__ == "__main__":
    main()
