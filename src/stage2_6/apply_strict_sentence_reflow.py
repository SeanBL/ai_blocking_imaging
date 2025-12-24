# src/stage2_6/apply_strict_sentence_reflow.py

from copy import deepcopy

def apply_strict_sentence_reflow(module: dict, suggestions: dict) -> dict:
    new_module = deepcopy(module)

    slide_map = {s["id"]: s for s in new_module.get("slides", [])}
    slide_suggestions = suggestions.get("slides", {})

    for slide_id, suggestion in slide_suggestions.items():
        if "sentence_reflow" not in suggestion:
            continue

        sr = suggestion["sentence_reflow"]
        if sr.get("rejected"):
            continue

        reflow = sr.get("sentence_reflow", {})
        if reflow.get("action") != "reflow":
            continue

        slide = slide_map.get(slide_id)
        if not slide:
            continue

        # STRICT: replace content with sentence array
        slide["content"] = reflow["sentences"]

    return new_module
