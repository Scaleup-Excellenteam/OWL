from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Global file registry mapping file_id to file Path
file_registry: list[Path] = []


@dataclass
class AutoCompleteData:
    completed_sentence: str
    source_text: str
    offset: int
    score: int


@dataclass(frozen=True)
class SentenceMetadata:
    file_id: int
    line_number: int  # 0-based offset


class TrieNode:
    def __init__(self, char: str = ""):
        self.char: str = char
        self.children: dict[str, 'TrieNode'] = {}
        self.sentence_refs: set[SentenceMetadata] = set()


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
