"""Zero-Downtime Snapshot Builder CLI Tool.

Builds a new versioned snapshot from an Archive directory and, once it has
been written and validated, atomically flips the snapshot store's `current`
pointer to it. This is the offline half of ZDT: it never touches whichever
snapshot a running service is currently reading, so it is always safe to run
this against a live, unattended process -- locally or against a remote
archive/snapshot mount -- to add a new data source with zero downtime.

Usage:
    python build_snapshot.py [archive_dir] [snapshots_dir]

Defaults to `Archive/` and `snapshots/` in the current directory, matching
`build_trie.py`'s existing single-cache-file tool. A running `main.py`
process started with `OWL_SNAPSHOTS_DIR` set to the same `snapshots_dir`
picks up the new snapshot automatically, on its own, without a restart.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.offline.snapshot_store import DEFAULT_SNAPSHOTS_ROOT, build_snapshot


def main() -> None:
    archive_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Archive")
    snapshots_dir = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SNAPSHOTS_ROOT
    )

    print("=" * 65)
    print("🚀 ZERO-DOWNTIME SNAPSHOT BUILDER")
    print("=" * 65)
    print(f"📂 Archive:   {archive_dir}")
    print(f"📦 Snapshots: {snapshots_dir}")

    start = time.time()
    snapshot_dir = build_snapshot(archive_dir, snapshots_dir)
    elapsed = time.time() - start

    print(f"✅ Published '{snapshot_dir.name}' in {elapsed:.2f}s.")
    print(
        "   Any running service watching this snapshots directory will pick "
        "it up on its next poll -- no restart needed."
    )
    print("=" * 65)


if __name__ == "__main__":
    main()
