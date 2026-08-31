from dataclasses import dataclass
from pathlib import Path

# Global file registry mapping file_id to file Path
file_registry: list[Path] = []


@dataclass
class AutoCompleteData:
    completed_sentence: str
    source_text: str
    offset: int
    score: int


@dataclass
class SentenceMetadata:
    file_id: int
    line_number: int  # 0-based offset


class TrieNode:
    def __init__(self, char: str = ""):
        self.char: str = char
        self.children: dict[str, 'TrieNode'] = {}
        self.sentence_refs: set[SentenceMetadata] = set()
