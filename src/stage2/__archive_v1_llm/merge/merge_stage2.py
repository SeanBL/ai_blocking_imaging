from __future__ import annotations
from typing import Dict, Any, List, Optional


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

def _make_title(text: str) -> str:
    words = text.split()
    return " ".join(words[:6]).rstrip(",.;")


def _make_uuid(prefix: str, index: int) -> str:
    return f"{prefix}-{index:03d}"


# -----------------------------------------------------------
# MAIN MERGE FUNCTION (FINAL UNITS ONLY)
# -----------------------------------------------------------

def merge_stage2(
    *,
    header: str,
    paragraphs: List[str],
    units: List[Dict[str, Any]],
    engage_data: Dict[str, Any],
    engage2_data: Dict[str, Any],
    labels_data: Dict[str, Any],
    images_data: Dict[str, Any],
    bullet_data: Dict[str, Any],
    quiz_data: Dict[str, Any],
    notes: Optional[str] = None,
) -> Dict[str, Any]:

    pages_out: List[Dict[str, Any]] = []

    # -----------------------------
    # Lookups
    # -----------------------------

    engage_label_lookup = {
        e["paragraph_index"]: e["button_label"]
        for e in labels_data.get("engage_labels", [])
    }

    engage2_label_lookup = {
        tuple(e.get("paragraph_indices", [])): e["button_label"]
        for e in labels_data.get("engage2_labels", [])
    }

    engage2_steps_lookup = {
        e["paragraph_indices"][0]: e.get("engage2_steps", [])
        for e in engage2_data.get("engage2_items", [])
        if e.get("paragraph_indices")
    }

    bullet_lookup = {
        b["paragraph_index"]: b.get("bullet_points", [])
        for b in bullet_data.get("bullet_blocks", [])
    }

    image_lookup = {
        (img["unit_id"], img["page_index"]): img.get("image_id")
        for img in images_data.get("images", [])
    }

    # -----------------------------
    # Build output pages
    # -----------------------------

    page_counter = 0

    for unit in units:
        utype = unit.get("unit_type")
        uid = unit.get("unit_id")

        # =====================================================
        # PAGE UNITS
        # =====================================================
        if utype == "page":
            for page_idx, page in enumerate(unit.get("pages", [])):
                p_indices = page.get("paragraph_indices", [])
                content = " ".join(paragraphs[i] for i in p_indices).strip()

                pages_out.append({
                    "uuid": _make_uuid("page", page_counter),
                    "type": "page",
                    "page_index": page_counter,
                    "title": _make_title(content),
                    "content": content,
                    "bullet_points": [
                        bp
                        for i in p_indices
                        for bp in bullet_lookup.get(i, [])
                    ],
                    "image_id": image_lookup.get((uid, page_idx)),
                })

                page_counter += 1

        # =====================================================
        # ENGAGE UNITS
        # =====================================================
        elif utype == "engage":
            # -----------------------------
            # Normalize intro
            # -----------------------------
            intro = unit.get("intro", {})
            intro_idx = intro.get("paragraph_index")

            if not isinstance(intro_idx, int):
                continue  # skip malformed engage safely

            intro_text = paragraphs[intro_idx]

            # -----------------------------
            # Normalize items
            # items -> pages -> paragraph_indices
            # -----------------------------
            items = []

            for item in unit.get("items", []):
                for page in item.get("pages", []):
                    for p_idx in page.get("paragraph_indices", []):
                        if not isinstance(p_idx, int):
                            continue

                        text = paragraphs[p_idx]
                        items.append({
                            "paragraph_index": p_idx,
                            "title": _make_title(text),
                            "content": text,
                            "button_label": engage_label_lookup.get(p_idx),
                        })

            pages_out.append({
                "uuid": _make_uuid("engage", page_counter),
                "type": "engage",
                "intro": {
                    "paragraph_index": intro_idx,
                    "title": _make_title(intro_text),
                    "content": intro_text,
                },
                "items": items,
            })

            page_counter += 1

        # =====================================================
        # ENGAGE2 UNITS
        # =====================================================
        elif utype == "engage2":
            p_indices = unit.get("paragraph_indices", [])

            # engage2 may legitimately have no steps
            if not p_indices:
                pages_out.append({
                    "uuid": _make_uuid("engage2", page_counter),
                    "type": "engage2",
                    "title": "",
                    "content": "",
                    "button_label": None,
                    "steps": [],
                })
                page_counter += 1
                continue

            combined_text = " ".join(paragraphs[i] for i in p_indices).strip()

            pages_out.append({
                "uuid": _make_uuid("engage2", page_counter),
                "type": "engage2",
                "title": _make_title(combined_text),
                "content": combined_text,
                "button_label": engage2_label_lookup.get(tuple(p_indices)),
                "steps": engage2_steps_lookup.get(p_indices[0], []),
            })

            page_counter += 1

    return {
        "header": header,
        "notes": notes,
        "pages": pages_out,
        "quiz": quiz_data.get("quiz", []),
    }


