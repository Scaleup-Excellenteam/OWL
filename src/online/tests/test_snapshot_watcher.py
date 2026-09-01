"""Tests for the online snapshot watcher that hot-swaps the active snapshot."""

import time
from pathlib import Path

import pytest

from src.models import TrieNode
from src.offline.snapshot_store import build_snapshot
from src.online.completion import configure_completion, get_best_k_completions
from src.online.snapshot_watcher import SnapshotWatcher, start_snapshot_service


@pytest.fixture(autouse=True)
def _reset_completion_state():
    """Leave global completion state clean between tests in this module."""
    yield
    configure_completion(TrieNode(), [])


def _make_archive(tmp_path: Path, name: str, text: str) -> Path:
    """Create a one-file archive directory for a test corpus.

    Args:
        tmp_path: Temporary directory supplied by pytest.
        name: Directory name to create under ``tmp_path``.
        text: Contents written to the single ``corpus.txt`` source file.

    Returns:
        The created archive directory.
    """
    archive_dir = tmp_path / name
    archive_dir.mkdir()
    (archive_dir / "corpus.txt").write_text(text, encoding="utf-8")
    return archive_dir


def test_poll_once_returns_false_when_no_snapshot_published_yet(tmp_path: Path):
    watcher = SnapshotWatcher(tmp_path / "snapshots")
    assert watcher.poll_once() is False


def test_poll_once_loads_and_configures_the_published_snapshot(tmp_path: Path):
    archive_dir = _make_archive(tmp_path, "Archive", "Hello world\n")
    snapshots_root = tmp_path / "snapshots"
    build_snapshot(archive_dir, snapshots_root)

    watcher = SnapshotWatcher(snapshots_root)
    swapped = watcher.poll_once()

    assert swapped is True
    assert get_best_k_completions("hello")


def test_poll_once_is_a_noop_when_the_pointer_has_not_moved(tmp_path: Path):
    archive_dir = _make_archive(tmp_path, "Archive", "Hello world\n")
    snapshots_root = tmp_path / "snapshots"
    build_snapshot(archive_dir, snapshots_root)

    watcher = SnapshotWatcher(snapshots_root)
    assert watcher.poll_once() is True
    assert watcher.poll_once() is False


def test_old_snapshot_keeps_serving_until_the_watcher_polls_the_new_one(
    tmp_path: Path,
):
    archive_dir = _make_archive(tmp_path, "Archive", "Alpha sentence\n")
    snapshots_root = tmp_path / "snapshots"
    build_snapshot(archive_dir, snapshots_root)

    watcher = SnapshotWatcher(snapshots_root)
    watcher.poll_once()

    # In-flight query still sees the first snapshot's data.
    assert get_best_k_completions("alpha")

    (archive_dir / "more.txt").write_text("Bravo sentence\n", encoding="utf-8")
    build_snapshot(archive_dir, snapshots_root)

    # The running service keeps answering from the old snapshot -- it has not
    # been told about the new one yet, so there is no downtime window.
    assert not get_best_k_completions("bravo")

    assert watcher.poll_once() is True
    assert get_best_k_completions("bravo")


def test_start_polls_in_a_background_thread_until_stopped(tmp_path: Path):
    archive_dir = _make_archive(tmp_path, "Archive", "Alpha sentence\n")
    snapshots_root = tmp_path / "snapshots"
    build_snapshot(archive_dir, snapshots_root)

    watcher = SnapshotWatcher(snapshots_root, poll_interval=0.05)
    watcher.start()
    try:
        deadline = time.time() + 2
        while time.time() < deadline and not get_best_k_completions("alpha"):
            time.sleep(0.02)
        assert get_best_k_completions("alpha")
    finally:
        watcher.stop()

    assert not watcher.is_running()


def test_start_snapshot_service_builds_an_initial_snapshot_when_none_exists(
    tmp_path: Path,
):
    archive_dir = _make_archive(tmp_path, "Archive", "Alpha sentence\n")
    snapshots_root = tmp_path / "snapshots"

    watcher = start_snapshot_service(archive_dir, snapshots_root, poll_interval=0.05)
    try:
        assert get_best_k_completions("alpha")
    finally:
        watcher.stop()
