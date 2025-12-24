from __future__ import annotations
import json
import pathlib
from typing import Dict, Any, List


def save_block_json(block: Dict[str, Any], output_path: pathlib.Path) -> None:
    """
    Save ONE block's final JSON to a file (used for per-block outputs).
    This includes blueprints, labels, bullets, images, quiz, etc.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(block, f, indent=2, ensure_ascii=False)


def build_full_module_json(stage2_dir: pathlib.Path) -> Dict[str, Any]:
    """
    Reads ALL Stage 2G_final JSON blocks and merges them into:

    {
        "module_title": "...",
        "blocks": [...],      # all merged blocks INCLUDING blueprints
        "final_exam": [...]   # aggregated final exam questions
    }

    • Inline quizzes stay inside blocks
    • Reserved questions go into final_exam[]
    • Blueprint fields are preserved exactly (Option-C)
    """
    module_data = {
        "module_title": None,
        "blocks": [],
        "final_exam": [],
    }

    json_files = sorted(stage2_dir.glob("*.json"))

    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            block = json.load(f)

        # -----------------------------------------
        # Module Title (first block header)
        # -----------------------------------------
        if module_data["module_title"] is None:
            module_data["module_title"] = block.get("header", "Untitled Module")

        # -----------------------------------------
        # Extract reserved questions
        # -----------------------------------------
        quiz_list: List[Dict[str, Any]] = block.get("quiz", [])

        for q in quiz_list:
            if q.get("reserve_for_final_exam"):
                module_data["final_exam"].append({
                    "header": block.get("header", ""),
                    **q
                })

        # -----------------------------------------
        # KEEP ALL block fields, including blueprints
        # (Option-C requirement)
        # -----------------------------------------
        module_data["blocks"].append(block)

    return module_data


def save_full_module_json(module_json: Dict[str, Any], output_path: pathlib.Path) -> None:
    """
    Save consolidated module JSON (with blueprints preserved).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(module_json, f, indent=2, ensure_ascii=False)
    print(f"Full module JSON written to: {output_path}")

