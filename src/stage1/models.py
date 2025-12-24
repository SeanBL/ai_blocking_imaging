from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RawBlock:
    header_line: str
    lines: List[str]

@dataclass
class ParsedBlock:
    header: str
    image_raw: Optional[str]
    english_text_raw: List[str]
    block_type_raw: Optional[str]
    notes_raw: Optional[str]