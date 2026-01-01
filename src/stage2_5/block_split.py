from typing import List, Dict, Any


def split_panel_blocks(blocks: List[Dict[str, Any]], max_paragraphs: int = 2) -> List[List[Dict[str, Any]]]:
    """
    Deterministically split panel content into panel-groups.

    Rules:
    - Pure paragraph panels: chunk into groups of up to `max_paragraphs` paragraphs.
    - If a bullets block appears, it MUST stay with the immediately preceding paragraph.
      If the current group already has other content before that paragraph, we split so the
      "intro paragraph + bullets" becomes its own group.
    - Order preserved. Unknown blocks preserved.
    """

    # ✅ NEW RULE — pure paragraph panels split by paragraph
    if blocks and all(b.get("type") == "paragraph" for b in blocks):
        return [[b] for b in blocks]

    output: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    para_count = 0

    for block in blocks:
        btype = block.get("type")

        if btype == "paragraph":
            # If adding this paragraph would exceed max, start a new group
            if current and para_count >= max_paragraphs:
                output.append(current)
                current = []
                para_count = 0

            current.append(block)
            para_count += 1
            continue

        if btype == "bullets":
            # Ensure bullets stay with the immediately preceding paragraph.
            # If current has MORE than 1 paragraph, peel off the last paragraph into its own group.
            if current:
                # Find last paragraph in current
                last_para_idx = None
                for i in range(len(current) - 1, -1, -1):
                    if current[i].get("type") == "paragraph":
                        last_para_idx = i
                        break

                if last_para_idx is not None and last_para_idx > 0:
                    # Split: everything before last paragraph becomes a group
                    output.append(current[:last_para_idx])
                    # New current: last paragraph only (bullets will attach)
                    current = current[last_para_idx:]
                    # Recount paragraphs in current (should be 1)
                    para_count = sum(1 for b in current if b.get("type") == "paragraph")

            # Attach bullets to current (or create if empty)
            if not current:
                current = []
                para_count = 0
            current.append(block)
            continue

        # Safety fallback: preserve unknown blocks
        if not current:
            current = []
            para_count = 0
        current.append(block)

    if current:
        output.append(current)

    return output

def build_block_split_proposal(
    header: str,
    blocks: List[List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Build a deterministic BLOCK_SPLIT proposal with continued headers.
    """

    proposed_panels = []

    for i, group in enumerate(blocks):
        proposed_panels.append({
            "header": header if i == 0 else f"{header} (continued)",
            "content": group,
        })

    return {
        "action": "split",
        "reason": "Deterministic block split (max paragraphs per panel).",
        "proposed_panels": proposed_panels,
    }

