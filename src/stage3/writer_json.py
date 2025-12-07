from __future__ import annotations
import json
import pathlib
from typing import Dict, Any, List


def save_block_json(block: Dict[str, Any], output_path: pathlib.Path) -> None:
    """
    Save ONE block's final JSON to a file (used for per-block outputs).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(block, f, indent=2, ensure_ascii=False)


def build_full_module_json(stage2_dir: pathlib.Path) -> Dict[str, Any]:
    """
    Reads ALL Stage 2D block JSON files and merges them into
    a single module JSON structure:

    {
        "module_title": "...",
        "blocks": [
            { ...block1... },
            { ...block2... }
        ]
    }
    """
    module_data = {
        "module_title": None,
        "blocks": []
    }

    json_files = sorted(stage2_dir.glob("*.json"))

    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            block = json.load(f)

        # Derive module_title from the first block header
        if module_data["module_title"] is None:
            module_data["module_title"] = block.get("header", "Untitled Module")

        module_data["blocks"].append(block)

    return module_data


def save_full_module_json(module_json: Dict[str, Any], output_path: pathlib.Path) -> None:
    """
    Saves the consolidated module JSON.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(module_json, f, indent=2, ensure_ascii=False)
    print(f"Full module JSON written to: {output_path}")