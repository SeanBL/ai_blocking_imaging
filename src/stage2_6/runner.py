from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from .prompts_for_2_6 import sentence_shaping_prompt
from .validate_sentence_shaping import validate_sentence_shaping
from src.stage2_5.llm_client import LLMClient


# ---------------------------------------------------------
# IO helpers
# ---------------------------------------------------------
def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ---------------------------------------------------------
# Stage 2.6 — Sentence Boundary Annotation ONLY
# ---------------------------------------------------------
def run_stage2_6(
    module_stage2: Dict[str, Any],
    stage2_5: Dict[str, Any],
    llm: LLMClient,
) -> Dict[str, Any]:

    out: Dict[str, Any] = {
        "module_id": module_stage2.get("module_title"),
        "slides": {},
    }

    for slide in module_stage2.get("slides", []):
        slide_id = slide.get("id")

        # 🔒 Stage 2.6 applies ONLY to panel slides
        if slide.get("type") != "panel":
            continue

        s25 = stage2_5.get("slides", {}).get(slide_id)
        if not s25:
            continue

        panel_final = s25.get("panel_final")
        if not panel_final:
            continue

        # 🔒 HARD SKIP: bullet panels are never sentence-shaped
        if panel_final.get("reason") == "bullet_panel":
            continue

        sentence_blocks = []
        sb_index = 0

        for block in panel_final.get("slides", []):
            source_text = block.get("content")

            # Only plain paragraph text is valid here
            if not isinstance(source_text, str):
                continue

            source_text = source_text.strip()
            if not source_text:
                continue

            prompt = sentence_shaping_prompt(source_text)
            raw = llm.call(prompt)

            validated = validate_sentence_shaping(raw, source_text)

            for sb in validated.get("sentence_blocks", []):
                sb_index += 1

                sentence_blocks.append({
                    "block_id": f"{slide_id}__sb{sb_index:02d}",
                    "sentences": sb["sentences"],
                    "word_count": sb["word_count"],
                    "source_text": source_text,
                })

        if sentence_blocks:
            out["slides"][slide_id] = {
                "sentence_blocks": sentence_blocks
            }

    return out


# ---------------------------------------------------------
# CLI entry
# ---------------------------------------------------------
def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage:\n"
            "  python -m src.stage2_6.runner "
            "<module_stage2.json> "
            "<stage2_5_suggestions.json> "
            "<out_stage2_6_suggestions.json>"
        )
        return 2

    in_stage2 = Path(argv[1])
    in_stage25 = Path(argv[2])
    out_path = Path(argv[3])

    module_stage2 = load_json(in_stage2)
    stage2_5 = load_json(in_stage25)

    from src.stage2_5.run_stage2_5 import llm_dispatch
    llm = LLMClient(llm_dispatch)

    result = run_stage2_6(module_stage2, stage2_5, llm)
    write_json(out_path, result)

    print(f"✅ Stage 2.6 written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


