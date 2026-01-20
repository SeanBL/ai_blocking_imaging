from __future__ import annotations

import sys
import json
from pathlib import Path

# -----------------------------
# Stage imports (existing code)
# -----------------------------

# Stage 1
from ..stage1.stage1_extract_v3 import extract_tables_v3

# Stage 1.1 (Word → Stage 1 fidelity)
from ..stage1_1.fidelity_audit import run_stage1_fidelity_audit

# Stage 2
from ..stage2.stage2_transform import transform_module_v3_to_stage2

# Stage 2.1 (Stage 1 → Stage 2 preservation)
from ..stage2_1.fidelity_audit import run_stage2_preservation_audit



# -----------------------------
# Paths
# -----------------------------

DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")


# -----------------------------
# Helpers
# -----------------------------

def resolve_single_docx() -> Path:
    docs = list(DATA_RAW.glob("*.docx"))
    if not docs:
        raise SystemExit("❌ No .docx files found in data/raw")
    if len(docs) > 1:
        raise SystemExit(
            "❌ Multiple .docx files found in data/raw:\n"
            + "\n".join(f"  - {d.name}" for d in docs)
        )
    return docs[0]


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# -----------------------------
# Pipeline
# -----------------------------

def main() -> None:
    print("▶ Pre-LLM structural pipeline starting")

    # -------------------------
    # Resolve input
    # -------------------------
    docx_path = resolve_single_docx()
    print(f"📄 Input Word document: {docx_path.name}")

    # -------------------------
    # Stage 1
    # -------------------------
    print("▶ Stage 1: Word → Stage 1 JSON")
    stage1_module = extract_tables_v3(docx_path)

    stage1_out = DATA_PROCESSED / "module_v3.json"
    save_json(stage1_out, stage1_module)
    print(f"✅ Stage 1 output written: {stage1_out}")

    # -------------------------
    # Stage 1.1 — HARD GATE
    # -------------------------
    print("▶ Stage 1.1: Fidelity audit (Word → Stage 1)")
    run_stage1_fidelity_audit(
        docx_path=docx_path,
        stage1_module=stage1_module,
    )
    print("✅ Stage 1.1 passed (no text loss)")

    # -------------------------
    # Stage 2
    # -------------------------
    print("▶ Stage 2: Stage 1 → Stage 2 JSON")
    stage2_module = transform_module_v3_to_stage2(stage1_module)

    stage2_out = DATA_PROCESSED / "module_stage2.json"
    save_json(stage2_out, stage2_module)
    print(f"✅ Stage 2 output written: {stage2_out}")

    # -------------------------
    # Stage 2.1 — HARD GATE
    # -------------------------
    print("▶ Stage 2.1: Preservation audit (Stage 1 → Stage 2)")
    run_stage2_preservation_audit(
        stage1_module=stage1_module,
        stage2_module=stage2_module,
    )
    print("✅ Stage 2.1 passed (no text loss)")

    print("🎉 Pre-LLM structural pipeline completed successfully")
    print("➡ Safe to proceed to Stage 2.7+ (LLM inference)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\n❌ PIPELINE FAILED")
        print(str(exc), file=sys.stderr)
        sys.exit(1)
