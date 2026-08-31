"""Build the suffix trie used by the online completion phase with high performance optimizations."""

from collections.abc import Iterable
from src.models import SentenceMetadata, TrieNode, create_metadata
from src.utils import normalize_text

SentenceRecord = tuple[int, int, str]
MAX_SUFFIX_LENGTH = 15
MAX_REFS_PER_NODE = 25


def insert_suffix(
    root: TrieNode,
    suffix: str,
    metadata: SentenceMetadata,
    max_refs: int = MAX_REFS_PER_NODE,
) -> None:
    """Insert one normalized suffix and associate its path with top sentence candidates."""
    node = root
    n = len(suffix)
    for i, char in enumerate(suffix):
        if node.children is None:
            node.children = {}
        
        children = node.children
        if char in children:
            node = children[char]
        else:
            new_node = TrieNode(char)
            children[char] = new_node
            node = new_node
        
        if i == n - 1:
            if node.sentence_refs is None:
                node.sentence_refs = []
            refs = node.sentence_refs
            if len(refs) < max_refs and metadata not in refs:
                refs.append(metadata)


def insert_sentence(
    root: TrieNode,
    sentence: str,
    metadata: SentenceMetadata,
    max_suffix_len: int = MAX_SUFFIX_LENGTH,
    max_refs: int = MAX_REFS_PER_NODE,
) -> None:
    """
    Normalize a sentence and insert suffixes starting at word boundaries.
    Caps depth to `max_suffix_len` and references per node to `max_refs`.
    """
    normalized_sentence = normalize_text(sentence)
    n = len(normalized_sentence)
    if not n:
        return

    for start_index in range(n):
        # Word-Boundary Optimization: only start suffix paths at the start of a word
        if start_index != 0 and normalized_sentence[start_index - 1] != " ":
            continue

        node = root
        limit = min(n, start_index + max_suffix_len)
        for i in range(start_index, limit):
            char = normalized_sentence[i]
            
            if node.children is None:
                node.children = {}
                
            children = node.children
            if char in children:
                node = children[char]
            else:
                new_node = TrieNode(char)
                children[char] = new_node
                node = new_node
            
            # Store metadata ONLY at the leaf of this suffix chunk
            if i == limit - 1:
                if node.sentence_refs is None:
                    node.sentence_refs = []
                refs = node.sentence_refs
                if len(refs) < max_refs and metadata not in refs:
                    refs.append(metadata)


def build_suffix_trie(
    records: Iterable[SentenceRecord],
    max_suffix_len: int = MAX_SUFFIX_LENGTH,
    max_refs: int = MAX_REFS_PER_NODE,
) -> TrieNode:
    """Build a suffix trie from ``(file_id, line_number, raw_line)`` records."""
    root = TrieNode()

    for file_id, line_number, raw_line in records:
        metadata = create_metadata(file_id, line_number)
        insert_sentence(root, raw_line, metadata, max_suffix_len=max_suffix_len, max_refs=max_refs)

    return root


def merge_tries(t1: TrieNode, t2: TrieNode, max_refs: int = MAX_REFS_PER_NODE) -> None:
    """
    Recursively merge t2 into t1.
    If a branch exists only in t2, the entire subtree is attached directly (O(1) operation).
    """
    if t2.children is None:
        return
        
    if t1.children is None:
        t1.children = {}
        
    for char, child2 in t2.children.items():
        if char in t1.children:
            child1 = t1.children[char]
            
            # Merge sentence_refs
            if child2.sentence_refs is not None:
                if child1.sentence_refs is None:
                    child1.sentence_refs = []
                refs1 = child1.sentence_refs
                for ref in child2.sentence_refs:
                    if len(refs1) < max_refs and ref not in refs1:
                        refs1.append(ref)
            
            # Recurse down overlapping branches
            merge_tries(child1, child2, max_refs)
        else:
            # Transfer branch pointer directly without recursion
            t1.children[char] = child2
