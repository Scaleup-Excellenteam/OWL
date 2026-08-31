import pytest
from pathlib import Path
from src.models import SentenceMetadata
from src.utils import normalize_text, get_original_sentence


def test_normalize_text_basic():
    assert normalize_text("Hello World") == "hello world"


def test_normalize_text_punctuation():
    assert normalize_text("Hello, World! How are you?") == "hello world how are you"
    assert normalize_text("Don't worry... be happy!") == "don t worry be happy"


def test_normalize_text_whitespace_collapsing():
    assert normalize_text("   Lots   of    spaces   and\ttabs\n\nnewlines  ") == "lots of spaces and tabs newlines"


def test_normalize_text_empty_and_special():
    assert normalize_text("") == ""
    assert normalize_text("    ") == ""
    assert normalize_text("!@#$%^&*()_+-=[]{}|;':,.<>?/") == ""


def test_get_original_sentence(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("First raw line with, punctuation!\nSecond line\nThird line: End.", encoding="utf-8")
    
    registry = [sample_file]
    
    meta_0 = SentenceMetadata(file_id=0, line_number=0)
    meta_1 = SentenceMetadata(file_id=0, line_number=1)
    meta_2 = SentenceMetadata(file_id=0, line_number=2)
    
    assert get_original_sentence(meta_0, registry) == "First raw line with, punctuation!"
    assert get_original_sentence(meta_1, registry) == "Second line"
    assert get_original_sentence(meta_2, registry) == "Third line: End."


def test_get_original_sentence_invalid_registry():
    meta = SentenceMetadata(file_id=5, line_number=0)
    with pytest.raises(IndexError):
        get_original_sentence(meta, [])
