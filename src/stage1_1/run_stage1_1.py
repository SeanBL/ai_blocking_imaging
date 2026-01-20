from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .fidelity_audit import run_stage1_fidelity_audit


# -------------------------------------------------
# IO helpers
# -------------------------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def auto_discover_inputs() -> tuple[Path, Path]:
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    docx_files = list(raw_dir.glob("*.docx"))
    if len(docx_files) == 0:
        raise SystemExit("❌ No Word (.docx) files found in data/raw")
    if len(docx_files) > 1:
        raise SystemExit(
            f"❌ Multiple Word files found in data/raw:\n"
            + "\n".join(f"  - {p.name}" for p in docx_files)
        )

    stage1_files = list(processed_dir.glob("module_v3.json"))
    if len(stage1_files) == 0:
        raise SystemExit("❌ Stage 1 output (module_v3.json) not found in data/processed")
    if len(stage1_files) > 1:
        raise SystemExit("❌ Multiple module_v3.json files found (unexpected)")

    return docx_files[0], stage1_files[0]


# -------------------------------------------------
# CLI
# -------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1.1 Fidelity Audit — verifies Stage 1 preserved all Word slide text"
    )
    parser.add_argument(
        "docx",
        nargs="?",
        type=str,
        help="Path to Word (.docx) file (optional if auto-discoverable)",
    )
    parser.add_argument(
        "stage1_json",
        nargs="?",
        type=str,
        help="Path to Stage 1 output JSON (optional if auto-discoverable)",
    )

    args = parser.parse_args()

    # Resolve inputs
    if args.docx and args.stage1_json:
        docx_path = Path(args.docx)
        stage1_path = Path(args.stage1_json)
    else:
        docx_path, stage1_path = auto_discover_inputs()

    # Validate paths
    if not docx_path.exists():
        print(f"❌ Word file not found: {docx_path}", file=sys.stderr)
        sys.exit(2)

    if not stage1_path.exists():
        print(f"❌ Stage 1 JSON not found: {stage1_path}", file=sys.stderr)
        sys.exit(2)

    stage1_module = load_json(stage1_path)

    # Run audit
    try:
        run_stage1_fidelity_audit(
            docx_path=docx_path,
            stage1_module=stage1_module,
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print("✅ Stage 1 Fidelity Audit PASSED — no text loss detected.")
    sys.exit(0)


if __name__ == "__main__":
    main()
