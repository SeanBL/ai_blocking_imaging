# src/stage3/writer_docx.py

from __future__ import annotations
from typing import List, Dict, Any
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import pathlib


def ensure_styles(doc: Document) -> None:
    """
    Create or adjust a few basic styles for headings if needed.
    We keep it simple and mostly rely on built-in styles.
    """
    styles = doc.styles

    # Make sure Heading 1, Heading 2, Heading 3 exist (they do in a normal template)
    # You can tweak font sizes, bold, etc. later if desired.
    for style_name in ["Heading 1", "Heading 2", "Heading 3"]:
        if style_name not in styles:
            styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)


def add_block_to_doc(doc: Document, block: Dict[str, Any]) -> None:
    """
    Add a single Stage 2D block into the DOCX.
    Includes:
      • Page title
      • Page content
      • Engage points with button labels (Option 2 format)
      • Engage2 steps with single button label
      • Image placeholder
      • Quiz questions
    """
    header = block.get("header", "Untitled Section")
    pages: List[Dict[str, Any]] = block.get("pages", [])
    quiz: List[Dict[str, Any]] = block.get("quiz", [])

    # -------------------------------
    # Header
    # -------------------------------
    h1 = doc.add_heading(header, level=1)
    h1.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # -------------------------------
    # Pages
    # -------------------------------
    for page in pages:
        page_type = page.get("type", "page")
        title = page.get("title", "")
        content = page.get("content", "")

        # Page title
        if title:
            doc.add_heading(title, level=2)

        # Image placeholder
        if page.get("image"):
            p_img = doc.add_paragraph()
            p_img.add_run(f"Image: {page['image']}").italic = True

        # Main content
        if content:
            doc.add_paragraph(content)

        # -------------------------------
        # ENGAGE (multiple buttons)
        # -------------------------------
        if page_type == "engage":
            engage_points = page.get("engage_points", [])
            button_labels = page.get("engage_button_labels", [])

            for point, label in zip(engage_points, button_labels):
                # Bullet point
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(point)

                # Indented button label
                p2 = doc.add_paragraph()
                r = p2.add_run(f"Button Label: {label}")
                p2.paragraph_format.left_indent = doc.styles['Normal'].paragraph_format.left_indent + 400000  # approx 0.5 inch
                r.italic = True

        # -------------------------------
        # ENGAGE2 (single button for all steps)
        # -------------------------------
        elif page_type == "engage2":
            steps = page.get("engage2_steps", [])
            button_label = page.get("engage2_button_label", "")

            # Numbered steps
            for step in steps:
                p = doc.add_paragraph(style="List Number")
                p.add_run(step)

            # Single button label (indented)
            if button_label:
                p2 = doc.add_paragraph()
                r = p2.add_run(f"Button Label: {button_label}")
                p2.paragraph_format.left_indent = doc.styles['Normal'].paragraph_format.left_indent + 400000
                r.italic = True

        doc.add_paragraph()  # spacing

    # -------------------------------
    # Quiz section
    # -------------------------------
    if quiz:
        doc.add_heading(f"Quiz: {header}", level=3)

        for idx, q in enumerate(quiz, start=1):
            question = q.get("question", "")
            options = q.get("options", [])
            correct = q.get("correct_answers", [])
            qtype = q.get("type", "")

            # Question
            doc.add_paragraph(f"Q{idx}. {question} ({qtype})")

            # Options
            label_letters = "abcdefghijklmnopqrstuvwxyz"
            for opt_idx, opt_text in enumerate(options):
                doc.add_paragraph(f"   {label_letters[opt_idx]}) {opt_text}")

            # Correct answers (for authoring review only)
            if correct:
                p = doc.add_paragraph()
                p.add_run(f"Correct: {', '.join(correct)}").bold = True

            doc.add_paragraph()  # spacing


def build_docx_from_stage2(stage2_dir, output_path, module_title=None) -> None:
    """
    Read all Stage 2D final JSON files and build a DOCX preview.
    """
    import json
    import pathlib

    doc = Document()
    ensure_styles(doc)

    if module_title:
        p = doc.add_paragraph()
        r = p.add_run(module_title)
        r.bold = True
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        doc.add_paragraph()

    for path in sorted(pathlib.Path(stage2_dir).glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        add_block_to_doc(doc, data)
        doc.add_page_break()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"DOCX written to: {output_path}")

