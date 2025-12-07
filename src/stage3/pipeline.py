from __future__ import annotations
import pathlib
from .writer_docx import build_docx_from_stage2
from .writer_json import (
    build_full_module_json,
    save_full_module_json
)


def run_stage3(module_name: str = "module"):
    """
    Stage 3 pipeline:
    Creates:
      • Per-block JSON (already exists from Stage 2)
      • Consolidated module.json
      • DOCX preview of the module
    """
    root = pathlib.Path(__file__).resolve().parents[1]

    stage2_dir = root / "data" / "processed" / "stage2_blocks"

    # -------------- Build consolidated JSON --------------
    full_json = build_full_module_json(stage2_dir)
    final_json_path = root / "data" / "final" / f"{module_name}.json"
    save_full_module_json(full_json, final_json_path)

    # -------------- Build DOCX preview --------------
    final_docx_path = root / "data" / "final" / f"{module_name}.docx"
    build_docx_from_stage2(
        stage2_dir=stage2_dir,
        output_path=final_docx_path,
        module_title=full_json["module_title"]
    )

    print("\nStage 3 complete.")
    print(f"JSON: {final_json_path}")
    print(f"DOCX: {final_docx_path}")


if __name__ == "__main__":
    run_stage3("huntington_disease")