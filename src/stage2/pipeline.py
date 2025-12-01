import json
import pathlib
from ..stage1_parse import ParsedBlock
from .llm_client import LLMClient
from .transform_block import transform_block

def run_stage2():
    root = pathlib.Path(__file__).resolve().parents[1]
    parsed_dir = root / "data" / "processed" / "stage1_blocks"
    out_dir = root / "data" / "processed" / "stage2_blocks"
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = LLMClient(provider="openai", model="gpt-4o-mini")

    for path in sorted(parsed_dir.glob("*.json")):
        block_data = json.load(open(path, "r", encoding="utf-8"))
        block = ParsedBlock(**block_data)

        result = transform_block(block, llm)

        out_path = out_dir / path.name
        json.dump(result, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

        print(f"Stage 2 completed for: {path.name}")
