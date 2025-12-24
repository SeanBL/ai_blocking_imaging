from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

from ...utils.llm_client_realtime import LLMClientRealtime


# -----------------------------------------------------------
# Load the prompt template
# -----------------------------------------------------------

PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "prompt_image_select.txt"
)

if not PROMPT_PATH.exists():
    raise FileNotFoundError(f"Image selection prompt not found at: {PROMPT_PATH}")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    IMAGE_PROMPT_TEMPLATE = f.read()


# -----------------------------------------------------------
# Build prompt for LLM
# -----------------------------------------------------------

def build_prompt(
    header: str,
    pages: List[Dict[str, Any]],
    image_catalog: List[Dict[str, Any]],
) -> str:

    pages_json = json.dumps(pages, ensure_ascii=False, indent=2)
    catalog_json = json.dumps(image_catalog, ensure_ascii=False, indent=2)

    return (
        IMAGE_PROMPT_TEMPLATE
        .replace("<<<HEADER>>>", header)
        .replace("<<<PAGES_JSON>>>", pages_json)
        .replace("<<<IMAGE_CATALOG_JSON>>>", catalog_json)
    )


# -----------------------------------------------------------
# Stage 2E — Image selection (FINAL UNITS ONLY)
# -----------------------------------------------------------

def select_images(
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
    image_catalog: List[Dict[str, Any]],
    llm: LLMClientRealtime,
) -> Dict[str, Any]:
    """
    Produces:
    {
      "header": "...",
      "images": [
        {
          "unit_id": "u01",
          "page_index": 0,
          "image_id": "dna_helix"
        }
      ]
    }
    """

    # -------------------------------------------------------
    # Collect pages deterministically from FINAL UNITS
    # -------------------------------------------------------

    pages: List[Dict[str, Any]] = []
    page_map: List[Dict[str, Any]] = []

    for unit in units:
        if unit.get("unit_type") != "page":
            continue

        for page_idx, page in enumerate(unit.get("pages", [])):
            paragraph_indices = page.get("paragraph_indices", [])
            text = " ".join(paragraphs[i] for i in paragraph_indices).strip()

            pages.append({
                "page_index": len(pages),
                "text": text,
            })

            page_map.append({
                "unit_id": unit.get("unit_id"),
                "page_index": page_idx,
            })

    # -------------------------------------------------------
    # No catalog → null images
    # -------------------------------------------------------

    if not image_catalog:
        return {
            "header": header,
            "images": [
                {
                    "unit_id": page_map[i]["unit_id"],
                    "page_index": page_map[i]["page_index"],
                    "image_id": None,
                }
                for i in range(len(page_map))
            ],
        }

    # -------------------------------------------------------
    # LLM selection
    # -------------------------------------------------------

    prompt = build_prompt(header, pages, image_catalog)
    response = llm.call_json(prompt)

    if "images" not in response:
        raise ValueError("LLM did not return required 'images' field.")

    # -------------------------------------------------------
    # Re-map images back to units/pages
    # -------------------------------------------------------

    images_out: List[Dict[str, Any]] = []

    for i, img in enumerate(response["images"]):
        images_out.append({
            "unit_id": page_map[i]["unit_id"],
            "page_index": page_map[i]["page_index"],
            "image_id": img.get("image_id"),
        })

    return {
        "header": header,
        "images": images_out,
    }

