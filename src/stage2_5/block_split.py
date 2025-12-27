from typing import List, Dict


def split_panel_blocks(blocks: List[Dict]) -> List[List[Dict]]:
    """
    Deterministically split panel content.

    Rules:
    - Bullets are atomic and attach to the nearest preceding paragraph.
    - Panels are split ONLY when bullets are present.
    - Pure paragraph panels remain intact.
    """

    # Detect if this panel contains bullets at all
    has_bullets = any(b.get("type") == "bullets" for b in blocks)

    # If no bullets, do NOT split — keep as one panel
    if not has_bullets:
        return [blocks]

    output_blocks: List[List[Dict]] = []
    current: List[Dict] = []

    for block in blocks:
        btype = block.get("type")

        if btype == "bullets":
            current.append(block)
            continue

        if btype == "paragraph":
            if current:
                output_blocks.append(current)
                current = []

            current.append(block)
            continue

        # Safety fallback
        current.append(block)

    if current:
        output_blocks.append(current)

    return output_blocks


def build_block_split_proposal(header: str, blocks: List[List[str]]) -> Dict:
    """
    Build a deterministic BLOCK_SPLIT proposal with continued headers.
    """
    proposed_panels = []

    for i, block in enumerate(blocks):
        panel_header = header if i == 0 else f"{header} (continued)"
        proposed_panels.append({
            "header": panel_header,
            "content": block
        })

    return {
        "action": "split",
        "reason": "Multiple independent content blocks detected under a single header.",
        "proposed_panels": proposed_panels
    }
