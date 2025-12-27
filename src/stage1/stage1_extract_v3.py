from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

from docx import Document


def normalize(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\u00A0", " ").split()).strip()


def looks_like_intro_cue(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return False

    # strong cue: ends with colon
    if t.endswith(":"):
        return True

    # common instructional cues seen in your modules
    cues = [
        "for example",
        "will focus on",
        "you will be able to",
        "the following",
        "include",
        "includes",
        "are",
        "are the",
        "the main objectives",
        "main objectives",
        "will be able",
        "will learn",
        "will discuss",
        "focuses on",
    ]
    return any(cue in t for cue in cues)


def looks_like_bullet_item(text: str) -> bool:
    # keep this simple and robust: bullets are usually not huge paragraphs
    # (allows full sentences, but blocks very long prose)
    return len(text) <= 220


def extract_tables_v3(docx_path: Path) -> Dict[str, Any]:
    doc = Document(str(docx_path))

    module = {"module_title": docx_path.stem, "slides": []}
    slide_index = 0

    def finalize_slide(slide, columns):
        notes = "\n".join(columns.get("notes and instructions", []))
        slide["notes"] = notes

        notes_lower = notes.lower()
        if "slide type = engage 1" in notes_lower:
            slide["slide_type"] = "engage1"
        elif "slide type = engage 2" in notes_lower:
            slide["slide_type"] = "engage2"
        else:
            slide["slide_type"] = "panel"

        if "image" in columns and columns["image"]:
            img = " ".join(columns["image"])
            if img.lower() != "button labels":
                slide["image"] = img

        blocks = []

        for txt in columns.get("english text", []):
            blocks.append({"type": "paragraph", "text": txt})

        bullet_items = columns.get("english text__bullets", [])
        if bullet_items:
            blocks.append({"type": "bullets", "items": bullet_items})

        slide["content"]["blocks"] = blocks

        if slide["slide_type"] in ("engage1", "engage2"):
            labels = []
            for txt in columns.get("button labels", []):
                labels.extend([p.strip() for p in txt.split("|") if p.strip()])
            if labels:
                slide["content"]["button_labels"] = labels

    for tbl in doc.tables:
        if len(tbl.rows) < 3:
            continue

        row_idx = 0
        slide = None
        columns = {}
        col_labels = []
        in_button_labels = False

        while row_idx < len(tbl.rows):
            row = tbl.rows[row_idx]
            first_cell = normalize(row.cells[0].text)

            if first_cell.lower().startswith("slide (header)"):
                if slide:
                    finalize_slide(slide, columns)
                    module["slides"].append(slide)

                slide_index += 1
                slide = {
                    "id": f"slide_{slide_index:03d}",
                    "header": first_cell,
                    "slide_type": "panel",
                    "image": None,
                    "notes": "",
                    "content": {"blocks": []},
                }

                label_row = tbl.rows[row_idx + 1]
                col_labels = [normalize(c.text).lower() for c in label_row.cells]
                columns = {label: [] for label in col_labels if label}
                in_button_labels = False

                row_idx += 2
                continue

            # content row
            for idx, cell in enumerate(row.cells):
                if idx >= len(col_labels):
                    continue
                label = col_labels[idx]
                if not label:
                    continue

                # gather paragraph objects (not just text) so we can separate list vs non-list
                paras = [p for p in cell.paragraphs if normalize(p.text)]
                if not paras:
                    continue

                # button labels marker row
                first_text = normalize(paras[0].text).lower()
                if first_text == "button labels" and idx == 0:
                    in_button_labels = True
                    continue

                if in_button_labels and label == "english text":
                    columns.setdefault("button labels", []).extend(normalize(p.text) for p in paras)
                    continue

                # --- FIX #1: handle mixed list + non-list paragraphs in same cell ---
                list_items = []
                non_list = []
                for p in paras:
                    txt = normalize(p.text)
                    if p.style and p.style.name == "List Paragraph":
                        list_items.append(txt)
                    else:
                        non_list.append(txt)

                if list_items:
                    # keep intro/non-list paragraphs AND bullets
                    if non_list:
                        columns[label].extend(non_list)
                    columns.setdefault(label + "__bullets", []).extend(list_items)
                    continue

                # --- FIX #2: only infer bullets when structure strongly suggests it ---
                texts = [normalize(p.text) for p in paras if normalize(p.text)]

                if label == "english text":
                    # Find a trailing run of 2+ candidate bullet items
                    # Example pattern: [intro, item, item, item]
                    if len(texts) >= 3:
                        intro = texts[0]
                        tail = texts[1:]

                        if looks_like_intro_cue(intro) and len(tail) >= 2 and all(looks_like_bullet_item(t) for t in tail):
                            columns[label].append(intro)
                            columns.setdefault(label + "__bullets", []).extend(tail)
                            continue

                # default: all are paragraphs
                columns[label].extend(texts)

            row_idx += 1

        if slide:
            finalize_slide(slide, columns)
            module["slides"].append(slide)

    return module


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Stage 1 v3 extractor (fixed bullets + no loss)")
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    args = parser.parse_args()

    module = extract_tables_v3(Path(args.in_path))
    Path(args.out_path).write_text(
        json.dumps(module, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"✅ Extracted {len(module['slides'])} slides")


if __name__ == "__main__":
    main()

