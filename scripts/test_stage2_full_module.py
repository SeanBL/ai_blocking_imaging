from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

from src.utils.llm_client_realtime import LLMClientRealtime

from src.stage2.aggregate.aggregate_by_header import aggregate_blocks_by_header
from src.stage2.structure.stage2A1_units import build_semantic_units
from src.stage2.structure.stage2A2_units import assign_final_units
from src.stage2.structure.stage2B_pack import stage2B_pack_units

from src.stage2.engage.extract_engage import extract_engage_data
from src.stage2.engage2.extract_engage2 import extract_engage2
from src.stage2.bullets.extract_bullets import extract_bullets
from src.stage2.images.select_images import select_images
from src.stage2.labels.generate_labels import generate_labels
from src.stage2.quiz.generate_quiz import generate_quiz
from src.stage2.merge.merge_stage2 import merge_stage2

def safe_filename(name: str) -> str:
    """
    Make a string safe for use as a filename on all platforms.
    """
    return (
        name.replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("?", "")
            .replace("*", "")
            .replace("\"", "")
            .replace("<", "")
            .replace(">", "")
            .replace("|", "")
            .strip()
    )


def main():
    root = Path(__file__).resolve().parents[1]
    stage1_dir = root / "data" / "processed" / "stage1_blocks"
    out_dir = root / "data" / "processed" / "stage2_full"
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = LLMClientRealtime()

    print("🔹 Aggregating Stage 1 blocks...")
    all_headers = aggregate_blocks_by_header(stage1_dir=stage1_dir)

    print(f"🔹 Found {len(all_headers)} headers")

    for header, header_doc in all_headers.items():
        print(f"\n▶ Processing header: {header}")

        paragraphs = [p["text"] for p in header_doc["paragraphs"]]

        # --- Stage 2A1
        units_A1 = build_semantic_units(header, paragraphs, llm)

        # --- Stage 2A2
        units_A2 = assign_final_units(header, paragraphs, llm)

        # --- Stage 2B
        packed = stage2B_pack_units(units_A2, paragraphs)

        # --- Extractors
        engage_data = extract_engage_data(header, paragraphs, packed["units"])
        engage2_data = extract_engage2(header, paragraphs, packed["units"], llm)
        bullet_data = extract_bullets(header, paragraphs, packed["units"], llm)

        images_data = select_images(
            header=header,
            paragraphs=paragraphs,
            units=packed["units"],
            image_catalog=[],   # keep empty for now
            llm=llm,
        )

        labels_data = generate_labels(header, paragraphs, packed["units"], llm)
        quiz_data = generate_quiz(header, paragraphs, packed["units"], llm)

        final_output = merge_stage2(
            header=header,
            paragraphs=paragraphs,
            units=packed["units"],
            engage_data=engage_data,
            engage2_data=engage2_data,
            labels_data=labels_data,
            images_data=images_data,
            bullet_data=bullet_data,
            quiz_data=quiz_data,
            notes=None,
        )

        filename = safe_filename(header).replace(" ", "_") + ".json"
        out_path = out_dir / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)

        out_path.write_text(
            json.dumps(final_output, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"✅ Finished: {out_path.name}")

    print("\n🎉 Stage 2 FULL MODULE COMPLETE")


if __name__ == "__main__":
    main()
