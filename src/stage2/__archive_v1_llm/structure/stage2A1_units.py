from __future__ import annotations
import json
import pathlib
from typing import Dict, Any, List
from ...utils.llm_client_realtime import LLMClientRealtime

def _load_prompt() -> str:
    root = pathlib.Path(__file__).resolve().parents[2]  # -> src/
    prompt_path = root / "config" / "prompt_stage2A1_units.txt"
    return prompt_path.read_text(encoding="utf-8")

PROMPT = _load_prompt()

def build_semantic_units(
    header: str,
    paragraphs: List[str],
    llm: LLMClientRealtime,
) -> Dict[str, Any]:
    """
    Stage 2A1: Given ALL paragraphs under one header (already aggregated),
    group paragraph indices into semantic units, without rewriting.

    Expected return:
    {
      "header": "...",
      "units": [
        {
          "unit_id": "u01",
          "paragraph_groups": [[0,1],[2]]   # groups of paragraph indices
        }
      ]
    }
    """
    prompt = (
        PROMPT
        .replace("<<<HEADER>>>", header)
        .replace("<<<PARAGRAPHS_JSON>>>", json.dumps(paragraphs, ensure_ascii=False, indent=2))
    )

    data = llm.call_json(prompt)

    print("🔍 Stage2A1 RAW LLM OUTPUT:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("header","").strip() != header.strip():
        raise ValueError("Stage2A1 returned mismatched header")

    units = data.get("units")

    # -------------------------------------------
    # Fallback: single unit containing all paragraphs
    # -------------------------------------------
    if not isinstance(units, list) or not units:
        units = [{
            "unit_id": "u01",
            "paragraph_groups": [[i for i in range(len(paragraphs))]]
        }]

    # -------------------------------------------
    # Normalize LLM output (robust to schema drift)
    # -------------------------------------------

    normalized_units: List[Dict[str, Any]] = []
    n = len(paragraphs)

    for idx, u in enumerate(units):
        # Case 1: correct schema already
        if "paragraph_groups" in u:
            groups = u["paragraph_groups"]

        # Case 2: LLM returned flat paragraph list
        elif "paragraphs" in u:
            groups = [[i] for i in u["paragraphs"]]

        else:
            raise ValueError(f"Stage2A1 unit missing paragraph info: {u}")

        # Validate indices
        for g in groups:
            for i in g:
                if not isinstance(i, int) or not (0 <= i < n):
                    raise ValueError(f"Stage2A1 invalid paragraph index: {i}")

        normalized_units.append({
            "unit_id": u.get("unit_id", f"u{idx+1:02d}"),
            "paragraph_groups": groups,
        })

    data["units"] = normalized_units

    return data
