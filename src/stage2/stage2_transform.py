from __future__ import annotations

import argparse
import json

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

def normalize_engage1(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Normalize Engage 1 slide.
    Assumes Stage 1 already provided intro + items structure.
    """

    ensure_uuid(slide, index)

    return {
        "uuid": slide["uuid"],
        "type": "engage",
        "header": normalize_ws(slide.get("header")),
        "notes": normalize_ws(slide.get("notes")) or None,
        "image": slide.get("image"),
        "intro": slide.get("content", {}).get("intro", {}),
        "items": slide.get("content", {}).get("items", []),
    }

def normalize_engage2(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    ensure_uuid(slide, index)

    # 🔒 Stage 2 MUST preserve button labels from Stage 1
    button_labels = (
        slide.get("content", {}).get("button_labels", [])
        if isinstance(slide.get("content"), dict)
        else []
    )

    raw_build = slide.get("build") or []

    if not raw_build:
        raw_build = extract_engage2_build_from_blocks(slide)

    if slide.get("slide_type") == "engage2" and not raw_build:
        raise ValueError(f"Engage2 slide {slide['uuid']} produced empty build")

    return {
        "uuid": slide["uuid"],
        "type": "engage2",
        "header": normalize_ws(slide.get("header")),
        "notes": normalize_ws(slide.get("notes")) or None,
        "image": slide.get("image"),
        "button_labels": button_labels,
        "build": raw_build,
    }

def normalize_panel(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    ensure_uuid(slide, index)

    return {
        "uuid": slide["uuid"],
        "type": "panel",
        "header": normalize_ws(slide.get("header")),
        "notes": normalize_ws(slide.get("notes")) or None,
        "image": slide.get("image"),
        "content": slide.get("content", {"blocks": []}),
    }

def transform_slide(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Stage 2 routing.
    - NO pedagogy inference
    - NO engage creation
    - Slide type is authoritative from Stage 1
    """

    ensure_uuid(slide, index)

    slide_type = normalize_ws(slide.get("slide_type")).lower()

    if slide_type == "panel":
        return normalize_panel(slide, index)

    if slide_type == "engage1":
        return normalize_engage1(slide, index)

    if slide_type == "engage2":
        return normalize_engage2(slide, index)

    # Safety fallback (should never happen)
    return normalize_panel(slide, index)

def extract_engage2_build_from_blocks(slide: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Engage2 fallback builder.

    RULES:
    - All paragraphs become build steps
    - EXCEPT the final paragraph if it is a button label
    - Button label is extracted, not invented
    """

    blocks = slide.get("content", {}).get("blocks", [])
    paragraphs: List[str] = []

    for b in blocks:
        if not isinstance(b, dict):
            continue
        if b.get("type") != "paragraph":
            continue

        text = normalize_ws(b.get("text"))
        if text:
            paragraphs.append(text)

    build: List[Dict[str, Any]] = []
    for text in paragraphs:
        build.append({
            "title": "",
            "content": [text],
        })

    return build

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
