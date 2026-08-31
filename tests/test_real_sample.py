import sys
import time
from pathlib import Path

# Add project root to sys.path so direct script execution works
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SentenceMetadata
from src.offline.file_reader import build_file_registry
from src.offline.trie_builder import build_suffix_trie
from src.utils import get_original_sentence, normalize_text


def test_build_trie_on_5_real_texts_1000_lines():
    archive_path = Path("Archive")
    assert archive_path.exists(), "Archive directory does not exist"

    all_files = build_file_registry(archive_path)
    assert len(all_files) >= 5, f"Expected at least 5 files in Archive, found {len(all_files)}"

    # Select the first 5 text files
    sample_registry = all_files[:5]
    print(f"\nTesting with 5 files (1,000 lines each):")
    for i, file_path in enumerate(sample_registry):
        print(f"  [{i}] {file_path.name}")

    # 1. Read up to 1,000 lines per file
    start_read = time.time()
    records = []
    for file_id, file_path in enumerate(sample_registry):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                if line_number >= 1000:
                    break
                if raw_line.strip():
                    records.append((file_id, line_number, raw_line))

    read_time = time.time() - start_read
    print(f"\nSuccessfully read {len(records)} lines in {read_time:.3f}s")

    # 2. Build Suffix Trie
    start_trie = time.time()
    trie_root = build_suffix_trie(records)
    build_time = time.time() - start_trie
    print(f"Built Suffix Trie in {build_time:.3f}s")

    # 3. Verify Trie structure and root children
    assert len(trie_root.children) > 0
    print(f"Root branching factor (unique starting characters): {len(trie_root.children)}")

    # 4. Verify suffix retrieval for a real sentence from file 0
    file_id, line_number, raw_line = records[0]
    metadata = SentenceMetadata(file_id=file_id, line_number=line_number)

    # Check original sentence retrieval
    original = get_original_sentence(metadata, sample_registry)
    assert original == raw_line.rstrip("\r\n")

    # Check that the first character of normalized line exists in Trie
    norm = normalize_text(raw_line)
    if norm:
        first_char = norm[0]
        assert first_char in trie_root.children

    print(f"Sample retrieved raw line: '{original[:60]}...'")
    print(f"Normalized line: '{norm[:60]}...'")
    print(f"Verification succeeded! (Total time: {read_time + build_time:.3f}s)\n")


if __name__ == "__main__":
    test_build_trie_on_5_real_texts_1000_lines()
