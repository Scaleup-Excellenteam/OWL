from dataclasses import dataclass

from src.models import Correction


@dataclass
class SearchMatch:
    """Represents a successful path found during fuzzy search."""
    sentence_refs: set['SentenceMetadata']
    correction: Correction | None
