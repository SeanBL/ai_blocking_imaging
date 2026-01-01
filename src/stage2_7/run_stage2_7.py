from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

from .runner import run_stage2_7

# -------------------------------------------------
# Load environment variables (.env)
# -------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

client = OpenAI(api_key=OPENAI_API_KEY)


def main():
    import argparse

    p = argparse.ArgumentParser(description="Stage 2.7 — Engage synthesis")
    p.add_argument("--in-json", required=True, type=Path)
    p.add_argument("--out-json", required=True, type=Path)
    args = p.parse_args()

    run_stage2_7(
        in_path=args.in_json,
        out_path=args.out_json,
        client=client
    )


if __name__ == "__main__":
    main()


