from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from .prompts_for_2_6 import sentence_shaping_prompt
from .validate_sentence_shaping import validate_sentence_shaping
from src.stage2_5.llm_client import LLMClient


# ---------------------------------------------------------
# IO helpers
# ---------------------------------------------------------
def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------
# Stage 2.6 — Sentence Structuring (MODULE MUTATION)
# ---------------------------------------------------------
def run_stage2_6(
    module: Dict[str, Any],
    llm: LLMClient,
) -> Dict[str, Any]:
    """
    Stage 2.6 MUTATES the module in-place.

    - Converts paragraph blocks into sentence_blocks
    - Preserves slide order, IDs, notes, quiz markers
    - NEVER changes engage slides
    - NEVER drops bullets
    """

    slides = module.get("slides", [])
    if not isinstance(slides, list):
        raise ValueError("Stage 2.6 invariant failed: slides must be a list")

    for slide in slides:
        slide_id = slide.get("id") or slide.get("uuid")
        if not slide_id:
            raise ValueError("Stage 2.6 invariant failed: slide missing id")

        slide_type = slide.get("slide_type") or slide.get("type")

        notes_lower = (slide.get("notes") or "").lower()
        if "[[locked]]" in notes_lower:
            continue

        # Only mutate panels
        if slide_type != "panel":
            continue

        content = slide.get("content", {})
        blocks = content.get("blocks", [])

        if not isinstance(blocks, list):
            continue

        new_blocks: List[Dict[str, Any]] = []
        sb_index = 0

        for block in blocks:
            if block.get("type") != "paragraph":
                # Preserve bullets / other blocks verbatim
                new_blocks.append(block)
                continue

            source_text = (block.get("text") or "").strip()
            if not source_text:
                continue

            prompt = sentence_shaping_prompt(source_text)
            raw = llm.call(prompt)
            validated = validate_sentence_shaping(raw, source_text)

            for sb in validated.get("sentence_blocks", []):
                sb_index += 1
                new_blocks.append({
                    "type": "sentence_block",
                    "block_id": f"{slide_id}__sb{sb_index:02d}",
                    "sentences": sb["sentences"],
                    "word_count": sb["word_count"],
                    "source_text": source_text,
                })

        slide["content"]["blocks"] = new_blocks

    return module


# ---------------------------------------------------------
# CLI entry
# ---------------------------------------------------------
def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage:\n"
            "  python -m src.stage2_6.runner "
            "<module_stage2_after_2_5.json> "
            "<out_module_stage2_after_2_6.json>"
        )
        return 2

    in_path = Path(argv[1])
    out_path = Path(argv[2])

    module = load_json(in_path)

    from src.stage2_5.run_stage2_5 import llm_dispatch
    llm = LLMClient(llm_dispatch)

    result = run_stage2_6(module, llm)
    write_json(out_path, result)

    print(f"✅ Stage 2.6 complete → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

