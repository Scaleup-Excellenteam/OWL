"""Build mock online data backed by real temporary source files."""

from pathlib import Path
from typing import NamedTuple

from src.models import TrieNode
from src.utils import normalize_text


class MockSentenceMetadata(NamedTuple):
    """Hashable stand-in for the shared sentence metadata model."""

    file_id: int
    line_number: int


def _insert_sentence(
    root: TrieNode,
    sentence: str,
    metadata: MockSentenceMetadata,
) -> None:
    """Insert every normalized character suffix for one mock sentence.

    Args:
        root: Trie root to populate.
        sentence: Original sentence text.
        metadata: Location of the sentence in the mock registry.
    """
    normalized_sentence = normalize_text(sentence)
    for start_index in range(len(normalized_sentence)):
        node = root
        for char in normalized_sentence[start_index:]:
            node = node.children.setdefault(char, TrieNode(char))
            node.sentence_refs.add(metadata)


def build_mock_system(
    tmp_path: Path,
    sentences: list[str],
) -> tuple[TrieNode, list[Path]]:
    """Create a mock suffix trie and matching one-file registry.

    Args:
        tmp_path: Temporary directory supplied by pytest.
        sentences: Original sentence lines to index.

    Returns:
        The populated trie root and registry containing the mock source path.
    """
    source_path = tmp_path / "mock_source.txt"
    source_path.write_text("\n".join(sentences) + "\n", encoding="utf-8")

    root = TrieNode()
    for line_number, sentence in enumerate(sentences):
        _insert_sentence(
            root,
            sentence,
            MockSentenceMetadata(file_id=0, line_number=line_number),
        )

    return root, [source_path]
