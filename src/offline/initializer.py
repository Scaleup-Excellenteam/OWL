import pickle
from pathlib import Path
from src.models import TrieNode, file_registry
from src.offline.file_reader import build_file_registry, read_archive_records
from src.offline.trie_builder import build_suffix_trie

DEFAULT_CACHE_FILE = Path("trie_cache.pkl")


def initialize_system(
    archive_path: Path, 
    cache_path: Path = DEFAULT_CACHE_FILE
) -> tuple[TrieNode, list[Path]]:
    """
    Initializes the search engine state:
    1. Checks if `cache_path` exists.
    2. If it exists: loads and returns (trie_root, file_registry) from the pickle cache.
    3. If it does NOT exist:
       - Builds `file_registry` by scanning `archive_path`.
       - Reads archive records and constructs the Suffix Trie using `build_suffix_trie()`.
       - Persists (trie_root, file_registry) to `cache_path` using pickle.
       - Returns (trie_root, file_registry).
    """
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            trie_root, loaded_registry = pickle.load(f)
            # Update global file_registry if necessary
            file_registry.clear()
            file_registry.extend(loaded_registry)
            return trie_root, file_registry

    # Registry does not exist, build it from scratch
    registry = build_file_registry(archive_path)
    file_registry.clear()
    file_registry.extend(registry)

    # Stream records directly into Developer 1's build_suffix_trie
    records = read_archive_records(archive_path, registry=registry)
    trie_root = build_suffix_trie(records)

    # Save to disk via pickle
    with open(cache_path, "wb") as f:
        pickle.dump((trie_root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)

    return trie_root, file_registry
