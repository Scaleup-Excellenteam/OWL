import pickle
import sys
from pathlib import Path
from multiprocessing import cpu_count
import concurrent.futures

from src.models import TrieNode, file_registry
from src.offline.file_reader import build_file_registry
from src.offline.trie_builder import build_suffix_trie, merge_tries

# Ensure deep Trie structures can be pickled without hitting Python's default 1000 limit
sys.setrecursionlimit(50000)

DEFAULT_CACHE_FILE = Path("trie_cache.pkl")


def _build_worker(chunk_id: int, chunk_files: list[tuple[int, Path]]) -> Path:
    """Worker function to build a partial Trie and save it to disk."""
    records = []
    for file_id, file_path in chunk_files:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                if raw_line.strip():
                    records.append((file_id, line_number, raw_line))
    
    trie_root = build_suffix_trie(records)
    chunk_path = Path(f"trie_chunk_{chunk_id}.pkl")
    
    with open(chunk_path, "wb") as f:
        pickle.dump(trie_root, f, protocol=pickle.HIGHEST_PROTOCOL)
        
    return chunk_path


from src.online.completion import configure_completion


def initialize_system(
    archive_path: Path, 
    cache_path: Path = DEFAULT_CACHE_FILE
) -> tuple[TrieNode, list[Path]]:
    if cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                trie_root, loaded_registry = pickle.load(f)
                file_registry.clear()
                file_registry.extend(loaded_registry)
                configure_completion(trie_root, file_registry)
                return trie_root, file_registry
        except (EOFError, pickle.UnpicklingError, Exception):
            print(f"Warning: Corrupt or incomplete cache at {cache_path}. Rebuilding from scratch...")
            try:
                cache_path.unlink()
            except Exception:
                pass

    # Registry does not exist, build it from scratch
    registry = build_file_registry(archive_path)
    file_registry.clear()
    file_registry.extend(registry)
    
    if not registry:
        master_root = TrieNode()
        with open(cache_path, "wb") as f:
            pickle.dump((master_root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)
        return master_root, file_registry
    
    # Map-Reduce setup
    num_cores = max(1, cpu_count())
    
    # Chunk the registry
    registry_with_ids = list(enumerate(registry))
    chunk_size = max(1, len(registry_with_ids) // num_cores)
    # Ensure chunk_size is at least 1, and don't create more chunks than needed
    chunks = [
        registry_with_ids[i:i + chunk_size] 
        for i in range(0, len(registry_with_ids), chunk_size)
    ]
    # Sometimes integer division creates one extra tiny chunk, that's fine.
    
    print(f"Distributing Trie build across {len(chunks)} workers...")
    
    master_root = TrieNode()
    
    # 1. Map Phase
    chunk_paths = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = {executor.submit(_build_worker, i, chunk): i for i, chunk in enumerate(chunks)}
        for future in concurrent.futures.as_completed(futures):
            chunk_paths.append(future.result())
            
    # 2. Reduce Phase
    print(f"Merging {len(chunk_paths)} chunk tries...")
    for chunk_path in chunk_paths:
        with open(chunk_path, "rb") as f:
            chunk_root = pickle.load(f)
        merge_tries(master_root, chunk_root)
        chunk_path.unlink() # Delete temp file

    # Save to disk via pickle
    print("Saving master cache...")
    with open(cache_path, "wb") as f:
        pickle.dump((master_root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)

    configure_completion(master_root, file_registry)
    return master_root, file_registry
