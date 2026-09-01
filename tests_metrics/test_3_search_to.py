import time
from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions

def run_test_3():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("Error: Archive directory not found.")
        return

    print("Loading system...")
    initialize_system(archive_dir)

    query = "To"
    
    print("\n============================================================")
    print("🚀 TEST 3: SEARCH FOR 'To'")
    print("============================================================")
    print(f"Executing exhaustive fuzzy search for '{query}'...")
    
    # Run it a few times to get a stable average
    iterations = 5
    total_time = 0
    total_results = 0
    
    for i in range(iterations):
        start_test = time.time()
        results = get_best_k_completions(query)
        end_test = time.time()
        
        total_results = len(results)
        total_time += (end_test - start_test)
        
    avg_time_ms = (total_time / iterations) * 1000

    print(f"\n✅ Search Complete!")
    print(f"Total Matches Displayed : {total_results} (capped at K=5)")
    print(f"Average Execution Time  : {avg_time_ms:.4f} milliseconds (over {iterations} runs)")
    print("============================================================\n")

if __name__ == "__main__":
    run_test_3()
