from pathlib import Path
from typing import Generator, Sequence
from src.models import SentenceMetadata
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
    files = sorted([p for p in archive_path.rglob("*.txt") if p.is_file()])
    return files


def read_archive_sentences(
    archive_path: Path, 
    registry: list[Path] | None = None
) -> Generator[tuple[str, SentenceMetadata], None, None]:
    """
    Memory-efficient generator that:
    1. Populates the registry if not already provided.
    2. Reads files line-by-line using utf-8 (with error fallback).
    3. Normalizes each line.
    4. Yields (normalized_sentence, SentenceMetadata(file_id, line_number)) for non-empty lines.

    Note: `line_number` is the original 0-based line index in the raw file,
    ensuring that `get_original_sentence()` can retrieve the exact un-normalized string.
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
                # Skip empty lines, but line_number stays accurate for original file offset
                if normalized:
                    yield normalized, SentenceMetadata(file_id=file_id, line_number=line_number)
