import time
from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions

def run_test():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("Error: Archive directory not found.")
        return

    print("Loading OWL System (Trie and Registry)...")
    start_load = time.time()
    initialize_system(archive_dir)
    print(f"System loaded in {time.time() - start_load:.2f} seconds.")

    query = "qwz"
    
    print(f"\nSearching for '{query}'...")
    
    # Run it a few times to get a stable average, since a single run can be noisy
    iterations = 5
    total_time = 0
    total_results = 0
    
    for i in range(iterations):
        start_test = time.time()
        results = get_best_k_completions(query, max_results=1)
        end_test = time.time()
        
        total_results = len(results)
        total_time += (end_test - start_test)
        
    avg_time_ms = (total_time / iterations) * 1000

    print("\n============================================================")
    print("🚀 'TO' QUERY BENCHMARK (OWL)")
    print("============================================================")
    print(f"Query executed         : '{query}'")
    print(f"Total Matches Found    : {total_results} (capped at 5)")
    print(f"Average Execution Time : {avg_time_ms:.4f} milliseconds (over {iterations} runs)")
    print("============================================================\n")

if __name__ == "__main__":
    run_test()
