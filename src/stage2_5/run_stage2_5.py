# src/stage2_5/run_stage2_5.py

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

from .runner import run_stage2_5
from .llm_client import LLMClient

# Load .env so OPENAI_API_KEY is available
load_dotenv()

client = OpenAI()


def llm_dispatch(prompt: str) -> Any:
    if (
        "sentence_reflow" in prompt
        or "THIS TASK IS PANEL SPLITTING ONLY" in prompt
    ):
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_completion_tokens=900,
        )
        return resp.choices[0].message.content

    return {"rejected": True, "reason": "LLM disabled for this task"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage:\n"
            "  python -m src.stage2_5.run_stage2_5 <in_module_stage2.json> <out_suggestions.json>\n"
        )
        return 2

    in_path = Path(argv[1])
    out_path = Path(argv[2])

    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}")
        return 2

    module_stage2 = load_json(in_path)

    llm = LLMClient(llm_dispatch)
    suggestions = run_stage2_5(module_stage2, llm)

    write_json(out_path, suggestions)
    print(f"✅ Stage 2.5 suggestions written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
