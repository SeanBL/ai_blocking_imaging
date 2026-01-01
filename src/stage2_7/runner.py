import json
import re
from pathlib import Path
from typing import Dict, Any

from .engage_detect import detect_engage_need
from .llm_engage import synthesize_engage


def _extract_source_text(slide: Dict[str, Any]) -> str:
    """
    Extract unstructured text to feed into the LLM.

    Stage 2 engage slides already contain text in intro.content.
    """
    # --- Case 1: Engage slide (Stage 2 shape) ---
    if slide.get("type") == "engage":
        intro = slide.get("intro", {})
        content = intro.get("content")
        if isinstance(content, list):
            return " ".join(c for c in content if isinstance(c, str)).strip()

    # --- Case 2: Legacy / panel slides ---
    if isinstance(slide.get("english_text_raw"), list):
        return "\n".join(slide["english_text_raw"]).strip()

    if isinstance(slide.get("english_text"), list):
        return "\n".join(slide["english_text"]).strip()

    content = slide.get("content", {})
    pages = content.get("pages", [])

    texts = []
    for block in pages:
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            texts.append(block["text"])

    return "\n".join(texts).strip()

def _norm(s: str) -> str:
    """
    Normalize text for robust exact-match checks:
    - collapse whitespace
    - normalize unicode spaces
    - strip
    """
    if not isinstance(s, str):
        return ""
    s = s.replace("\u00A0", " ")  # NBSP
    s = " ".join(s.split())       # collapse whitespace
    return s.strip()

def _sentences(text: str) -> list[str]:
    text = _norm(text)
    return [_norm(s) for s in re.split(r'(?<=[.!?])\s+', text) if _norm(s)]

def _all_sentences_preserved(source: str, engage_block: dict) -> bool:
    source_sents = _sentences(source)
    output_texts = []

    intro = engage_block.get("intro", {})
    if "content" in intro:
        output_texts.extend(intro.get("content", []))
    elif "text" in intro:
        output_texts.append(intro.get("text", ""))

    for item in engage_block.get("items", []):
        if "content" in item:
            output_texts.extend(item.get("content", []))
        elif "text" in item:
            output_texts.append(item.get("text", ""))

    combined = _norm(" ".join(output_texts))
    return all(_norm(sent) in combined for sent in source_sents)

def _is_intro_framing_sentence(
    sentence: str,
    following_sentences: list[str],
) -> bool:
    """
    Decide whether a sentence is a framing / bridge sentence
    that should belong in the intro, not as an engage item.
    """

    s = sentence.strip().lower()

    # --- Strong structural cues ---
    if s.endswith(":"):
        return True

    if s.endswith("the following.") or s.endswith("as follows."):
        return True

    # --- Grammatical / semantic cues ---
    abstract_nouns = (
        "objective", "objectives",
        "goal", "goals",
        "aim", "aims",
        "purpose", "purposes",
        "area", "areas",
        "focus", "focuses",
    )

    if any(noun in s for noun in abstract_nouns):
        # Look ahead: are we introducing a list?
        to_count = sum(
            1 for nxt in following_sentences[:5]
            if nxt.strip().lower().startswith("to ")
        )
        if to_count >= 2:
            return True

    return False


def _normalize_engage1_shape(engage_block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize LLM Engage 1 output into the exact Stage 2 schema
    using robust sentence-role classification.
    """

    intro_sentences = []

    # Start with intro sentence from LLM
    intro_text = engage_block.get("intro", {}).get("text")
    if intro_text:
        intro_sentences.append(intro_text.strip())

    raw_items = engage_block.get("items", [])
    item_texts = [item.get("text", "").strip() for item in raw_items]

    items = []

    for idx, item in enumerate(raw_items):
        text = item.get("text", "").strip()
        label = item.get("button_label", "").strip()

        following = item_texts[idx + 1 :]

        # Robust framing detection
        if _is_intro_framing_sentence(text, following):
            intro_sentences.append(text)
            continue

        items.append({
            "title": "",
            "content": [text],
            "image": None,
            "button_label": label
        })

    return {
        "type": "engage",
        "intro": {
            "title": "",
            "content": [" ".join(intro_sentences)]
        },
        "items": items
    }


def run_stage2_7(in_path: Path, out_path: Path, client) -> None:
    """
    Stage 2.7 runner:
    - Detect engage intent
    - Synthesize engage if needed
    - Otherwise pass-through
    """
    module: Dict[str, Any] = json.loads(in_path.read_text(encoding="utf-8"))

    slides = module.get("slides", [])
    if not isinstance(slides, list):
        raise ValueError("module.slides must be a list")

    for slide in slides:
        print(f"\n--- SLIDE {slide.get('id')} ---")
        decision = detect_engage_need(slide)
        print("DETECT RESULT:", decision)

        if not decision:
            continue

        print("ENGAGE SYNTHESIS TRIGGERED")

        source_text = _extract_source_text(slide)
        print("SOURCE TEXT LENGTH:", len(source_text))

        if not source_text:
            continue  # fail-safe: do nothing if no text

        engage_block = synthesize_engage(
            source_text=source_text,
            engage_type=decision["engage_type"],
            client=client
        )

        print("LLM RETURNED:", engage_block.keys())

        # Normalize to exact Stage 2 Engage 1 schema
        if decision["engage_type"] == "engage":
            engage_block = _normalize_engage1_shape(engage_block)

        # 🔒 HARD GUARANTEE: no sentence loss allowed
        if not _all_sentences_preserved(source_text, engage_block):
            raise RuntimeError(
                f"Stage 2.7 ERROR: Sentence loss detected in slide {slide.get('id')}"
            )
        
        # Replace top-level engage structure
        slide["type"] = "engage"
        slide["intro"] = engage_block["intro"]
        slide["items"] = engage_block["items"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(module, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
