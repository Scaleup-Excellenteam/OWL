"""Versioned offline snapshots with an atomically-updated "current" pointer.

Zero-downtime hand-off: instead of overwriting the single active
``trie_cache.pkl`` in place (what ``initialize_system()`` still does for the
simple single-process CLI), an offline build here writes each new snapshot
into its own version directory under ``snapshots_root`` and only then flips a
small pointer file to name it "current". The pointer is updated by writing a
temp file and calling ``os.replace()``, so a reader can never observe a
half-written pointer, and a build that fails validation never becomes
current. The online side (``src.online.snapshot_watcher``) polls that
pointer and hot-swaps the running service onto the new snapshot.
"""

import os
import pickle
import time
import uuid
from pathlib import Path

from src.models import TrieNode
from src.offline.initializer import build_trie_and_registry

DEFAULT_SNAPSHOTS_ROOT = Path("snapshots")
SNAPSHOT_CACHE_FILENAME = "trie_cache.pkl"
POINTER_FILENAME = "current"


def _generate_version() -> str:
    """Return a new, time-ordered, collision-free snapshot version id.

    Returns:
        A version id combining a UTC timestamp with a short random suffix.
    """
    timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def read_current_version(snapshots_root: Path = DEFAULT_SNAPSHOTS_ROOT) -> str | None:
    """Read which snapshot version is currently marked active.

    Args:
        snapshots_root: Directory holding versioned snapshot subdirectories
            and the ``current`` pointer file.

    Returns:
        The active version id, or ``None`` if no snapshot has been published.
    """
    pointer_path = snapshots_root / POINTER_FILENAME
    if not pointer_path.exists():
        return None
    return pointer_path.read_text(encoding="utf-8").strip()


def load_snapshot(
    snapshots_root: Path, version: str
) -> tuple[TrieNode, list[Path]]:
    """Load one versioned snapshot's Trie and file registry from disk.

    Args:
        snapshots_root: Directory holding versioned snapshot subdirectories.
        version: Version id of the snapshot to load.

    Returns:
        The Trie root and file registry stored in that snapshot.
    """
    cache_path = snapshots_root / version / SNAPSHOT_CACHE_FILENAME
    with open(cache_path, "rb") as f:
        trie_root, registry = pickle.load(f)
    return trie_root, registry


def _write_pointer(snapshots_root: Path, version: str) -> None:
    """Atomically point ``current`` at ``version`` via write-then-rename.

    Args:
        snapshots_root: Directory holding the ``current`` pointer file.
        version: Version id to mark as current.
    """
    pointer_path = snapshots_root / POINTER_FILENAME
    tmp_path = snapshots_root / f".{POINTER_FILENAME}.{uuid.uuid4().hex[:8]}.tmp"
    tmp_path.write_text(version, encoding="utf-8")
    os.replace(tmp_path, pointer_path)


def build_snapshot(
    archive_path: Path,
    snapshots_root: Path = DEFAULT_SNAPSHOTS_ROOT,
    *,
    version: str | None = None,
) -> Path:
    """Build a new versioned snapshot from an archive and publish it.

    The snapshot is written to its own ``snapshots_root/<version>`` directory
    -- the currently-published snapshot, if any, is left untouched so that a
    service still serving it keeps working. Only once the new snapshot has
    been written and re-loaded successfully (a basic write validation) is the
    ``current`` pointer atomically moved to it.

    Args:
        archive_path: Directory containing the ``.txt`` source corpus.
        snapshots_root: Directory to hold versioned snapshot subdirectories
            and the ``current`` pointer file.
        version: Explicit version id to use instead of an auto-generated one.

    Returns:
        The path to the newly built snapshot's version directory.

    Raises:
        FileNotFoundError: If ``archive_path`` does not exist.
        Exception: If the newly written snapshot fails to reload; the
            ``current`` pointer is left untouched in that case.
    """
    version = version or _generate_version()
    snapshots_root.mkdir(parents=True, exist_ok=True)

    trie_root, registry = build_trie_and_registry(archive_path)

    snapshot_dir = snapshots_root / version
    snapshot_dir.mkdir(parents=True)
    cache_path = snapshot_dir / SNAPSHOT_CACHE_FILENAME
    with open(cache_path, "wb") as f:
        pickle.dump((trie_root, registry), f, protocol=pickle.HIGHEST_PROTOCOL)

    # Validate before publishing: a build that cannot be read back must never
    # become "current".
    load_snapshot(snapshots_root, version)

    _write_pointer(snapshots_root, version)
    return snapshot_dir
