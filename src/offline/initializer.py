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


def _build_worker_record_chunk(chunk_id: int, records_chunk: list[tuple[int, int, str]]) -> Path:
    """Worker process: builds Trie from an evenly distributed slice of lines."""
    chunk_root = build_suffix_trie(records_chunk)
    temp_chunk_path = Path(f"trie_chunk_{chunk_id}.pkl")
    with open(temp_chunk_path, "wb") as f:
        pickle.dump(chunk_root, f, protocol=pickle.HIGHEST_PROTOCOL)
        
    return temp_chunk_path


from src.online.completion import configure_completion


def initialize_system(
    archive_path: Path, 
    cache_path: Path = DEFAULT_CACHE_FILE
) -> tuple[TrieNode, list[Path]]:
    if cache_path.exists():
        import time
        import gc
        print(f"Found master cache ({cache_path.stat().st_size / (1024*1024):.1f} MB). Unpickling... (This might take a minute for large tries)")
        start = time.time()
        gc.disable()
        with open(cache_path, "rb") as f:
            trie_root, loaded_registry = pickle.load(f)
        gc.enable()
        print(f"Unpickled in {time.time() - start:.2f}s!")
        
        file_registry.clear()
        file_registry.extend(loaded_registry)
        configure_completion(trie_root, file_registry)
        return trie_root, file_registry

    # Registry does not exist, build it from scratch
    registry = build_file_registry(archive_path)
    file_registry.clear()
    file_registry.extend(registry)
    
    if not registry:
        master_root = TrieNode()
        with open(cache_path, "wb") as f:
            pickle.dump((master_root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)
        return master_root, file_registry
    
    # Map-Reduce setup: strictly limit concurrency to prevent memory explosion
    num_cores = max(1, min(4, cpu_count() // 2))
    
    print(f"📖 Reading all lines from {len(registry)} files into memory...")
    records: list[tuple[int, int, str]] = []
    for file_id, file_path in enumerate(registry):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                if raw_line.strip():
                    records.append((file_id, line_number, raw_line))

    total_lines = len(records)
    print(f"🔨 Total lines: {total_lines:,} | Distributing across {num_cores} CPU cores...")
    
    master_root = TrieNode()
    
    if total_lines == 0:
        return master_root, file_registry

    # Partition lines evenly across all available cores
    chunk_size = max(1, (total_lines + num_cores - 1) // num_cores)
    chunks = [
        records[i:i + chunk_size]
        for i in range(0, total_lines, chunk_size)
    ]
    
    print(f"Distributing Trie build across {len(chunks)} workers...")
    
    # 1. Map Phase
    chunk_paths = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = {executor.submit(_build_worker_record_chunk, i, chunk): i for i, chunk in enumerate(chunks)}
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
