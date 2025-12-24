from __future__ import annotations
import argparse
import json
import logging
import pathlib
from typing import Dict, Any, List

from tqdm import tqdm

from ...stage1.stage1_parse import ParsedBlock
from ...utils.config_loader import load_settings
from ...utils.llm_client_realtime import LLMClientRealtime

from .transform_block import transform_block
from .final_exam.collect_final_exam import collect_final_exam


# ------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------

def setup_logging() -> None:
    settings = load_settings()
    # PROJECT ROOT: go up two levels from src/stage2/pipeline.py
    root = pathlib.Path(__file__).resolve().parents[2]

    logs_rel = settings.get("paths", {}).get("logs", "logs")
    logs_dir = root / logs_rel
    logs_dir.mkdir(parents=True, exist_ok=True)

    logfile = logs_dir / "stage2.log"

    logging.basicConfig(
        filename=str(logfile),
        filemode="a",
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )

    logging.info("\n--- Stage 2 Pipeline Started ---\n")


# ------------------------------------------------------------
# Paths + Image Catalog
# ------------------------------------------------------------

def get_paths() -> Dict[str, pathlib.Path]:
    """
    Returns all Stage 2 save directories according to settings.yaml.

    IMPORTANT:
      - Root is the PROJECT ROOT (…/AI_BLOCKING_IMAGING)
      - All paths in settings.yaml are relative to that root.
    """
    # PROJECT ROOT
    root = pathlib.Path(__file__).resolve().parents[2]
    settings = load_settings()
    path_cfg = settings.get("paths", {})

    return {
        "stage1": root / path_cfg.get("stage1", "data/processed/stage1_blocks"),

        # Stage 2A: classification only (rewrite removed)
        "stage2A_classify": root / path_cfg.get(
            "stage2A_classify", "data/processed/stage2A_classify"
        ),

        # Stage 2B / 2C / Bullets / Labels / Images / Quiz
        "stage2B_engage": root / path_cfg.get(
            "stage2B_engage", "data/processed/stage2B_engage"
        ),
        "stage2C_engage2": root / path_cfg.get(
            "stage2C_engage2", "data/processed/stage2C_engage2"
        ),
        "stage2B_bullets": root / path_cfg.get(
            "stage2B_bullets", "data/processed/stage2B_bullets"
        ),
        "stage2D_labels": root / path_cfg.get(
            "stage2D_labels", "data/processed/stage2D_labels"
        ),
        "stage2E_images": root / path_cfg.get(
            "stage2E_images", "data/processed/stage2E_images"
        ),
        "stage2F_quiz": root / path_cfg.get(
            "stage2F_quiz", "data/processed/stage2F_quiz"
        ),

        # Final merged output
        "stage2G_final": root / path_cfg.get(
            "stage2G_final", "data/processed/stage2G_final"
        ),

        # Aggregated final exam questions
        "stage2H_final_exam": root / path_cfg.get(
            "stage2H_final_exam", "data/processed/stage2H_final_exam"
        ),
    }


def load_image_catalog() -> List[Dict[str, Any]]:
    """
    Loads image catalog JSON if present. Returns [] if missing or invalid.

    Expected settings.yaml:

      paths:
        image_catalog: data/config/image_catalog.json
    """
    settings = load_settings()
    # PROJECT ROOT
    root = pathlib.Path(__file__).resolve().parents[2]
    path_cfg = settings.get("paths", {})

    catalog_rel = path_cfg.get("image_catalog", "data/config/image_catalog.json")
    catalog_path = root / catalog_rel

    if not catalog_path.exists():
        logging.warning(f"No image catalog found at: {catalog_path}")
        return []

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logging.warning(f"Image catalog at {catalog_path} is not a list; ignoring.")
        return []
    except Exception as e:
        logging.error(f"Error loading image catalog {catalog_path}: {e}")
        return []


# ------------------------------------------------------------
# Helper: Save JSON
# ------------------------------------------------------------

def save_json(path: pathlib.Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------
# Run Stage 2 on Single Block
# ------------------------------------------------------------

def run_single_block(
    filename: str,
    llm: LLMClientRealtime,
    paths: Dict[str, pathlib.Path],
    image_catalog: List[Dict[str, Any]],
) -> None:
    """
    Run all Stage 2 sub-stages for a SINGLE block,
    saving every sub-stage to its own directory + the final merged JSON.
    """
    name = pathlib.Path(filename).name
    block_path = paths["stage1"] / name

    if not block_path.exists():
        raise FileNotFoundError(f"Block not found: {block_path}")

    print(f"\n=== Stage 2 for block: {name} ===")
    logging.info(f"Processing block: {name}")

    # Load Stage 1 block
    with open(block_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    parsed_block = ParsedBlock(**raw)

    # Central orchestrator – returns all sub-stage outputs + merged
    all_outputs = transform_block(
        parsed_block=parsed_block,
        llm=llm,
        image_catalog=image_catalog,
        return_all=True,
    )

    # --------------------------------------------------
    # 🚨 Skip non-instructional blocks cleanly
    # --------------------------------------------------
    if all_outputs.get("skipped"):
        logging.info(
            f"Skipping block {name}: {all_outputs.get('reason')}"
        )
        print(f"⏭️  Skipped block: {name}")
        return

    # Unpack
    semantic_units = all_outputs["semantic_units"]
    unit_plan      = all_outputs["unit_plan"]
    engage_data = all_outputs["engage"]
    engage2_data = all_outputs["engage2"]
    bullet_data = all_outputs["bullets"]
    labels_data = all_outputs["labels"]
    images_data = all_outputs["images"]
    quiz_data = all_outputs["quiz"]
    merged_block = all_outputs["merged"]

    # Save each sub-stage
    save_json(paths["stage2A_classify"] / name, {
        "semantic_units": all_outputs["semantic_units"],
        "unit_plan": all_outputs["unit_plan"],
    })

    save_json(paths["stage2B_engage"] / name, engage_data)
    logging.info(f"Stage 2B (engage extraction) complete: {name}")

    save_json(paths["stage2C_engage2"] / name, engage2_data)
    logging.info(f"Stage 2C (engage2 extraction) complete: {name}")

    save_json(paths["stage2B_bullets"] / name, bullet_data)
    logging.info(f"Stage 2B-bullets (page bullet extraction) complete: {name}")

    save_json(paths["stage2D_labels"] / name, labels_data)
    logging.info(f"Stage 2D (button labels) complete: {name}")

    save_json(paths["stage2E_images"] / name, images_data)
    logging.info(f"Stage 2E (image selection) complete: {name}")

    save_json(paths["stage2F_quiz"] / name, quiz_data)
    logging.info(f"Stage 2F (quiz generation) complete: {name}")

    # Save final merged block
    save_json(paths["stage2G_final"] / name, merged_block)
    logging.info(f"Stage 2G (final merge) complete: {name}")

    print(f"🎉 Finished Stage 2 for block: {name}")


# ------------------------------------------------------------
# Run Stage 2 on ALL Blocks
# ------------------------------------------------------------

def run_all_blocks(
    llm: LLMClientRealtime,
    paths: Dict[str, pathlib.Path],
    image_catalog: List[Dict[str, Any]],
) -> None:
    """
    Run Stage 2 for ALL blocks found in the stage1 directory.
    """
    blocks = sorted(paths["stage1"].glob("*.json"))
    print(f"\n=== Stage 2 for ALL blocks ({len(blocks)}) ===")
    logging.info(f"Processing ALL blocks: {len(blocks)}")
    logging.info(f"Stage1 directory resolved to: {paths['stage1']}")

    for path in tqdm(blocks, desc="Blocks", unit="block"):
        run_single_block(path.name, llm, paths, image_catalog)

    print("\n🎉 Stage 2 complete for ALL blocks")
    logging.info("\n--- Stage 2 ALL processing complete ---\n")

    # --------------------------------------------------------
    # Collect final exam questions into one file
    # --------------------------------------------------------
    final_exam_path = paths["stage2H_final_exam"] / "final_exam.json"
    collect_final_exam(
        stage2D_dir=paths["stage2F_quiz"],   # quizzes live here
        output_path=final_exam_path,
    )

    print(f"📘 Final exam collected → {final_exam_path}")
    logging.info(f"Final exam collected at {final_exam_path}")


# ------------------------------------------------------------
# Main CLI
# ------------------------------------------------------------

def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Run Stage 2 pipeline.")
    parser.add_argument("--all", action="store_true", help="Process all blocks")
    parser.add_argument("--block", type=str, help="Process a single block by filename")
    args = parser.parse_args()

    paths = get_paths()

    # Ensure directories exist
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)

    llm = LLMClientRealtime()
    image_catalog = load_image_catalog()

    if args.all:
        run_all_blocks(llm, paths, image_catalog)
    elif args.block:
        run_single_block(args.block, llm, paths, image_catalog)
    else:
        print("❌ You must specify either --all or --block")
        print("Examples:")
        print("   python -m src.stage2.pipeline --all")
        print("   python -m src.stage2.pipeline --block 003_Causes.json")


if __name__ == "__main__":
    main()

