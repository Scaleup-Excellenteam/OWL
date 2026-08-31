import sys
import time
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.offline.initializer import initialize_system

def test_multiprocessing_build():
    archive_dir = Path("Archive")
    if not archive_dir.exists():
        print("[ERROR] Archive folder not found!")
        return
        
    print("=" * 60)
    print("MULTIPROCESSING MAP-REDUCE TEST")
    print("=" * 60)
    
    # We will test on a smaller sample (5 files, 1000 lines each) to compare speed fairly
    sample_dir = Path("SampleArchive")
    if not sample_dir.exists():
        sample_dir.mkdir()
        # copy exactly 5 files and truncate to 1000 lines
        files = list(archive_dir.rglob("*.txt"))[:5]
        for f in files:
            target_path = sample_dir / f.name
            with open(f, "r", encoding="utf-8", errors="replace") as fin, \
                 open(target_path, "w", encoding="utf-8") as fout:
                for i, line in enumerate(fin):
                    if i >= 1000:
                        break
                    fout.write(line)

    
    # Force rebuild
    test_cache = Path("test_mp_cache.pkl")
    if test_cache.exists():
        test_cache.unlink()
        
    start_time = time.time()
    print("Starting Map-Reduce initialize_system...")
    
    trie, registry = initialize_system(sample_dir, test_cache)
    
    elapsed = time.time() - start_time
    print(f"\n[SUCCESS] Completed initialize_system on SAMPLE ARCHIVE in {elapsed:.2f} seconds!")
    print(f"Registry size: {len(registry)} files")
    
    if test_cache.exists():
        test_cache.unlink()
    if sample_dir.exists():
        shutil.rmtree(sample_dir)

if __name__ == "__main__":
    test_multiprocessing_build()
