from __future__ import annotations
from typing import Dict, Any, List, Tuple


# (block_id, block_type, original, suggested, notes, analysis)
Row = Tuple[str, str, str, str, str, str]


def _format_analysis(block: Dict[str, Any]) -> str:
    """
    Format clinical/editorial analysis (if present) into readable text.
    Expected shape:
      analysis = {
        "flags": [...],
        "notes": "..."
      }
    """
    analysis = block.get("analysis")
    if not isinstance(analysis, dict):
        return ""

    flags = analysis.get("flags") or []
    notes = analysis.get("notes") or ""

    parts: List[str] = []

    if isinstance(flags, list) and flags:
        parts.append("FLAGS:")
        for f in flags:
            if isinstance(f, str) and f.strip():
                parts.append(f"• {f.strip()}")

    if isinstance(notes, str) and notes.strip():
        if parts:
            parts.append("")
        parts.append(f"NOTES: {notes.strip()}")

    return "\n".join(parts).strip()


def slide_to_rows(slide: Dict[str, Any]) -> List[Row]:
    rows: List[Row] = []

    for block in slide.get("blocks", []):
        block_id = block.get("block_id", "—")
        block_type = block.get("type", "—")

        original = block.get("original") or "—"
        suggested = block.get("suggested") or "No change suggested."
        notes = block.get("notes") or ""
        analysis_text = _format_analysis(block)

        # -------------------------------------------------
        # Intro → Engage Items bridge (review-only)
        # -------------------------------------------------
        if block_type == "intro_bridge":
            rows.append((
                block_id,
                "Intro → Items Bridge (Optional)",
                "— (Did not exist in original)",
                suggested,
                notes or "Optional sentence to bridge the intro and engage items.",
                analysis_text,
            ))
            continue

        # -------------------------------------------------
        # Standard review row
        # -------------------------------------------------
        rows.append((
            block_id,
            block_type,
            original,
            suggested,
            notes,
            analysis_text,
        ))

    return rows

