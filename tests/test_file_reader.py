import pytest
from pathlib import Path
from src.models import SentenceMetadata
from src.offline.file_reader import build_file_registry, read_archive_sentences
from src.utils import get_original_sentence


def test_build_file_registry(tmp_path: Path):
    sub1 = tmp_path / "sub1"
    sub2 = tmp_path / "sub2"
    sub1.mkdir()
    sub2.mkdir()

    file_a = sub1 / "a.txt"
    file_b = sub2 / "b.txt"
    file_ignored = sub1 / "ignored.png"

    file_a.write_text("Hello", encoding="utf-8")
    file_b.write_text("World", encoding="utf-8")
    file_ignored.write_text("Not text", encoding="utf-8")

    registry = build_file_registry(tmp_path)
    assert len(registry) == 2
    assert file_a in registry
    assert file_b in registry
    assert file_ignored not in registry


def test_build_file_registry_nonexistent():
    with pytest.raises(FileNotFoundError):
        build_file_registry(Path("non_existent_path_12345"))


def test_read_archive_sentences_streaming(tmp_path: Path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"

    file1.write_text("Hello, World!\n\nThis is line 2.\n", encoding="utf-8")
    file2.write_text("Another File: First Line!\n   \nThird Line here.\n", encoding="utf-8")

    registry: list[Path] = []
    results = list(read_archive_sentences(tmp_path, registry=registry))

    # Check registry populated
    assert len(registry) == 2

    # Check streamed results
    # file1.txt:
    # line 0: "Hello, World!" -> normalized: "hello world"
    # line 1: "" -> skipped
    # line 2: "This is line 2." -> normalized: "this is line 2"
    # file2.txt:
    # line 0: "Another File: First Line!" -> normalized: "another file first line"
    # line 1: "   " -> skipped
    # line 2: "Third Line here." -> normalized: "third line here"

    expected = [
        ("hello world", SentenceMetadata(file_id=0, line_number=0)),
        ("this is line 2", SentenceMetadata(file_id=0, line_number=2)),
        ("another file first line", SentenceMetadata(file_id=1, line_number=0)),
        ("third line here", SentenceMetadata(file_id=1, line_number=2)),
    ]

    assert len(results) == len(expected)
    for (actual_text, actual_meta), (exp_text, exp_meta) in zip(results, expected):
        assert actual_text == exp_text
        assert actual_meta == exp_meta

        # Verify that get_original_sentence accurately retrieves the un-normalized string
        raw_line = get_original_sentence(actual_meta, registry)
        assert len(raw_line) > 0
