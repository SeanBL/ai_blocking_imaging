from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .fidelity_audit import run_fidelity_audit
from .errors import FidelityAuditError


# -------------------------------------------------
# IO helpers
# -------------------------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# -------------------------------------------------
# CLI
# -------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 2.1 Fidelity Audit — verifies no text was dropped between Word and Stage 2"
    )
    parser.add_argument(
        "docx",
        nargs="?",
        type=str,
        help="Path to original Word (.docx) file (optional if auto-discoverable)",
    )
    parser.add_argument(
        "stage2_json",
        nargs="?",
        type=str,
        help="Path to Stage 2 output JSON file (optional if auto-discoverable)",
    )

    args = parser.parse_args()

    # ---------------------------------------------
    # Resolve inputs (explicit OR auto-discovered)
    # ---------------------------------------------
    if args.docx and args.stage2_json:
        docx_path = Path(args.docx)
        stage2_path = Path(args.stage2_json)
    else:
        docx_path, stage2_path = auto_discover_inputs()

    # ---------------------------------------------
    # Validate resolved paths
    # ---------------------------------------------
    if not docx_path.exists():
        print(f"❌ Word file not found: {docx_path}", file=sys.stderr)
        sys.exit(2)

    if not stage2_path.exists():
        print(f"❌ Stage 2 JSON not found: {stage2_path}", file=sys.stderr)
        sys.exit(2)

    # ---------------------------------------------
    # Run audit
    # ---------------------------------------------
    stage2_module = load_json(stage2_path)

    try:
        run_fidelity_audit(
            docx_path=docx_path,
            stage2_module=stage2_module,
        )
    except FidelityAuditError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print("✅ Stage 2.1 Fidelity Audit PASSED — no text loss detected.")
    sys.exit(0)

def auto_discover_inputs() -> tuple[Path, Path]:
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    docx_files = list(raw_dir.glob("*.docx"))
    if len(docx_files) == 0:
        raise SystemExit("❌ No Word (.docx) files found in data/raw")
    if len(docx_files) > 1:
        raise SystemExit(f"❌ Multiple Word files found in data/raw: {[p.name for p in docx_files]}")

    stage2_files = list(processed_dir.glob("module_stage2_9.json"))
    if len(stage2_files) == 0:
        raise SystemExit("❌ No Stage 2 JSON files found in data/processed")
    if len(stage2_files) > 1:
        raise SystemExit(f"❌ Multiple Stage 2 JSON files found: {[p.name for p in stage2_files]}")

    return docx_files[0], stage2_files[0]


if __name__ == "__main__":
    main()
