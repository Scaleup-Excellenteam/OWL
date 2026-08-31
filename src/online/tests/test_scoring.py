"""Tests for the scoring module."""

import pytest

from src.online.models.correction import Correction, CorrectionType
from src.online.scoring import calculate_score


def test_exact_match():
    """Test exact match scoring (no correction)."""
    # "To be" -> length 5 (normalized)
    assert calculate_score(5, None) == 10

    # "or Not" -> length 6
    assert calculate_score(6, None) == 12

    # "be, that" -> length 7 (normalized, assuming punctuation stripped)
    assert calculate_score(7, None) == 14


def test_replacement_scoring():
    """Test replacement penalty logic."""
    # "2o be" -> length 5, replace at pos 1 (index 0)
    correction = Correction(correction_type=CorrectionType.REPLACEMENT, position=1)
    assert calculate_score(5, correction) == 3  # 2 * 4 - 5 = 3

    # "to pe" -> length 5, replace at pos 4 (index 3)
    correction = Correction(correction_type=CorrectionType.REPLACEMENT, position=4)
    assert calculate_score(5, correction) == 6  # 2 * 4 - 2 = 6

    # Test all replacement penalty positions for prefix of length 5
    # Pos 1: 2*4 - 5 = 3
    assert calculate_score(5, Correction(CorrectionType.REPLACEMENT, 1)) == 3
    # Pos 2: 2*4 - 4 = 4
    assert calculate_score(5, Correction(CorrectionType.REPLACEMENT, 2)) == 4
    # Pos 3: 2*4 - 3 = 5
    assert calculate_score(5, Correction(CorrectionType.REPLACEMENT, 3)) == 5
    # Pos 4: 2*4 - 2 = 6
    assert calculate_score(5, Correction(CorrectionType.REPLACEMENT, 4)) == 6
    # Pos 5+: 2*4 - 1 = 7
    assert calculate_score(5, Correction(CorrectionType.REPLACEMENT, 5)) == 7


def test_deletion_scoring():
    """Test deletion (extra character in typed query) penalty logic."""
    # "or knot" -> length 7, delete extra k at pos 4 (index 3)
    correction = Correction(correction_type=CorrectionType.DELETION, position=4)
    assert calculate_score(7, correction) == 8  # 2 * 6 - 4 = 8

    # Test all deletion penalty positions for prefix of length 6
    # Pos 1: 2*5 - 10 = 0
    assert calculate_score(6, Correction(CorrectionType.DELETION, 1)) == 0
    # Pos 2: 2*5 - 8 = 2
    assert calculate_score(6, Correction(CorrectionType.DELETION, 2)) == 2
    # Pos 3: 2*5 - 6 = 4
    assert calculate_score(6, Correction(CorrectionType.DELETION, 3)) == 4
    # Pos 4: 2*5 - 4 = 6
    assert calculate_score(6, Correction(CorrectionType.DELETION, 4)) == 6
    # Pos 5+: 2*5 - 2 = 8
    assert calculate_score(6, Correction(CorrectionType.DELETION, 5)) == 8


def test_insertion_scoring():
    """Test insertion (missing character in typed query) penalty logic."""
    # "or nt" -> length 5, insert missing o at pos 5 (index 4)
    correction = Correction(correction_type=CorrectionType.INSERTION, position=5)
    assert calculate_score(5, correction) == 8  # 2 * 5 - 2 = 8

    # Test all insertion penalty positions for prefix of length 5
    # Pos 1: 2*5 - 10 = 0
    assert calculate_score(5, Correction(CorrectionType.INSERTION, 1)) == 0
    # Pos 2: 2*5 - 8 = 2
    assert calculate_score(5, Correction(CorrectionType.INSERTION, 2)) == 2
    # Pos 3: 2*5 - 6 = 4
    assert calculate_score(5, Correction(CorrectionType.INSERTION, 3)) == 4
    # Pos 4: 2*5 - 4 = 6
    assert calculate_score(5, Correction(CorrectionType.INSERTION, 4)) == 6
    # Pos 5+: 2*5 - 2 = 8
    assert calculate_score(5, Correction(CorrectionType.INSERTION, 5)) == 8
