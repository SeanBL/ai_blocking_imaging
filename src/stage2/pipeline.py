from __future__ import annotations
import argparse
import json
import pathlib
import logging

from tqdm import tqdm

from ..stage1.stage1_parse import ParsedBlock
from ..utils.config_loader import load_settings
from ..utils.llm_client_realtime import LLMClientRealtime
from ..utils import config_loader  # for root path if needed later

from .transform_block import transform_block     # Stage 2A
from .select_image import add_images_to_pages    # Stage 2B
from .quiz_generator import generate_quiz        # Stage 2C
from .merge_stage2 import merge_blocks           # Stage 2D


# ---------------- logging ----------------

def setup_logging():
    settings = load_settings()
    root = pathlib.Path(__file__).resolve().parents[1]
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


# ---------------- paths ----------------

def get_paths():
    root = pathlib.Path(__file__).resolve().parents[1]
    settings = load_settings()
    path_cfg = settings.get("paths", {})

    return {
        "stage1": root / path_cfg.get("stage1", "data/processed/stage1_blocks"),
        "stage2A": root / path_cfg.get("stage2A", "data/processed/stage2A_blocks"),
        "stage2B": root / path_cfg.get("stage2B", "data/processed/stage2B_blocks"),
        "stage2C": root / path_cfg.get("stage2C", "data/processed/stage2C_quiz"),
        "stage2D": root / path_cfg.get("stage2D", "data/processed/stage2_final"),
    }


# ---------------- core helpers ----------------

def run_single_block(filename: str, llm: LLMClientRealtime, paths: dict):
    name = pathlib.Path(filename).name
    block_path = paths["stage1"] / name

    if not block_path.exists():
        raise FileNotFoundError(f"Block not found: {block_path}")

    print(f"\n=== Stage 2 for block: {name} ===")
    logging.info(f"Processing block: {name}")

    with open(block_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    block = ParsedBlock(**raw)

    # 2A
    stage2A = transform_block(block, llm)
    paths["stage2A"].mkdir(parents=True, exist_ok=True)
    with open(paths["stage2A"] / name, "w", encoding="utf-8") as f:
        json.dump(stage2A, f, ensure_ascii=False, indent=2)
    logging.info(f"Stage 2A complete: {name}")

    # 2B
    stage2B = {
        "header": stage2A["header"],
        "pages": add_images_to_pages(stage2A["pages"]),
    }
    paths["stage2B"].mkdir(parents=True, exist_ok=True)
    with open(paths["stage2B"] / name, "w", encoding="utf-8") as f:
        json.dump(stage2B, f, ensure_ascii=False, indent=2)
    logging.info(f"Stage 2B complete: {name}")

    # 2C
    stage2C = generate_quiz(stage2A, llm)
    paths["stage2C"].mkdir(parents=True, exist_ok=True)
    with open(paths["stage2C"] / name, "w", encoding="utf-8") as f:
        json.dump(stage2C, f, ensure_ascii=False, indent=2)
    logging.info(f"Stage 2C complete: {name}")

    # 2D
    stage2D = merge_blocks(stage2A, stage2B, stage2C)
    paths["stage2D"].mkdir(parents=True, exist_ok=True)
    with open(paths["stage2D"] / name, "w", encoding="utf-8") as f:
        json.dump(stage2D, f, ensure_ascii=False, indent=2)
    logging.info(f"Stage 2D complete: {name}")

    print(f"🎉 Finished Stage 2 for block: {name}")


def run_all_blocks(llm: LLMClientRealtime, paths: dict):
    blocks = sorted(paths["stage1"].glob("*.json"))
    print(f"\n=== Stage 2 for ALL blocks ({len(blocks)}) ===")
    logging.info(f"Processing ALL blocks: {len(blocks)}")

    for path in tqdm(blocks, desc="Blocks", unit="block"):
        run_single_block(path.name, llm, paths)

    print("\n🎉 Stage 2 complete for ALL blocks")
    logging.info("\n--- Stage 2 ALL processing complete ---\n")


# ---------------- main ----------------

def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Run Stage 2 pipeline.")
    parser.add_argument("--all", action="store_true", help="Process all blocks")
    parser.add_argument("--block", type=str, help="Process a single block by filename")
    args = parser.parse_args()

    paths = get_paths()
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)

    llm = LLMClientRealtime()

    if args.all:
        run_all_blocks(llm, paths)
    elif args.block:
        run_single_block(args.block, llm, paths)
    else:
        print("❌ You must specify either --all or --block")
        print("Example:")
        print("   python -m src.stage2.pipeline --all")
        print("   python -m src.stage2.pipeline --block 03_Causes.json")


if __name__ == "__main__":
    main()
