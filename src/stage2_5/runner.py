# src/stage2_5/runner.py

from typing import Dict, Any

from .validators import (
    engage_item_exceeds_soft_limit,
    button_label_invalid,
    word_count,
)
from .prompts import (
    engage1_item_review_prompt,
    button_label_prompt,
    panel_semantic_slides_prompt,
)
from .llm_client import LLMClient
from .validate_llm_output import (
    validate_engage1_item_review,
    validate_button_label_suggestions,
)

def _has_bullets(blocks: list[str]) -> bool:
    return any(
        line.strip().startswith(("•", "-", "*"))
        for block in blocks
        for line in block.splitlines()
    )

def run_stage2_5(module_stage2: Dict[str, Any], llm: LLMClient) -> Dict[str, Any]:
    suggestions = {
        "module_id": module_stage2.get("module_title"),
        "slides": {}
    }

    for slide in module_stage2.get("slides", []):
        slide_id = slide.get("id")
        slide_type = slide.get("type")

        slide_suggestions: Dict[str, Any] = {}

        # --------------------------------------
        # META (for humans + auditing)
        # --------------------------------------
        slide_suggestions["meta"] = {
            "id": slide_id,
            "header": slide.get("header"),
            "type": slide_type,
            "content_preview": slide.get("content", [])[:2],
        }

        # ======================================================
        # 🔹 PANEL HANDLING (LLM FINAL SPLIT — IMMUTABLE TEXT)
        # ======================================================
        if slide_type == "panel":

            panel_blocks = slide.get("content", [])
            panel_text = " ".join(panel_blocks)
            panel_wc = word_count(panel_text)

            # 🔒 HARD SKIP — bullet panels are NEVER split
            if _has_bullets(panel_blocks):
                slide_suggestions["panel_final"] = {
                    "action": "skip",
                    "reason": "bullet_panel",
                    "source_word_count": panel_wc,
                    "slides": [
                        {
                            "header": slide.get("header"),
                            "content": panel_text,
                            "word_count": panel_wc,
                        }
                    ],
                }

            # Within bounds → keep as-is
            elif panel_wc <= 70:
                slide_suggestions["panel_final"] = {
                    "action": "keep",
                    "source_word_count": panel_wc,
                    "slides": [
                        {
                            "header": slide.get("header"),
                            "content": panel_text,
                            "word_count": panel_wc,
                        }
                    ],
                }

            # Overlong → LLM split (immutable text)
            else:
                prompt = panel_semantic_slides_prompt(
                    header=slide.get("header", ""),
                    source_text=panel_text,
                )
                raw = llm.call(prompt)

                result = raw if isinstance(raw, dict) else {}
                slides = result.get("slides", [])

                if len(slides) < 2:
                    slide_suggestions["panel_final"] = {
                        "action": "keep",
                        "reason": "LLM did not produce a valid split",
                        "slides": [
                            {
                                "header": slide.get("header"),
                                "content": panel_text,
                            }
                        ],
                    }
                    continue

                invalid = False
                finalized = []

                for idx, s in enumerate(slides):
                    content = s.get("content", "")
                    wc = word_count(content)

                    if wc < 30 or wc > 70:
                        invalid = True
                        break

                    finalized.append({
                        "header": (
                            slide.get("header")
                            if idx == 0
                            else f"{slide.get('header')} (continued)"
                        ),
                        "content": content,
                        "word_count": wc,
                    })

                if invalid:
                    slide_suggestions["panel_final"] = {
                        "action": "keep",
                        "reason": "LLM produced invalid panel sizes",
                        "source_word_count": panel_wc,
                        "slides": [
                            {
                                "header": slide.get("header"),
                                "content": panel_text,
                                "word_count": panel_wc,
                            }
                        ],
                    }
                    continue


                slide_suggestions["panel_final"] = {
                    "action": "split",
                    "source_word_count": panel_wc,
                    "slides": finalized,
                }


        # ======================================================
        # 🔹 ENGAGE 1
        # ======================================================
        if slide_type == "engage":
            items = [
                " ".join(item.get("content", []))
                for item in slide.get("items", [])
            ]

            if any(engage_item_exceeds_soft_limit(t) for t in items):
                prompt = engage1_item_review_prompt(items)
                raw = llm.call(prompt)
                ok, validated_or_err = validate_engage1_item_review(raw)
                slide_suggestions["engage1_item_review"] = validated_or_err

        # ======================================================
        # 🔹 BUTTON LABELS
        # ======================================================
        if slide_type in ("engage", "engage2"):
            invalid = False
            context = ""

            if slide_type == "engage":
                for item in slide.get("items", []):
                    if button_label_invalid(item.get("button_label")):
                        invalid = True
                        context += " ".join(item.get("content", [])) + "\n"

            if slide_type == "engage2":
                if button_label_invalid(slide.get("button", {}).get("label")):
                    invalid = True
                    context = " ".join(slide.get("steps", []))

            if invalid:
                prompt = button_label_prompt(context)
                raw = llm.call(prompt)
                ok, validated_or_err = validate_button_label_suggestions(raw)
                slide_suggestions["button_label_suggestions"] = validated_or_err

        if slide_suggestions:
            suggestions["slides"][slide_id] = slide_suggestions

    return suggestions
