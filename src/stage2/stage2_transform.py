from __future__ import annotations

import argparse
import json
import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def unpack_stage1_content(content: Any) -> Dict[str, Any]:
    """
    Unpacks Stage 1 v3 content.

    Supports BOTH:
      - content as dict: { "blocks": [...] }
      - content as list of serialized strings (legacy)

    NEVER drops text.
    """
    paragraphs: List[str] = []
    button_labels: List[str] | None = None

    # ----------------------------------
    # Case 1: content is already a dict
    # ----------------------------------
    if isinstance(content, dict):
        blocks = content.get("blocks", [])
        for block in blocks:
            if block.get("type") == "paragraph":
                text = normalize_ws(block.get("text"))
                if text:
                    paragraphs.append(text)

        if "button_labels" in content and isinstance(content["button_labels"], list):
            button_labels = [
                normalize_ws(lbl)
                for lbl in content["button_labels"]
                if normalize_ws(lbl)
            ]

        return {
            "paragraphs": paragraphs,
            "button_labels": button_labels,
        }

    # ----------------------------------
    # Case 2: content is a list (legacy)
    # ----------------------------------
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                blocks = item.get("blocks", [])
                for block in blocks:
                    if block.get("type") == "paragraph":
                        text = normalize_ws(block.get("text"))
                        if text:
                            paragraphs.append(text)

                if "button_labels" in item and isinstance(item["button_labels"], list):
                    button_labels = [
                        normalize_ws(lbl)
                        for lbl in item["button_labels"]
                        if normalize_ws(lbl)
                    ]
                continue

            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    paragraphs.append(normalize_ws(stripped))

        return {
            "paragraphs": paragraphs,
            "button_labels": button_labels,
        }

    # ----------------------------------
    # Fallback: preserve anything else
    # ----------------------------------
    text = normalize_ws(content)
    if text:
        paragraphs.append(text)

    return {
        "paragraphs": paragraphs,
        "button_labels": button_labels,
    }


# -----------------------------
# Whitespace + text normalization
# -----------------------------
def normalize_ws(s: Any) -> str:
    """
    Deterministic whitespace normalization:
    - converts NBSP to space
    - trims
    - collapses internal whitespace to single spaces
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\u00A0", " ")
    s = " ".join(s.split())
    return s.strip()


def normalize_paragraph_list(x: Any) -> List[str]:
    """
    Accepts None | str | list[str] and returns a cleaned list[str].
    Does NOT split paragraphs beyond what already exists.
    """
    if x is None:
        return []
    if isinstance(x, str):
        s = normalize_ws(x)
        return [s] if s else []
    if isinstance(x, list):
        out: List[str] = []
        for item in x:
            s = normalize_ws(item)
            if s:
                out.append(s)
        return out
    # fallback: coerce to string
    s = normalize_ws(x)
    return [s] if s else []


def first_present(d: Dict[str, Any], keys: List[str]) -> Tuple[Optional[str], Any]:
    """
    Returns (key, value) for the first key that exists in dict d.
    """
    for k in keys:
        if k in d:
            return k, d[k]
    return None, None


def ensure_uuid(slide: Dict[str, Any], index: int, prefix: str = "stage2") -> None:
    """
    Stage 2 should preserve UUID if present. If missing, fill deterministically.
    """
    if normalize_ws(slide.get("uuid")):
        slide["uuid"] = normalize_ws(slide.get("uuid"))
        return
    slide["uuid"] = f"{prefix}-{index:03d}"


# -----------------------------
# Engage item helpers
# -----------------------------
def default_engage_item_label(i: int) -> str:
    return f"Item {i}"


def default_engage2_button_label() -> str:
    return "Next"


def normalize_text_block(obj: Dict[str, Any], title_keys: List[str], content_keys: List[str]) -> Dict[str, Any]:
    """
    Normalizes a generic text block to:
      { "title": str, "content": List[str] }
    """
    _, raw_title = first_present(obj, title_keys)
    _, raw_content = first_present(obj, content_keys)

    title = normalize_ws(raw_title)
    content = normalize_paragraph_list(raw_content)

    return {"title": title, "content": content}


def normalize_engage_intro(slide: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical shape:
      intro: { title: str, content: List[str] }
    Accepts several possible Stage 1 variants.
    """
    intro = slide.get("intro")

    # Case 1: intro already dict-like
    if isinstance(intro, dict):
        normalized = normalize_text_block(
            intro,
            title_keys=["title", "header", "heading", "label"],
            content_keys=["content", "text", "paragraphs", "body"],
        )
        return normalized

    # Case 2: intro is a string or list (content only)
    if isinstance(intro, (str, list)) or intro is None:
        return {"title": "", "content": normalize_paragraph_list(intro)}

    # Case 3: Stage 1 stored intro elsewhere
    # Try some common fallbacks:
    _, intro_title = first_present(slide, ["intro_title", "introHeading", "intro_header"])
    _, intro_content = first_present(slide, ["intro_content", "intro_text", "introText", "introBody"])

    title = normalize_ws(intro_title)
    content = normalize_paragraph_list(intro_content)

    # If still empty, allow missing intro entirely (empty)
    return {"title": title, "content": content}


def normalize_engage_items(slide: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Canonical shape for Engage 1 items:
      items: [
        { button_label: str, title: str, content: List[str] }
      ]
    Accepts many possible keys from Stage 1.
    """
    # Find items array under common names
    _, raw_items = first_present(slide, ["items", "points", "engage_items", "engagePoints", "engage_points"])

    if raw_items is None:
        raw_items = []

    # Sometimes Stage 1 could output a single dict/string
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if isinstance(raw_items, str):
        raw_items = [{"content": raw_items}]
    if not isinstance(raw_items, list):
        raw_items = []

    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        if isinstance(item, str):
            # content-only item
            out.append(
                {
                    "button_label": default_engage_item_label(idx),
                    "title": "",
                    "content": normalize_paragraph_list(item),
                }
            )
            continue

        if not isinstance(item, dict):
            # unknown type -> coerce
            out.append(
                {
                    "button_label": default_engage_item_label(idx),
                    "title": "",
                    "content": normalize_paragraph_list(item),
                }
            )
            continue

        # Button label
        _, raw_btn = first_present(item, ["button_label", "button", "label", "btn", "buttonLabel"])
        btn = normalize_ws(raw_btn) or default_engage_item_label(idx)

        # Title/content
        normalized_block = normalize_text_block(
            item,
            title_keys=["title", "header", "heading", "name"],
            content_keys=["content", "text", "paragraphs", "body"],
        )

        out.append(
            {
                "button_label": btn,
                "title": normalized_block["title"],
                "content": normalized_block["content"],
            }
        )

    return out


def normalize_engage1(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Normalizes an Engage 1 slide into canonical shape.
    Preserves non-core keys where possible, but guarantees:
      uuid, type, header, notes, intro, items
    """
    ensure_uuid(slide, index)

    slide_out: Dict[str, Any] = dict(slide)  # shallow copy
    slide_out["type"] = "engage"

    slide_out["header"] = normalize_ws(slide.get("header"))
    slide_out["notes"] = normalize_ws(slide.get("notes")) or None

    # canonical intro + items
    slide_out["intro"] = normalize_engage_intro(slide)
    slide_out["items"] = normalize_engage_items(slide)

    # Remove legacy aliases if present (optional cleanliness)
    for k in ["points", "engage_items", "engagePoints", "engage_points"]:
        if k in slide_out:
            slide_out.pop(k, None)

    return slide_out


def normalize_engage2_build(slide: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Canonical engage2 build:
      build: [
        { title: str, content: List[str] }
      ]
    """
    _, raw_build = first_present(slide, ["build", "items", "steps", "sequence", "engage2_items", "engage2Items"])

    if raw_build is None:
        raw_build = []

    if isinstance(raw_build, dict):
        raw_build = [raw_build]
    if isinstance(raw_build, str):
        raw_build = [{"content": raw_build}]
    if not isinstance(raw_build, list):
        raw_build = []

    out: List[Dict[str, Any]] = []
    for item in raw_build:
        if isinstance(item, str):
            out.append({"title": "", "content": normalize_paragraph_list(item)})
            continue

        if not isinstance(item, dict):
            out.append({"title": "", "content": normalize_paragraph_list(item)})
            continue

        normalized_block = normalize_text_block(
            item,
            title_keys=["title", "header", "heading", "name"],
            content_keys=["content", "text", "paragraphs", "body"],
        )
        out.append(normalized_block)

    return out


def normalize_engage2(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Normalizes an Engage 2 slide into canonical shape.
    Guarantees:
      uuid, type, header, notes, button_label, build
    """
    ensure_uuid(slide, index)

    slide_out: Dict[str, Any] = dict(slide)
    slide_out["type"] = "engage2"

    slide_out["header"] = normalize_ws(slide.get("header"))
    slide_out["notes"] = normalize_ws(slide.get("notes")) or None

    # button label: single progressive button
    _, raw_btn = first_present(slide, ["button_label", "button", "label", "buttonLabel"])
    btn = normalize_ws(raw_btn) or default_engage2_button_label()
    slide_out["button_label"] = btn

    slide_out["build"] = normalize_engage2_build(slide)

    # Remove likely legacy keys (optional)
    for k in ["items", "steps", "sequence", "engage2_items", "engage2Items"]:
        if k in slide_out and k != "build":
            slide_out.pop(k, None)

    return slide_out

def normalize_engage2_structure(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    STEP 5A (updated): Normalize Engage 2 structure
    with intro + progressive steps.
    No button label yet.
    """
    ensure_uuid(slide, index)

    content: List[str] = slide.get("content", [])

    if not isinstance(content, list):
        content = []

    intro_content: List[str] = []
    steps: List[Dict[str, Any]] = []

    if content:
        # First paragraph = intro
        intro_content = [content[0]]

        # Remaining paragraphs = steps
        for paragraph in content[1:]:
            steps.append(
                {
                    "content": [paragraph]
                }
            )

    slide_out = dict(slide)
    slide_out["type"] = "engage2"

    slide_out["intro"] = {
        "title": "",
        "content": intro_content,
    }

    slide_out["button"] = {
        "label": ""
    }

    slide_out["steps"] = steps

    # Remove flat content
    slide_out.pop("content", None)

    return slide_out

def apply_engage2_button_label(
    slide: Dict[str, Any],
    original_slide: Dict[str, Any]
) -> Dict[str, Any]:
    """
    STEP 5B: Apply single button label to Engage 2 slide.
    """
    label = None

    content = original_slide.get("content")
    if isinstance(content, dict):
        labels = content.get("button_labels")
        if isinstance(labels, list) and labels:
            label = normalize_ws(labels[0])

    if not label:
        label = "Next"

    slide["button"]["label"] = label
    return slide

def normalize_panel(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Panels: preserve meaning, but MATERIALIZE Stage 1 serialized content blocks
    into real paragraph text.
    """
    ensure_uuid(slide, index)

    slide_out: Dict[str, Any] = dict(slide)

    # Force canonical type
    slide_out["type"] = "panel"

    slide_out["header"] = normalize_ws(slide.get("header"))
    slide_out["notes"] = normalize_ws(slide.get("notes")) or None
    slide_out["image"] = slide.get("image")

    raw_content = slide.get("content")

    if raw_content is not None:
        unpacked = unpack_stage1_content(raw_content)
        slide_out["content"] = unpacked["paragraphs"]
    else:
        slide_out["content"] = []

    return slide_out

def normalize_engage_flat(slide: Dict[str, Any], index: int, engage_type: str) -> Dict[str, Any]:
    """
    STEP 3B: Engage unpacking ONLY.
    Same behavior as panel unpacking, but explicitly for engage slides.
    NO normalization yet.
    """
    slide_out = normalize_panel(slide, index)
    slide_out["type"] = engage_type
    return slide_out

def normalize_engage1_structure(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    STEP 4A: Normalize Engage 1 structure (intro + items).
    No button labels yet.
    """
    ensure_uuid(slide, index)

    content: List[str] = slide.get("content", [])

    # Safety: ensure list
    if not isinstance(content, list):
        content = []

    intro_content: List[str] = []
    items: List[Dict[str, Any]] = []

    if content:
        intro_content = [content[0]]

        for paragraph in content[1:]:
            items.append(
                {
                    "title": "",
                    "content": [paragraph],
                }
            )

    slide_out = dict(slide)
    slide_out["type"] = "engage"

    slide_out["intro"] = {
        "title": "",
        "content": intro_content,
    }

    slide_out["items"] = items

    # Remove flat content
    slide_out.pop("content", None)

    return slide_out

def apply_engage1_button_labels(
    slide: Dict[str, Any],
    original_slide: Dict[str, Any]
) -> Dict[str, Any]:
    """
    STEP 4B: Apply button labels to Engage 1 items.
    Uses Stage 1 button_labels when present.
    """
    items = slide.get("items", [])
    labels = None

    # Pull button labels from original Stage 1 slide if present
    content = original_slide.get("content")
    if isinstance(content, dict):
        labels = content.get("button_labels")

    if not isinstance(labels, list):
        labels = []

    for i, item in enumerate(items):
        if i < len(labels) and normalize_ws(labels[i]):
            item["button_label"] = normalize_ws(labels[i])
        else:
            item["button_label"] = f"Item {i + 1}"

    return slide

def transform_slide(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    STEP 3B: Routing + flat unpacking.
    """
    slide_type = normalize_ws(slide.get("slide_type")).lower()

    if slide_type == "panel":
        return normalize_panel(slide, index)

    if slide_type == "engage1":
        flat = normalize_engage_flat(slide, index, "engage")
        structured = normalize_engage1_structure(flat, index)
        return apply_engage1_button_labels(structured, slide)


    if slide_type == "engage2":
        flat = normalize_engage_flat(slide, index, "engage2")
        structured = normalize_engage2_structure(flat, index)
        return apply_engage2_button_label(structured, slide)


    # Safety fallback
    return normalize_panel(slide, index)




def transform_module_v3_to_stage2(module: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input: Stage 1 module_v3.json
    Output: module_stage2.json (canonical shapes for Engage 1/2; panels preserved)
    """
    out: Dict[str, Any] = dict(module)

    out["module_title"] = normalize_ws(module.get("module_title")) or normalize_ws(module.get("title"))
    slides = module.get("slides")

    if not isinstance(slides, list):
        raise ValueError("Expected module['slides'] to be a list.")

    out_slides: List[Dict[str, Any]] = []
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            # Coerce non-dict slide into a panel-like wrapper
            slide = {"type": "panel", "content": slide}
        out_slides.append(transform_slide(slide, i))

    out["slides"] = out_slides
    return out


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 2 deterministic transformer: module_v3.json -> module_stage2.json (no LLM, no Word parsing)"
    )
    parser.add_argument("input", type=str, help="Path to module_v3.json (Stage 1 output)")
    parser.add_argument("output", type=str, help="Path to write module_stage2.json (Stage 2 output)")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    module_v3 = load_json(in_path)
    module_stage2 = transform_module_v3_to_stage2(module_v3)
    save_json(out_path, module_stage2)

    print(f"✅ Wrote Stage 2 output: {out_path}")


if __name__ == "__main__":
    main()
