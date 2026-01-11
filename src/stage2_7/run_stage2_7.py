from pathlib import Path
import os
from dotenv import load_dotenv

from openai import OpenAI

from .runner import run_stage2_7


def main():
    import argparse

    p = argparse.ArgumentParser(description="Stage 2.7 — Engage synthesis")
    p.add_argument("--in-json", required=True, type=Path)
    p.add_argument("--out-json", required=True, type=Path)

    # NEW: LLM is optional
    p.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable OpenAI-based engage synthesis (requires OPENAI_API_KEY).",
    )

    args = p.parse_args()

    client = None

    if args.use_llm:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in .env (required when --use-llm is set)")
        client = OpenAI(api_key=api_key)

    run_stage2_7(
        in_path=args.in_json,
        out_path=args.out_json,
        client=client,  # may be None
    )


if __name__ == "__main__":
    main()



