"""Poll the on-disk snapshot pointer and hot-swap the live completion state.

This is the online half of the zero-downtime hand-off: the offline side
(``src.offline.snapshot_store``) publishes new snapshot versions without
touching whichever one is currently active. ``SnapshotWatcher`` periodically
checks the ``current`` pointer and, only when it has actually moved, loads
the newly published snapshot and swaps it in via
``src.online.completion.configure_completion()``. In-flight requests keep
being answered from the previously configured snapshot right up until that
swap -- there is no restart and no window where completion is unconfigured.
"""

import threading
from pathlib import Path

from src.offline.snapshot_store import (
    DEFAULT_SNAPSHOTS_ROOT,
    build_snapshot,
    load_snapshot,
    read_current_version,
)
from src.online.completion import configure_completion

DEFAULT_POLL_INTERVAL_SECONDS = 2.0


class SnapshotWatcher:
    """Poll a snapshot store and keep the online completion state current."""

    def __init__(
        self,
        snapshots_root: Path = DEFAULT_SNAPSHOTS_ROOT,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        """Configure a watcher for one snapshot store.

        Args:
            snapshots_root: Directory holding versioned snapshots and the
                ``current`` pointer file.
            poll_interval: Seconds to wait between pointer checks once
                ``start()`` is running in the background.
        """
        self._snapshots_root = snapshots_root
        self._poll_interval = poll_interval
        self._current_version: str | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def current_version(self) -> str | None:
        """Return the version this watcher last swapped in.

        Returns:
            The active version id, or ``None`` before the first swap.
        """
        return self._current_version

    def poll_once(self) -> bool:
        """Check the pointer once and swap in a newly published snapshot.

        Returns:
            ``True`` if a new snapshot was loaded and swapped in, ``False``
            if the pointer is unset or unchanged since the last swap.
        """
        version = read_current_version(self._snapshots_root)
        if version is None or version == self._current_version:
            return False

        trie_root, registry = load_snapshot(self._snapshots_root, version)
        configure_completion(trie_root, registry)
        self._current_version = version
        return True

    def start(self) -> None:
        """Start polling for new snapshots in a background daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        def _run() -> None:
            while not self._stop_event.is_set():
                self.poll_once()
                self._stop_event.wait(self._poll_interval)

        self._thread = threading.Thread(
            target=_run, name="owl-snapshot-watcher", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the background polling thread and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 5)
            self._thread = None

    def is_running(self) -> bool:
        """Report whether the background polling thread is active.

        Returns:
            ``True`` while a thread started by ``start()`` is still alive.
        """
        return self._thread is not None and self._thread.is_alive()


def start_snapshot_service(
    archive_path: Path,
    snapshots_root: Path = DEFAULT_SNAPSHOTS_ROOT,
    *,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> SnapshotWatcher:
    """Bring up the online service against a snapshot store, live-reloadable.

    If no snapshot has ever been published to ``snapshots_root`` yet, builds
    one from ``archive_path`` first so the service has something to serve
    immediately. Either way, completion is configured with the current
    snapshot before this returns, and a background watcher is left running
    so that any later ``build_snapshot()`` call -- run from anywhere, at any
    time, without stopping this process -- gets picked up automatically.

    Args:
        archive_path: Directory containing the ``.txt`` source corpus, used
            only to build an initial snapshot when the store is empty.
        snapshots_root: Directory holding versioned snapshots and the
            ``current`` pointer file.
        poll_interval: Seconds to wait between pointer checks.

    Returns:
        The running ``SnapshotWatcher``; call ``stop()`` to shut it down.
    """
    if read_current_version(snapshots_root) is None:
        build_snapshot(archive_path, snapshots_root)

    watcher = SnapshotWatcher(snapshots_root, poll_interval=poll_interval)
    watcher.poll_once()
    watcher.start()
    return watcher
