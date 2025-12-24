from typing import List, Dict


def split_panel_blocks(content: List[str]) -> List[List[str]]:
    """
    Deterministically split panel content into independent blocks.

    Each block is a list of strings (paragraphs / bullets).
    Bullet lines stay attached to the preceding paragraph.
    """
    blocks: List[List[str]] = []
    current: List[str] = []

    for line in content:
        line = line.strip()
        if not line:
            continue

        # Bullet lines stay with previous paragraph
        if line.startswith(("•", "-", "*")):
            current.append(line)
            continue

        # New paragraph → start a new block
        if current:
            blocks.append(current)
            current = []

        current.append(line)

    if current:
        blocks.append(current)

    return blocks


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
