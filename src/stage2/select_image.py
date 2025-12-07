from __future__ import annotations
from typing import List, Dict, Any

# Simple keyword-to-image mapping. You can refine this over time.
KEYWORD_IMAGE_MAP = [
    ({"dna", "gene", "genes"}, "dna_helix"),
    ({"chromosome", "chromosomes"}, "chromosomes_diagram"),
    ({"protein", "proteins"}, "protein_synthesis"),
    ({"neuron", "neurons", "brain"}, "brain_outline"),
    ({"movement", "motor"}, "motor_control"),
    ({"symptom", "symptoms", "signs"}, "symptoms_chart"),
    ({"prevent", "prevention", "protect"}, "shield"),
    ({"mutation", "mutations"}, "gene_mutation"),
]

DEFAULT_IMAGE = "generic_health"


def _choose_image_for_page(page: Dict[str, Any]) -> str:
    # Combine all relevant text fields and lowercase them
    text_parts: List[str] = []
    text_parts.append(page.get("title", "") or "")
    text_parts.append(page.get("content", "") or "")
    for pt in page.get("engage_points", []) or []:
        text_parts.append(pt)
    for st in page.get("engage2_steps", []) or []:
        text_parts.append(st)

    text = " ".join(text_parts).lower()

    for keywords, image_id in KEYWORD_IMAGE_MAP:
        if any(keyword in text for keyword in keywords):
            return image_id

    return DEFAULT_IMAGE


def add_images_to_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Stage 2B:
    Take the pages from Stage 2A and attach an "image" field
    using simple keyword-based rules. If a page already has an image,
    we leave it as is.
    """
    new_pages: List[Dict[str, Any]] = []

    for page in pages:
        page_copy = dict(page)  # shallow copy so we don't mutate in place
        if not page_copy.get("image"):
            page_copy["image"] = _choose_image_for_page(page_copy)
        new_pages.append(page_copy)

    return new_pages