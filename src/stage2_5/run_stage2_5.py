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
from .apply_splits import apply_stage2_5_splits


# -------------------------------------------------
# Load .env so OPENAI_API_KEY is available
# -------------------------------------------------
load_dotenv()

client = OpenAI()


def llm_dispatch(prompt: str) -> Any:
    if (
        "sentence_reflow" in prompt
        or "THIS TASK IS PANEL SPLITTING ONLY" in prompt
        or "THIS TASK IS SENTENCE SHAPING ONLY" in prompt
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
        return json.loads(resp.choices[0].message.content)

    return {"rejected": True, "reason": "LLM disabled for this task"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage:\n"
            "  python -m src.stage2_5.run_stage2_5 "
            "<in_module_stage2.json> "
            "<out_stage2_5_suggestions.json> "
            "<out_module_stage2_after_2_5.json>\n"
        )
        return 2

    in_path = Path(argv[1])
    suggestions_path = Path(argv[2])
    applied_path = Path(argv[3])

    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}")
        return 2

    # ----------------------------------
    # Load Stage 2 input
    # ----------------------------------
    module_stage2 = load_json(in_path)

    # ----------------------------------
    # Run Stage 2.5 (decision + execution)
    # ----------------------------------
    llm = LLMClient(llm_dispatch)
    suggestions = run_stage2_5(module_stage2, llm)

    write_json(suggestions_path, suggestions)
    print(f"✅ Stage 2.5 suggestions written to: {suggestions_path}")

    # ----------------------------------
    # APPLY SPLITS (THIS IS CRITICAL)
    # ----------------------------------
    applied_module = apply_stage2_5_splits(
        module_stage2=module_stage2,
        stage2_5=suggestions,
    )

    write_json(applied_path, applied_module)
    print(f"✅ Stage 2.5 applied module written to: {applied_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
