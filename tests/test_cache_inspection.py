import os
import pickle
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.models import SentenceMetadata, TrieNode
from src.offline.file_reader import build_file_registry
from src.offline.trie_builder import build_suffix_trie
from src.utils import get_original_sentence, normalize_text

SAMPLE_CACHE_FILE = Path("sample_trie_cache.pkl")


def quick_sample_trie_test():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("[ERROR] Archive folder not found!")
        return

    print("=" * 60)
    print("OPTIMIZED SAMPLE TRIE BENCHMARK & SEARCH TEST")
    print("=" * 60)

    # 1. Pick 5 text files
    all_files = build_file_registry(archive_dir)
    sample_registry = all_files[:5]
    print("Using 5 sample files:")
    for i, p in enumerate(sample_registry):
        print(f"   [{i}] {p.name}")

    # 2. Build the sample cache to benchmark optimizations
    if SAMPLE_CACHE_FILE.exists():
        SAMPLE_CACHE_FILE.unlink()
        
    print("\nBuilding Optimized Sample Trie from first 1000 lines of each file...")
    start_build = time.time()
    records = []
    for file_id, file_path in enumerate(sample_registry):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                if line_number >= 1000:
                    break
                if raw_line.strip():
                    records.append((file_id, line_number, raw_line))

    trie_root = build_suffix_trie(records)
    registry = sample_registry
    build_time = time.time() - start_build
    print(f"[SUCCESS] Built Optimized Trie on {len(records)} lines in {build_time:.3f}s!")

    # Save to sample_trie_cache.pkl
    start_save = time.time()
    with open(SAMPLE_CACHE_FILE, "wb") as f:
        pickle.dump((trie_root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)
    save_time = time.time() - start_save
    size_kb = os.path.getsize(SAMPLE_CACHE_FILE) / 1024
    print(f"[SAVED] Cache saved to {SAMPLE_CACHE_FILE} in {save_time:.3f}s (Size: {size_kb:.1f} KB)")

    # Measure load time
    start_load = time.time()
    with open(SAMPLE_CACHE_FILE, "rb") as f:
        _ = pickle.load(f)
    load_time = time.time() - start_load
    print(f"[LOADED] Cache loaded back into memory in {load_time:.4f}s")

    # 3. Test Lookups for words
    test_words = ["intel", "python", "the", "system"]
    print("\n" + "=" * 60)
    print("TESTING SEARCH LOOKUPS ON SAMPLE TRIE:")
    print("=" * 60)

    for word in test_words:
        norm_word = normalize_text(word)
        node = trie_root
        found = True
        for char in norm_word:
            if char in node.children:
                node = node.children[char]
            else:
                found = False
                break

        print(f"\nSearching for: '{word}' (normalized: '{norm_word}')")
        if found and node.sentence_refs:
            refs = list(node.sentence_refs)
            print(f"   [FOUND] {len(refs)} matches in Trie!")
            print(f"   Top 2 matching original sentences:")
            for i, meta in enumerate(refs[:2]):
                raw_sentence = get_original_sentence(meta, registry)
                file_name = registry[get_file_id(meta)].name
                clean_preview = raw_sentence.strip()[:80].encode("ascii", "replace").decode("ascii")
                print(f"     [{i+1}] ({file_name}:{get_line_number(meta)}) -> {clean_preview}")
        else:
            print(f"   [NOT FOUND] No matches found for '{word}'.")

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    quick_sample_trie_test()
