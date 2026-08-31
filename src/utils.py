import itertools
from pathlib import Path
import string
from src.models import SentenceMetadata

# Precomputed fast C-level translation table for stripping punctuation
# Replaces all standard punctuation characters with a space
_PUNCT_TO_SPACE_TABLE = str.maketrans({char: " " for char in string.punctuation})


def normalize_text(text: str) -> str:
    """
    Highly optimized text normalizer:
    1. Converts text to lowercase.
    2. Replaces punctuation with whitespace using a precomputed C-level translate table.
    3. Collapses all consecutive whitespaces (spaces, tabs, newlines) into a single space
       and strips leading/trailing spaces via fast C-level `split()` and `' '.join()`.
    """
    if not text:
        return ""
    
    # 1. Lowercase & replace punctuation with space (executed in C)
    cleaned = text.lower().translate(_PUNCT_TO_SPACE_TABLE)
    
    # 2. `split()` without arguments splits on any whitespace and collapses multiple spaces,
    #    `' '.join(...)` produces a single space separated normalized string.
    return " ".join(cleaned.split())


def get_original_sentence(metadata: SentenceMetadata, registry: list[Path]) -> str:
    """
    Given the sentence metadata and file registry, opens the target file,
    lazily seeks to the specific 0-based line without loading the entire file into memory,
    and returns the raw un-normalized string (stripped of trailing newlines).
    """
    if metadata.file_id < 0 or metadata.file_id >= len(registry):
        raise IndexError(f"file_id {metadata.file_id} is out of bounds for registry of size {len(registry)}")

    file_path = registry[metadata.file_id]
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # itertools.islice consumes the iterator up to the requested line in C
        line = next(itertools.islice(f, metadata.line_number, metadata.line_number + 1), "")
        return line.rstrip("\r\n")
