"""
Batch / Incremental Trie Builder CLI Tool.

Allows indexing files from Archive in manageable batches,
automatically tracking the file registry and merging new batches
into the master trie_cache.pkl.
"""

import os
import pickle
import sys
import time
from pathlib import Path
from multiprocessing import cpu_count
import concurrent.futures

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.models import SentenceMetadata, TrieNode, file_registry
from src.offline.file_reader import build_file_registry
from src.offline.trie_builder import build_suffix_trie, merge_tries

sys.setrecursionlimit(50000)
MASTER_CACHE_FILE = Path("trie_cache.pkl")


def _build_worker_record_chunk(chunk_id: int, records_chunk: list[tuple[int, int, str]]) -> Path:
    """Worker process: builds Trie from an evenly distributed slice of lines."""
    chunk_root = build_suffix_trie(records_chunk)
    temp_chunk_path = Path(f"_temp_trie_chunk_{chunk_id}.pkl")
    with open(temp_chunk_path, "wb") as f:
        pickle.dump(chunk_root, f, protocol=pickle.HIGHEST_PROTOCOL)

    return temp_chunk_path


def load_master_state(cache_path: Path = MASTER_CACHE_FILE) -> tuple[TrieNode, list[Path]]:
    """Loads existing master cache or returns an empty root and empty registry."""
    if cache_path.exists():
        try:
            print(f"📦 Loading existing master cache from '{cache_path}'...")
            start_load = time.time()
            import gc
            gc.disable()
            with open(cache_path, "rb") as f:
                root, reg = pickle.load(f)
            gc.enable()
            elapsed = time.time() - start_load
            size_mb = os.path.getsize(cache_path) / (1024 * 1024)
            print(f"✅ Loaded master cache ({len(reg)} files, {size_mb:.1f} MB) in {elapsed:.2f}s.\n")
            return root, reg
        except Exception as e:
            print(f"⚠️  Could not load existing cache ({e}). Starting fresh.")
    
    return TrieNode(), []


def save_master_state(root: TrieNode, registry: list[Path], cache_path: Path = MASTER_CACHE_FILE) -> None:
    """Saves master Trie and registry to disk."""
    print(f"\n💾 Saving master cache to '{cache_path}' ({len(registry)} total files)...")
    start_save = time.time()
    import gc
    gc.disable()
    with open(cache_path, "wb") as f:
        pickle.dump((root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)
    gc.enable()
    elapsed = time.time() - start_save
    size_mb = os.path.getsize(cache_path) / (1024 * 1024)
    print(f"✅ Cache saved in {elapsed:.2f}s (Size: {size_mb:.1f} MB).\n")


def build_incremental_batch(
    master_root: TrieNode,
    master_registry: list[Path],
    files_to_add: list[Path],
    cache_path: Path = MASTER_CACHE_FILE,
) -> tuple[TrieNode, list[Path]]:
    """
    Reads lines from batch files, distributes them evenly across ALL CPU cores,
    merges chunk Tries into master_root, and saves progress.
    """
    if not files_to_add:
        print("No new files to add.")
        return master_root, master_registry

    start_file_id = len(master_registry)
    print(f"📖 Reading lines from {len(files_to_add)} files...")
    
    # 1. Fast reading of all lines in this batch
    records: list[tuple[int, int, str]] = []
    for idx, file_path in enumerate(files_to_add):
        file_id = start_file_id + idx
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                if raw_line.strip():
                    records.append((file_id, line_number, raw_line))

    total_lines = len(records)
    num_cores = max(1, cpu_count())
    print(f"🔨 Total lines in batch: {total_lines:,} | Distributing across all {num_cores} CPU cores...")

    # 2. Partition lines evenly across all available cores
    chunk_size = max(1, (total_lines + num_cores - 1) // num_cores)
    chunks = [
        records[i:i + chunk_size]
        for i in range(0, total_lines, chunk_size)
    ]

    print(f"⚡ Launching {len(chunks)} parallel worker processes (~{chunk_size:,} lines each)...")
    start_build = time.time()

    # 3. Map Phase (Parallel Building on all cores)
    chunk_paths = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = {executor.submit(_build_worker_record_chunk, i, chunk): i for i, chunk in enumerate(chunks)}
        for future in concurrent.futures.as_completed(futures):
            chunk_paths.append(future.result())

    build_time = time.time() - start_build
    print(f"✅ All {len(chunks)} workers finished in {build_time:.2f}s!")

    # 4. Reduce Phase (Merge into Master Trie)
    print(f"🔄 Merging {len(chunk_paths)} chunk tries into master tree...")
    start_merge = time.time()
    for chunk_path in chunk_paths:
        with open(chunk_path, "rb") as f:
            chunk_root = pickle.load(f)
        merge_tries(master_root, chunk_root)
        try:
            chunk_path.unlink()
        except Exception:
            pass

    merge_time = time.time() - start_merge
    print(f"✅ Merged in {merge_time:.2f}s.")

    # 5. Update Registry & Persist to Disk
    master_registry.extend(files_to_add)
    save_master_state(master_root, master_registry, cache_path=cache_path)

    return master_root, master_registry


def interactive_builder():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print(f"❌ Error: Archive directory '{archive_dir}' not found.")
        return

    print("=" * 65)
    print("🚀 BATCH & INCREMENTAL TRIE BUILDER")
    print("=" * 65)

    # 1. Scan Archive & Load Master Cache
    all_archive_files = build_file_registry(archive_dir)
    total_archive_count = len(all_archive_files)
    
    master_root, master_registry = load_master_state()
    
    # Identify which files are already indexed (by matching relative paths/filenames)
    indexed_names = {p.name for p in master_registry}
    unindexed_files = [p for p in all_archive_files if p.name not in indexed_names]
    
    print(f"📊 Archive Status:")
    print(f"   • Total files in Archive:    {total_archive_count}")
    print(f"   • Already indexed in Trie:   {len(master_registry)}")
    print(f"   • Remaining to be indexed:   {len(unindexed_files)}")
    print("=" * 65)

    if not unindexed_files:
        print("🎉 All files in the Archive are already indexed in your master cache!")
        return

    # 2. Interactive Loop
    while unindexed_files:
        print(f"\nRemaining unindexed files: {len(unindexed_files)}")
        user_choice = input(f"Enter number of new files to add (1-{len(unindexed_files)}, 'all', or 'q' to quit): ").strip().lower()

        if user_choice in ("q", "quit", "exit"):
            print("Exiting builder. Master cache is safely saved!")
            break

        if user_choice == "all":
            count = len(unindexed_files)
        else:
            try:
                count = int(user_choice)
                if count <= 0:
                    print("Please enter a positive number.")
                    continue
                count = min(count, len(unindexed_files))
            except ValueError:
                print("Invalid input. Enter a number, 'all', or 'q'.")
                continue

        # Select next batch
        batch = unindexed_files[:count]
        unindexed_files = unindexed_files[count:]

        # Build and merge
        master_root, master_registry = build_incremental_batch(
            master_root=master_root,
            master_registry=master_registry,
            files_to_add=batch,
            cache_path=MASTER_CACHE_FILE,
        )

        print(f"✨ Progress: {len(master_registry)} / {total_archive_count} files indexed ({(len(master_registry)/total_archive_count)*100:.1f}% complete)!")

    print("\n" + "=" * 65)
    print(f"🏁 DONE! Master Trie now contains {len(master_registry)} files in '{MASTER_CACHE_FILE}'.")
    print("=" * 65)


if __name__ == "__main__":
    interactive_builder()
