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
    strict_sentence_reflow_prompt,
)
from .llm_client import LLMClient
from .validate_llm_output import (
    validate_engage1_item_review,
    validate_button_label_suggestions,
)
from .routing import classify_panel, PanelRouting
from .block_split import split_panel_blocks

def _sentences_from_reflow(text: str, indexes: list[int]) -> list[str]:
    # indexes are sentence start positions; last sentence ends at len(text)
    cuts = sorted(set(i for i in indexes if isinstance(i, int)))
    if not cuts or cuts[0] != 0:
        cuts = [0] + cuts
    cuts = [i for i in cuts if 0 <= i <= len(text)]
    cuts = sorted(set(cuts))
    cuts.append(len(text))

    sentences = []
    for i in range(len(cuts) - 1):
        s = text[cuts[i]:cuts[i + 1]].strip()
        if s:
            sentences.append(s)
    return sentences


def _chunk_sentences_30_70(sentences: list[str]) -> list[str]:
    # Greedy pack sentences into chunks 30–70 words
    chunks: list[str] = []
    current: list[str] = []

    def wc(s: str) -> int:
        return word_count(s)

    for sent in sentences:
        candidate = (" ".join(current + [sent])).strip()
        if not current:
            current = [sent]
            continue

        # If adding stays <= 70, keep packing
        if wc(candidate) <= 70:
            current.append(sent)
            continue

        # Otherwise, close current chunk
        chunk_text = " ".join(current).strip()
        if chunk_text:
            chunks.append(chunk_text)
        current = [sent]

    # flush
    if current:
        chunks.append(" ".join(current).strip())

    # Enforce minimum 30 by merging small chunks with neighbor
    merged: list[str] = []
    for ch in chunks:
        if not merged:
            merged.append(ch)
            continue
        if word_count(ch) < 30:
            merged[-1] = (merged[-1] + " " + ch).strip()
        else:
            merged.append(ch)

    # If last chunk is still <30 and we have >1 chunk, merge backward
    if len(merged) > 1 and word_count(merged[-1]) < 30:
        merged[-2] = (merged[-2] + " " + merged[-1]).strip()
        merged.pop()

    return merged


def _split_text_strict_30_70(llm: LLMClient, header: str, text: str) -> list[dict]:
    """
    Split a SINGLE text group into 30–70 word panels.
    1) Try LLM panel split
    2) If invalid, do sentence_reflow -> deterministic chunking
    Returns list of {header, content, word_count}
    """
    text = text.strip()
    if not text:
        return []

    # Fast path
    wc = word_count(text)
    if wc <= 70:
        return [{"header": header, "content": text, "word_count": wc}]

    # --- Try LLM split first ---
    prompt = panel_semantic_slides_prompt(header=header, source_text=text)
    raw = llm.call(prompt)
    result = raw if isinstance(raw, dict) else {}
    slides = result.get("slides", [])

    ok = True
    finalized: list[dict] = []
    for i, s in enumerate(slides):
        c = (s.get("content") or "").strip()
        w = word_count(c)
        if w < 30 or w > 70 or not c:
            ok = False
            break
        finalized.append({
            "header": header if i == 0 else f"{header} (continued)",
            "content": c,
            "word_count": w,
        })

    if ok and len(finalized) >= 2:
        return finalized

    # --- Fallback: sentence reflow indexes + deterministic chunking ---
    reflow_prompt = strict_sentence_reflow_prompt(text)
    reflow_raw = llm.call(reflow_prompt)
    reflow = (reflow_raw or {}).get("sentence_reflow", {})
    indexes = reflow.get("indexes", [])

    sentences = _sentences_from_reflow(text, indexes if isinstance(indexes, list) else [])
    if not sentences:
        # final fallback: keep unsplit rather than lose text
        return [{"header": header, "content": text, "word_count": wc}]

    chunks = _chunk_sentences_30_70(sentences)

    out = []
    for i, ch in enumerate(chunks):
        out.append({
            "header": header if i == 0 else f"{header} (continued)",
            "content": ch,
            "word_count": word_count(ch),
        })
    return out

def run_stage2_5(module_stage2: Dict[str, Any], llm: LLMClient) -> Dict[str, Any]:
    suggestions = {
        "module_id": module_stage2.get("module_title"),
        "slides": {}
    }

    for slide in module_stage2.get("slides", []):
        slide_id = slide.get("id")
        slide_type = slide.get("type", slide.get("slide_type"))

        slide_suggestions: Dict[str, Any] = {}

        # 🔒 LOCK: Stage 2.5 must NEVER touch Engage slides
        if slide_type in ("engage", "engage1", "engage2"):
            slide_suggestions["meta"] = {
                "id": slide_id,
                "header": slide.get("header"),
                "type": slide_type,
            }
            slide_suggestions["final"] = {
                "action": "keep",
                "reason": "Engage slides are immutable in Stage 2.5",
            }
            suggestions["slides"][slide_id] = slide_suggestions
            continue

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

            panel_text = " ".join(b["text"] for b in paragraph_blocks).strip()
            if not panel_text and bullet_blocks:
                panel_wc = 0
            panel_wc = word_count(panel_text) if panel_text else 0

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
            elif routing == PanelRouting.SEMANTIC_INDEX:
                # ✅ Paragraph-boundary aware grouping:
                # Group 1 = paragraph 1
                # Group 2 = remaining paragraphs combined
                paragraph_texts = [b["text"].strip() for b in paragraph_blocks if b.get("text", "").strip()]

                groups: list[str] = []
                if paragraph_texts:
                    groups.append(paragraph_texts[0])
                if len(paragraph_texts) > 1:
                    groups.append(" ".join(paragraph_texts[1:]).strip())

                # Now enforce 30–70 within each group (without crossing paragraph boundaries)
                built_slides: list[dict] = []
                for gi, gtext in enumerate(groups):
                    base_header = slide.get("header") if gi == 0 else f"{slide.get('header')} (continued)"
                    split_parts = _split_text_strict_30_70(llm, base_header, gtext)

                    # If the splitter returned continued headers internally, keep them as-is
                    built_slides.extend(split_parts)

                slide_suggestions["panel_final"] = {
                    "action": "split" if len(built_slides) > 1 else "keep",
                    "source_word_count": panel_wc,
                    "slides": built_slides if built_slides else [
                        {"header": slide.get("header"), "content": panel_text, "word_count": panel_wc}
                    ],
                }

            elif routing == PanelRouting.SEMANTIC_SPLIT:
                # Single paragraph overlong → split within that paragraph
                split_parts = _split_text_strict_30_70(llm, slide.get("header"), panel_text)
                slide_suggestions["panel_final"] = {
                    "action": "split" if len(split_parts) > 1 else "keep",
                    "source_word_count": panel_wc,
                    "slides": split_parts if split_parts else [
                        {"header": slide.get("header"), "content": panel_text, "word_count": panel_wc}
                    ],
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
