import sys
from pathlib import Path

# Ensure src/ is on the Python path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from stage2_6.apply_semantic_index import apply_semantic_index_executor



def test_slide_001_splits_into_two_valid_panels():
    module_stage2 = {
        "slides": [
            {
                "id": "slide_001",
                "type": "panel",
                "header": "Intro",
                "content": [
                    (
                        "Children in Low Middle-Income Countries (LMIC) face multiple "
                        "threats from infectious diseases, such as HIV/AIDS, diarrhea, "
                        "malaria, and pneumonia, which can negatively affect their "
                        "development, particularly when they occur in the context of "
                        "malnutrition. In addition, diagnostic and treatment services "
                        "for children with developmental disabilities are limited in "
                        "these settings. Advancing child health in LMIC focuses on "
                        "addressing malnutrition, infectious diseases, and limited "
                        "access to quality care such as breast feeding, vaccination, "
                        "proper nutrition, and strengthening access to health care."
                    )
                ],
            }
        ]
    }

    suggestions = {
        "slides": {
            "slide_001": {
                "routing": "semantic_split",
                "strict_sentence_boundaries": {
                    "sentence_reflow": {
                        "indexes": [0, 227, 454]
                    }
                }
            }
        }
    }

    new_module, debug = apply_semantic_index_executor(module_stage2, suggestions)

    slides = new_module["slides"]

    # ✅ Must split into exactly 2 slides
    assert len(slides) == 2

    # ✅ Each slide must be ≤70 words
    for slide in slides:
        wc = len(slide["content"][0].split())
        assert wc <= 70

    # ✅ Text must be preserved (concatenation matches original)
    reconstructed = " ".join(s["content"][0] for s in slides)
    original = module_stage2["slides"][0]["content"][0]
    assert reconstructed.replace(" ", "") == original.replace(" ", "")
