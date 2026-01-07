from pathlib import Path
from src.stage1.stage1_extract_v3 import extract_tables_v3


def test_stage1_preserves_prose_and_bullets():
    module = extract_tables_v3(Path("tests/fixtures/mixed_prose_and_bullets.docx"))

    found = False

    for slide in module["slides"]:
        blocks = slide["content"]["blocks"]

        has_paragraph = any(b["type"] == "paragraph" for b in blocks)
        has_bullets = any(b["type"] == "bullets" for b in blocks)

        if has_paragraph and has_bullets:
            found = True
            break

    assert found, "No slide preserved mixed prose + bullets"
