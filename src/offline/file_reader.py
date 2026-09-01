from pathlib import Path
from typing import Generator
from src.models import SentenceMetadata, create_metadata
from src.utils import normalize_text


def build_file_registry(archive_path: Path) -> list[Path]:
    """
    Recursively scans the given archive path for all '.txt' files,
    sorts them deterministically, and returns the list of file paths.
    The index in this list corresponds to the unique `file_id`.
    """
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive directory not found: {archive_path}")

    # Recursively find all .txt files and sort for deterministic file_ids
    return sorted([p for p in archive_path.rglob("*.txt") if p.is_file()])


def read_archive_records(
    archive_path: Path, 
    registry: list[Path] | None = None
) -> Generator[tuple[int, int, str], None, None]:
    """
    Yields (file_id, line_number, raw_line) for all non-empty lines in the archive.
    Matches Developer 1's `SentenceRecord` format for direct ingestion into `build_suffix_trie()`.
    """
    if registry is None:
        target_registry = build_file_registry(archive_path)
    else:
        if not registry:
            registry.extend(build_file_registry(archive_path))
        target_registry = registry

    for file_id, file_path in enumerate(target_registry):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                if raw_line.strip():
                    yield file_id, line_number, raw_line


def read_archive_sentences(
    archive_path: Path, 
    registry: list[Path] | None = None
) -> Generator[tuple[str, SentenceMetadata], None, None]:
    """
    Memory-efficient generator that yields (normalized_sentence, SentenceMetadata(file_id, line_number))
    for all non-empty lines.
    """
    if registry is None:
        target_registry = build_file_registry(archive_path)
    else:
        if not registry:
            registry.extend(build_file_registry(archive_path))
        target_registry = registry

    for file_id, file_path in enumerate(target_registry):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f):
                normalized = normalize_text(raw_line)
                if normalized:
                    yield normalized, create_metadata(file_id, line_number)
