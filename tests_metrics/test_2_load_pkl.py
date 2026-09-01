import time
from pathlib import Path
from src.offline.initializer import initialize_system

def run_test_2():
    archive_dir = Path("Archive")
    cache_path = Path("trie_cache.pkl")
    
    if not cache_path.exists():
        print("Error: trie_cache.pkl not found! You must run the main app or Test 1 to generate it first.")
        return

    print("============================================================")
    print("🚀 TEST 2: LOAD TRIE FROM EXISTING .PKL FILE")
    print("============================================================")
    print(f"Loading '{cache_path}' into memory...")
    
    start_time = time.time()
    
    # This triggers the unpickling process
    initialize_system(archive_dir, cache_path=cache_path)
    
    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n✅ Loading Complete!")
    print(f"Total time to unpickle and load Trie into RAM: {total_time:.4f} seconds")
    print("============================================================\n")

if __name__ == "__main__":
    run_test_2()
