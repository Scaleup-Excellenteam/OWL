import time
from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions, _file_registry
from src.utils import normalize_text

def run_test_5():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("Error: Archive directory not found.")
        return

    print("Loading system...")
    initialize_system(archive_dir)

    print("\n============================================================")
    print("🚀 TEST 5: SEARCH 50 LONG QUERIES")
    print("============================================================")
    
    # Deterministically select 50 long lines to use as queries
    queries = []
    
    # Bypass the registry and just walk the Archive folder directly!
    for file_path in archive_dir.rglob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = normalize_text(line)
                    # Find lines that are decently long
                    if len(line) > 25:
                        # Use a long prefix (20 chars) to ensure blazing fast lookup
                        queries.append(line[:20])
                        if len(queries) >= 50:
                            break
        except Exception:
            continue
            
        if len(queries) >= 50:
            break
                
    if not queries:
        print("Error: Could not find enough long text lines to query.")
        return
        
    print(f"Executing search for {len(queries)} long text queries...")
    
    start_test = time.time()
    total_results = 0
    
    for query in queries:
        results = get_best_k_completions(query)
        total_results += len(results)
        
    end_test = time.time()
    
    total_time = end_test - start_test
    avg_time_ms = (total_time / len(queries)) * 1000

    print(f"\n✅ Searches Complete!")
    print(f"Total Matches Found    : {total_results}")
    print(f"Total Execution Time   : {total_time:.4f} seconds")
    print(f"Average Time per Query : {avg_time_ms:.4f} milliseconds")
    print("============================================================\n")

if __name__ == "__main__":
    run_test_5()
