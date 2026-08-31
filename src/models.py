from dataclasses import dataclass
from pathlib import Path

# Global file registry mapping file_id to file Path
file_registry: list[Path] = []


@dataclass(slots=True)
class AutoCompleteData:
    completed_sentence: str
    source_text: str
    offset: int
    score: int


@dataclass(frozen=True, slots=True)
class SentenceMetadata:
    file_id: int
    line_number: int  # 0-based offset


class TrieNode:
    __slots__ = ("char", "children", "sentence_refs")

    def __init__(self, char: str = ""):
        self.char: str = char
        self.children: dict[str, "TrieNode"] = {}
        # Bounded list of top candidate references for maximum speed and minimal memory
        self.sentence_refs: list[SentenceMetadata] = []
