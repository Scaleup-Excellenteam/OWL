import time
import random
from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions, _file_registry
from src.utils import normalize_text

def run_stress_test(num_queries=100):
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("Error: Archive directory not found.")
        return

    print("Loading system (Trie and Registry)...")
    start_load = time.time()
    trie, registry = initialize_system(archive_dir)
    print(f"System loaded in {time.time() - start_load:.2f} seconds.")

    print(f"\nGenerating {num_queries} realistic search queries...")
    queries = []
    
    files_to_sample = min(50, len(registry))
    sampled_files = random.sample(registry, files_to_sample)
    
    all_lines = []
    for file_path in sampled_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                all_lines.extend(f.readlines())
        except Exception:
            pass

    valid_lines = [normalize_text(line) for line in all_lines if len(normalize_text(line)) > 10]
    
    for _ in range(num_queries):
        line = random.choice(valid_lines)
        prefix_len = random.randint(5, min(35, len(line)))
        query = line[:prefix_len]
        
        if random.random() < 0.2 and len(query) > 5:
            typo_idx = random.randint(1, len(query) - 2)
            query = query[:typo_idx] + "x" + query[typo_idx + 1:]
            
        queries.append(query)

    print("\nStarting Stress Test...")
    start_test = time.time()
    
    total_results = 0
    
    for i, query in enumerate(queries):
        results = get_best_k_completions(query)
        total_results += len(results)

    end_test = time.time()
    total_time = end_test - start_test
    avg_time_ms = (total_time / num_queries) * 1000

    print("\n============================================================")
    print("🚀 STRESS TEST RESULTS")
    print("============================================================")
    print(f"Total Queries Executed : {num_queries}")
    print(f"Total Matches Found    : {total_results}")
    print(f"Total Execution Time   : {total_time:.4f} seconds")
    print(f"Average Time per Query : {avg_time_ms:.4f} milliseconds")
    print("============================================================\n")

if __name__ == "__main__":
    run_stress_test(100)
