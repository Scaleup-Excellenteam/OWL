from dataclasses import dataclass
from enum import Enum


class CorrectionType(Enum):
    """Types of spelling corrections allowed during search."""
    REPLACEMENT = "replacement"
    INSERTION = "insertion"
    DELETION = "deletion"


@dataclass
class Correction:
    """Records a single spelling correction made during search."""
    correction_type: CorrectionType
    position: int  # 1-based index in the typed prefix
