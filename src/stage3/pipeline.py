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
      • Consolidated module.json (built from Stage 2 merged blocks)
      • DOCX preview of the module (with inline quizzes + final exam)
    """
    root = pathlib.Path(__file__).resolve().parents[2]  # project root
    stage2_dir = root / "data" / "processed" / "stage2G_final"

    # Ensure directory exists
    if not stage2_dir.exists():
        raise RuntimeError(f"Stage 2 output directory not found: {stage2_dir}")

    # ------------------------------------
    # Build consolidated module.json
    # ------------------------------------
    full_json = build_full_module_json(stage2_dir)
    final_json_path = root / "data" / "final" / f"{module_name}.json"
    save_full_module_json(full_json, final_json_path)

    # ------------------------------------
    # Build DOCX preview
    # ------------------------------------
    final_docx_path = root / "data" / "final" / f"{module_name}.docx"
    build_docx_from_stage2(
        stage2_dir=stage2_dir,
        output_path=final_docx_path,
        module_title=full_json.get("module_title", "Untitled Module"),
        final_exam=full_json.get("final_exam", [])
    )

    print("\nStage 3 complete.")
    print(f"JSON: {final_json_path}")
    print(f"DOCX: {final_docx_path}")


if __name__ == "__main__":
    run_stage3("huntington_disease")

