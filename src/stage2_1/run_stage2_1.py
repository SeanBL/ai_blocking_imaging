from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .fidelity_audit import run_stage2_preservation_audit
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
        description="Stage 2.1 Preservation Audit — verifies Stage 2 did not drop Stage 1 content"
    )
    parser.add_argument(
        "stage1_json",
        nargs="?",
        type=str,
        help="Path to Stage 1 output JSON (optional if auto-discoverable)",
    )
    parser.add_argument(
        "stage2_json",
        nargs="?",
        type=str,
        help="Path to Stage 2 output JSON (optional if auto-discoverable)",
    )

    args = parser.parse_args()

    # ---------------------------------------------
    # Resolve inputs (explicit OR auto-discovered)
    # ---------------------------------------------
    if args.stage1_json and args.stage2_json:
        stage1_path = Path(args.stage1_json)
        stage2_path = Path(args.stage2_json)
    else:
        stage1_path, stage2_path = auto_discover_inputs()

    # ---------------------------------------------
    # Validate resolved paths
    # ---------------------------------------------
    if not stage1_path.exists():
        print(f"❌ Stage 1 JSON not found: {stage1_path}", file=sys.stderr)
        sys.exit(2)

    if not stage2_path.exists():
        print(f"❌ Stage 2 JSON not found: {stage2_path}", file=sys.stderr)
        sys.exit(2)

    stage1_module = load_json(stage1_path)
    stage2_module = load_json(stage2_path)

    # ---------------------------------------------
    # Run preservation audit
    # ---------------------------------------------
    try:
        run_stage2_preservation_audit(
            stage1_module=stage1_module,
            stage2_module=stage2_module,
        )
    except FidelityAuditError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print("✅ Stage 2.1 Preservation Audit PASSED — no content dropped.")
    sys.exit(0)


def auto_discover_inputs() -> tuple[Path, Path]:
    processed_dir = Path("data/processed")

    stage1_files = list(processed_dir.glob("module_v3.json"))
    if len(stage1_files) == 0:
        raise SystemExit("❌ No Stage 1 JSON (module_v3.json) found in data/processed")
    if len(stage1_files) > 1:
        raise SystemExit(f"❌ Multiple Stage 1 JSON files found: {[p.name for p in stage1_files]}")

    stage2_files = list(processed_dir.glob("module_stage2.json"))
    if len(stage2_files) == 0:
        raise SystemExit("❌ No Stage 2 JSON (module_stage2.json) found in data/processed")
    if len(stage2_files) > 1:
        raise SystemExit(f"❌ Multiple Stage 2 JSON files found: {[p.name for p in stage2_files]}")

    return stage1_files[0], stage2_files[0]


if __name__ == "__main__":
    main()
