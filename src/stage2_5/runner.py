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
from .routing import classify_panel, PanelRouting
from .block_split import split_panel_blocks


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
        content = slide.get("content", {})
        blocks = content.get("blocks", [])

        slide_suggestions["meta"] = {
            "id": slide_id,
            "header": slide.get("header"),
            "type": slide_type,
            "content_preview": [
                block.get("text") if block.get("type") == "paragraph"
                else f"[bullets: {len(block.get('items', []))}]"
                for block in blocks[:2]
            ],
        }


        # ======================================================
        # 🔹 PANEL HANDLING (LLM FINAL SPLIT — IMMUTABLE TEXT)
        # ======================================================
        

        if slide_type == "panel":

            content = slide.get("content", {})
            blocks = content.get("blocks", [])

            paragraph_blocks = [b for b in blocks if b.get("type") == "paragraph"]
            bullet_blocks = [b for b in blocks if b.get("type") == "bullets"]

            panel_text = " ".join(b["text"] for b in paragraph_blocks)
            panel_wc = word_count(panel_text)

            routing = classify_panel(slide)

            # -------------------------------
            # NO ACTION → keep panel as-is
            # -------------------------------
            if routing == PanelRouting.NO_ACTION:
                slide_suggestions["panel_final"] = {
                    "action": "keep",
                    "source_word_count": panel_wc,
                    "slides": [
                        {
                            "header": slide.get("header"),
                            "content": blocks,
                        }
                    ],
                }

            # -------------------------------
            # STRUCTURAL SPLIT (Stage 2.5)
            # -------------------------------
            elif routing == PanelRouting.BLOCK_SPLIT:
                split_blocks = split_panel_blocks(blocks)

                slide_suggestions["panel_final"] = {
                    "action": "split",
                    "source_word_count": panel_wc,
                    "slides": [
                        {
                            "header": slide.get("header") if i == 0 else f"{slide.get('header')} (continued)",
                            "content": group,
                        }
                        for i, group in enumerate(split_blocks)
                    ],
                }

            # -------------------------------
            # SEMANTIC SPLIT (LLM)
            # -------------------------------
            elif routing == PanelRouting.SEMANTIC_SPLIT:
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
                else:
                    finalized = []
                    for idx, s in enumerate(slides):
                        content_text = s.get("content", "")
                        wc = word_count(content_text)
                        finalized.append({
                            "header": slide.get("header") if idx == 0 else f"{slide.get('header')} (continued)",
                            "content": content_text,
                            "word_count": wc,
                        })

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
