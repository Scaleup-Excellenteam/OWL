"""Unit tests for versioned offline snapshots and the atomic current-pointer."""

import os
from pathlib import Path

import pytest

from src.models import TrieNode
from src.offline.snapshot_store import (
    build_snapshot,
    load_snapshot,
    read_current_version,
)


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


def test_read_current_version_returns_none_when_no_pointer_exists(tmp_path: Path):
    assert read_current_version(tmp_path / "snapshots") is None


def test_build_snapshot_writes_a_new_versioned_directory_and_updates_pointer(
    tmp_path: Path,
):
    archive_dir = _make_archive(tmp_path, "Archive", "Hello world\n")
    snapshots_root = tmp_path / "snapshots"

    snapshot_dir = build_snapshot(archive_dir, snapshots_root)

    assert snapshot_dir.parent == snapshots_root
    assert (snapshot_dir / "trie_cache.pkl").exists()

    version = read_current_version(snapshots_root)
    assert version == snapshot_dir.name

    trie_root, registry = load_snapshot(snapshots_root, version)
    assert isinstance(trie_root, TrieNode)
    assert len(registry) == 1


def test_build_snapshot_does_not_overwrite_previous_versions(tmp_path: Path):
    archive_dir = _make_archive(tmp_path, "Archive", "Hello world\n")
    snapshots_root = tmp_path / "snapshots"

    first_dir = build_snapshot(archive_dir, snapshots_root)
    first_version = read_current_version(snapshots_root)

    (archive_dir / "more.txt").write_text("Second source\n", encoding="utf-8")
    second_dir = build_snapshot(archive_dir, snapshots_root)
    second_version = read_current_version(snapshots_root)

    assert first_dir != second_dir
    assert second_version != first_version
    assert first_dir.exists()  # the old snapshot is left intact for in-flight readers

    _, old_registry = load_snapshot(snapshots_root, first_version)
    assert len(old_registry) == 1

    _, new_registry = load_snapshot(snapshots_root, second_version)
    assert len(new_registry) == 2


def test_build_snapshot_pointer_swap_is_write_then_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The pointer file must be updated via a temp file plus ``os.replace``."""
    archive_dir = _make_archive(tmp_path, "Archive", "Hello world\n")
    snapshots_root = tmp_path / "snapshots"

    seen = {}
    original_replace = os.replace

    def spy_replace(src, dst):
        seen["src"] = Path(src)
        seen["dst"] = Path(dst)
        return original_replace(src, dst)

    monkeypatch.setattr("src.offline.snapshot_store.os.replace", spy_replace)

    build_snapshot(archive_dir, snapshots_root)

    assert seen["dst"].name == "current"
    assert seen["src"] != seen["dst"]
    assert seen["src"].parent == seen["dst"].parent


def test_build_snapshot_raises_and_leaves_pointer_untouched_when_archive_missing(
    tmp_path: Path,
):
    snapshots_root = tmp_path / "snapshots"
    missing_archive = tmp_path / "does-not-exist"

    with pytest.raises(FileNotFoundError):
        build_snapshot(missing_archive, snapshots_root)

    assert read_current_version(snapshots_root) is None


def test_build_snapshot_does_not_flip_pointer_when_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A build that fails post-write validation must not become "current"."""
    archive_dir = _make_archive(tmp_path, "Archive", "Hello world\n")
    snapshots_root = tmp_path / "snapshots"

    # Establish a known-good current version first.
    build_snapshot(archive_dir, snapshots_root)
    good_version = read_current_version(snapshots_root)

    def broken_load_snapshot(_snapshots_root, _version):
        raise ValueError("simulated corrupt snapshot")

    monkeypatch.setattr(
        "src.offline.snapshot_store.load_snapshot", broken_load_snapshot
    )

    with pytest.raises(ValueError):
        build_snapshot(archive_dir, snapshots_root)

    assert read_current_version(snapshots_root) == good_version
