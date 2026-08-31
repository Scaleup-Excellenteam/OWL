"""Build the suffix trie used by the online completion phase."""

from collections.abc import Iterable

from src.models import SentenceMetadata, TrieNode
from src.utils import normalize_text

SentenceRecord = tuple[int, int, str]


def insert_suffix(
    root: TrieNode,
    suffix: str,
    metadata: SentenceMetadata,
) -> None:
    """Insert one normalized suffix and associate its path with a sentence."""
    node = root

    for char in suffix:
        node = node.children.setdefault(char, TrieNode(char))
        node.sentence_refs.add(metadata)


def insert_sentence(
    root: TrieNode,
    sentence: str,
    metadata: SentenceMetadata,
) -> None:
    """Normalize a sentence and insert every non-empty character suffix."""
    normalized_sentence = normalize_text(sentence)

    for start_index in range(len(normalized_sentence)):
        insert_suffix(root, normalized_sentence[start_index:], metadata)


def build_suffix_trie(records: Iterable[SentenceRecord]) -> TrieNode:
    """Build a suffix trie from ``(file_id, line_number, raw_line)`` records."""
    root = TrieNode()

    for file_id, line_number, raw_line in records:
        metadata = SentenceMetadata(file_id=file_id, line_number=line_number)
        insert_sentence(root, raw_line, metadata)

    return root
