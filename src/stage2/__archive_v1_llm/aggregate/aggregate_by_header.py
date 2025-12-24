from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

def aggregate_blocks_by_header(
    stage1_dir: Path,
) -> Dict[str, Any]:
    """
    Stage 2A0:
    Aggregates all Stage 1 blocks by header and flattens paragraphs.

    Returns:
      {
        "<Header>": {
          "header": "<Header>",
          "paragraphs": [
            {
              "global_index": int,
              "text": str,
              "source_block": str,
              "local_index": int
            },
            ...
          ]
        },
        ...
      }
    """

    if not stage1_dir.exists():
        raise FileNotFoundError(f"Stage1 directory not found: {stage1_dir}")

    # --------------------------------------------------
    # Load all Stage 1 blocks (sorted for stability)
    # --------------------------------------------------
    block_paths = sorted(stage1_dir.glob("*.json"))

    # Group blocks by header
    blocks_by_header: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for path in block_paths:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        header = data.get("header")
        paragraphs = data.get("english_text_raw", [])

        if not header or not isinstance(paragraphs, list):
            continue  # skip malformed blocks safely

        blocks_by_header[header].append({
            "filename": path.name,
            "paragraphs": paragraphs
        })

    # --------------------------------------------------
    # Flatten paragraphs per header
    # --------------------------------------------------
    aggregated: Dict[str, Dict[str, Any]] = {}

    for header, blocks in blocks_by_header.items():
        flattened: List[Dict[str, Any]] = []
        global_idx = 0

        for block in blocks:
            filename = block["filename"]
            for local_idx, text in enumerate(block["paragraphs"]):
                flattened.append({
                    "global_index": global_idx,
                    "text": text,
                    "source_block": filename,
                    "local_index": local_idx,
                })
                global_idx += 1

        aggregated[header] = {
            "header": header,
            "paragraphs": flattened
        }

    return aggregated
