import pytest
from pathlib import Path
from src.models import SentenceMetadata
from src.offline.initializer import initialize_system


def test_initialize_system_build_and_cache(tmp_path: Path):
    # Setup archive directory
    archive_dir = tmp_path / "Archive"
    archive_dir.mkdir()

    file1 = archive_dir / "file1.txt"
    file1.write_text("Hello World\nAnother line", encoding="utf-8")

    cache_file = tmp_path / "test_trie_cache.pkl"

    assert not cache_file.exists()

    # 1. First initialization: builds from scratch and writes cache
    trie_root, registry = initialize_system(archive_dir, cache_path=cache_file)

    assert len(registry) == 1
    assert cache_file.exists()

    # Verify trie contains suffixes from "hello world"
    assert "h" in trie_root.children
    assert "w" in trie_root.children

    # 2. Second initialization: loads from cache
    trie_loaded, registry_loaded = initialize_system(archive_dir, cache_path=cache_file)

    assert len(registry_loaded) == 1
    assert "h" in trie_loaded.children
    assert "w" in trie_loaded.children
