import time
import os
from pathlib import Path
from src.offline.initializer import initialize_system

def run_test_1():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("Error: Archive directory not found.")
        return

    # We use a dummy cache file so the engine is forced to build the Trie from scratch
    # instead of loading the existing trie_cache.pkl
    dummy_cache = Path("test_1_dummy_cache.pkl")
    if dummy_cache.exists():
        dummy_cache.unlink()

    print("============================================================")
    print("🚀 TEST 1: GENERATE TRIE FROM ARCHIVE (FROM SCRATCH)")
    print("============================================================")
    print(f"Scanning '{archive_dir}' and building in-memory Trie...")
    
    start_time = time.time()
    
    # This triggers the Map-Reduce Trie generation
    trie_root, registry = initialize_system(archive_dir, cache_path=dummy_cache)
    
    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n✅ Trie Generation Complete!")
    print(f"Total time to parse all files and build Trie: {total_time:.4f} seconds")
    print(f"Total files processed: {len(registry)}")
    print("============================================================\n")

    # Clean up the dummy cache file we just created so we don't waste disk space
    if dummy_cache.exists():
        dummy_cache.unlink()

if __name__ == "__main__":
    run_test_1()
