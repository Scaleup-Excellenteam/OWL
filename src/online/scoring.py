"""Score calculation and penalty rules for search matches."""

from src.online.models.correction import Correction, CorrectionType


def calculate_score(prefix_length: int, correction: Correction | None) -> int:
    """Calculates the score for a single search path based on the applied correction.

    Args:
        prefix_length: The length of the typed query string.
        correction: The correction applied to match the path, or None for an exact match.

    Returns:
        The calculated score based on matching characters and penalty rules.
    """
    if correction is None:
        return 2 * prefix_length

    # The position is 1-based, directly aligning with the penalty tables
    pos = correction.position

    if correction.correction_type == CorrectionType.REPLACEMENT:
        matching_characters = prefix_length - 1
        if pos == 1:
            penalty = 5
        elif pos == 2:
            penalty = 4
        elif pos == 3:
            penalty = 3
        elif pos == 4:
            penalty = 2
        else:
            penalty = 1
        return 2 * matching_characters - penalty

    elif correction.correction_type in (CorrectionType.INSERTION, CorrectionType.DELETION):
        if correction.correction_type == CorrectionType.DELETION:
            # Extra character in query, deleted to match trie
            matching_characters = prefix_length - 1
        else:
            # Missing character in query, inserted from trie
            matching_characters = prefix_length

        if pos == 1:
            penalty = 10
        elif pos == 2:
            penalty = 8
        elif pos == 3:
            penalty = 6
        elif pos == 4:
            penalty = 4
        else:
            penalty = 2
            
        return 2 * matching_characters - penalty

    return 0
