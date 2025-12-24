import json
import sys
from pathlib import Path

from .apply_block_split import apply_block_split_executor
from .apply_semantic_index import apply_semantic_index_executor


def main(argv):
    if len(argv) != 4:
        print(
            "Usage:\n"
            "  python -m src.stage2_6.run_stage2_6 "
            "<module_stage2.json> <stage2_5_suggestions.json> <out_module.json>"
        )
        return 2

    module_path = Path(argv[1])
    suggestions_path = Path(argv[2])
    out_path = Path(argv[3])

    module = json.loads(module_path.read_text(encoding="utf-8"))
    suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))

    # -------------------------------------------------
    # STEP 1: SEMANTIC_SPLIT (HARD >70 WORD ENFORCEMENT)
    # -------------------------------------------------
    module_after_semantic, semantic_debug = apply_semantic_index_executor(
        module,
        suggestions,
    )

    # -------------------------------------------------
    # STEP 2: BLOCK_SPLIT (STRUCTURAL REPAIR)
    # -------------------------------------------------
    module_after_block, block_debug = apply_block_split_executor(
        module_after_semantic,
        suggestions,
    )

    final_module = module_after_block

    # -------------------------------------------------
    # DEBUG REPORT (WIRED)
    # -------------------------------------------------
    debug_report = {
        "stage": "2.6",
        "steps": [
            "semantic_split",
            "block_split",
        ],
        "semantic_split": semantic_debug,
        "block_split": block_debug,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(final_module, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    debug_path = out_path.with_suffix(".debug.json")
    debug_path.write_text(
        json.dumps(debug_report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"✅ Stage 2.6 module written to: {out_path}")
    print(f"🧪 Stage 2.6 debug written to:  {debug_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
