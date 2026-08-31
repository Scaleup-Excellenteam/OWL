from dataclasses import dataclass
from enum import Enum
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

    def __reduce__(self):
        # Fast C-level tuple serialization that bypasses Python reflection
        return (TrieNode, (self.char,), (self.children, self.sentence_refs))

    def __setstate__(self, state):
        self.children, self.sentence_refs = state


class CorrectionType(Enum):
    """Types of spelling corrections allowed during search."""
    REPLACEMENT = "replacement"
    INSERTION = "insertion"
    DELETION = "deletion"


@dataclass
class Correction:
    """Records a single spelling correction made during search."""
    correction_type: CorrectionType
    position: int  # 1-based index in the typed prefix


@dataclass
class SearchCursor:
    """Represents a paused DFS state in the Trie."""
    node: TrieNode
    budget: int
    correction: Correction | None
