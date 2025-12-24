from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

from docx import Document


def normalize(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\u00A0", " ").split()).strip()


def extract_tables_v3(docx_path: Path) -> Dict[str, Any]:
    """
    v3 extractor based on *actual observed Word structure*:

    - A single Word table may contain MULTIPLE slides
    - Each slide starts with a row whose first cell starts with "Slide (Header)"
    - The NEXT row contains column labels
    - Rows after that are content until the next Slide (Header)
    """

    doc = Document(str(docx_path))

    module = {
        "module_title": docx_path.stem,
        "slides": []
    }

    slide_index = 0

    def finalize_slide(slide, columns):
        """Convert collected column data into slide fields."""

        # Notes
        notes = "\n".join(columns.get("notes and instructions", []))
        slide["notes"] = notes

        notes_lower = notes.lower()
        if "slide type = engage 1" in notes_lower:
            slide["slide_type"] = "engage1"
        elif "slide type = engage 2" in notes_lower:
            slide["slide_type"] = "engage2"
        else:
            slide["slide_type"] = "panel"

        # Image
        if "image" in columns and columns["image"]:
            img = " ".join(columns["image"])
            if img.lower() != "button labels":
                slide["image"] = img

        # English text → blocks
        blocks = []
        for txt in columns.get("english text", []):
            parts = [p.strip() for p in txt.split("|") if p.strip()]
            for p in parts:
                blocks.append({"type": "paragraph", "text": p})

        slide["content"]["blocks"] = blocks

        # Button labels (engage only)
        if slide["slide_type"] in ("engage1", "engage2"):
            labels = []
            for txt in columns.get("button labels", []):
                labels.extend([p.strip() for p in txt.split("|") if p.strip()])
            if labels:
                slide["content"]["button_labels"] = labels

    # ==========================================================
    # MAIN LOOP
    # ==========================================================
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

            # -----------------------------
            # NEW SLIDE DETECTED
            # -----------------------------
            if first_cell.lower().startswith("slide (header)"):
                # Flush previous slide
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
                    "content": {"blocks": []}
                }

                # Read column labels from NEXT row
                label_row = tbl.rows[row_idx + 1]
                col_labels = [
                    normalize(c.text).lower()
                    for c in label_row.cells
                ]

                columns = {label: [] for label in col_labels if label}
                in_button_labels = False

                row_idx += 2
                continue

            # -----------------------------
            # CONTENT ROW
            # -----------------------------
            for idx, cell in enumerate(row.cells):
                if idx >= len(col_labels):
                    continue

                label = col_labels[idx]
                if not label:
                    continue

                text = normalize(cell.text)
                if not text:
                    continue

                # Button Labels marker
                if text.lower() == "button labels" and idx == 0:
                    in_button_labels = True
                    continue

                if in_button_labels and label == "english text":
                    columns.setdefault("button labels", []).append(text)
                    continue

                columns[label].append(text)

            row_idx += 1

        # Flush last slide in table
        if slide:
            finalize_slide(slide, columns)
            module["slides"].append(slide)

    return module



def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Stage 1 v3 extractor (structure-safe)")
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    args = parser.parse_args()

    module = extract_tables_v3(Path(args.in_path))
    Path(args.out_path).write_text(
        json.dumps(module, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"✅ Extracted {len(module['slides'])} slides")


if __name__ == "__main__":
    main()
