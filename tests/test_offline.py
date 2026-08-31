"""Unit tests for offline initialization and trie construction."""

from src.models import SentenceMetadata, TrieNode
from src.offline.trie_builder import (
    build_suffix_trie,
    insert_sentence,
    insert_suffix,
)


def _find_node(root: TrieNode, text: str) -> TrieNode | None:
    node = root
    for char in text:
        node = node.children.get(char)
        if node is None:
            return None
    return node


def test_sentence_metadata_can_be_stored_in_a_set():
    metadata = create_metadata(2, line_number=7)

    assert {metadata} == {create_metadata(2, line_number=7)}


def test_insert_suffix_creates_nodes_and_sentence_references():
    root = TrieNode()
    metadata = create_metadata(0, line_number=3)

    insert_suffix(root, "demo", metadata)

    node = root
    for char in "demo":
        node = node.children[char]
        assert node.char == char
        assert metadata in node.sentence_refs


def test_insert_suffix_reuses_an_existing_path():
    root = TrieNode()
    first = create_metadata(0, line_number=0)
    second = create_metadata(1, line_number=4)

    insert_suffix(root, "same", first)
    original_s_node = root.children["s"]
    insert_suffix(root, "sample", second)

    assert root.children["s"] is original_s_node
    assert root.children["s"].sentence_refs == {first, second}


def test_insert_sentence_normalizes_and_inserts_every_suffix():
    root = TrieNode()
    metadata = create_metadata(0, line_number=1)

    insert_sentence(root, "Hello,  World!", metadata)

    full_sentence = _find_node(root, "hello world")
    middle_suffix = _find_node(root, "lo world")
    final_suffix = _find_node(root, "world")

    assert full_sentence is not None
    assert middle_suffix is not None
    assert final_suffix is not None
    assert metadata in full_sentence.sentence_refs
    assert metadata in middle_suffix.sentence_refs
    assert metadata in final_suffix.sentence_refs


def test_insert_sentence_ignores_empty_normalized_text():
    root = TrieNode()

    insert_sentence(root, "... !!!", create_metadata(0, line_number=0))

    assert root.children == {}


def test_build_suffix_trie_uses_file_and_line_metadata():
    records = [
        (0, 0, "Alpha sentence"),
        (1, 5, "Beta sentence"),
    ]

    root = build_suffix_trie(records)

    alpha_node = _find_node(root, "alpha")
    beta_node = _find_node(root, "beta")
    shared_node = _find_node(root, "sentence")

    assert alpha_node is not None
    assert beta_node is not None
    assert shared_node is not None
    assert alpha_node.sentence_refs == {create_metadata(0, 0)}
    assert beta_node.sentence_refs == {create_metadata(1, 5)}
    assert shared_node.sentence_refs == {
        create_metadata(0, 0),
        create_metadata(1, 5),
    }
