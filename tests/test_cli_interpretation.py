"""CLI tests for choosing between ambiguous query interpretations."""

from main import choose_interpretation
from src.models import AutoCompleteData
from src.search_service import SearchAlternative, SearchResponse


def _option(query: str, description: str) -> SearchAlternative:
    return SearchAlternative(
        searched_query=query,
        description=description,
        detected_language=None,
        translated=description == "Google translation",
        keyboard_corrected=description == "keyboard correction",
        completions=[AutoCompleteData(query, "sample.txt", 0, 10)],
    )


def test_cli_asks_and_returns_the_selected_interpretation(monkeypatch, capsys):
    keyboard = _option("python", "keyboard correction")
    translation = _option("serpent", "Google translation")
    response = SearchResponse(
        original_query="פטאיםמ",
        searched_query="serpent",
        detected_language="he",
        translated=True,
        completions=translation.completions,
        alternatives=(keyboard, translation),
    )
    answers = iter(["invalid", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    selected = choose_interpretation(response)

    assert selected is translation
    output = capsys.readouterr().out
    assert "python (keyboard correction)" in output
    assert "serpent (Google translation)" in output
    assert "Please choose" in output


def test_cli_does_not_ask_when_query_is_unambiguous(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: (_ for _ in ()).throw(AssertionError("input was called")),
    )
    response = SearchResponse("שלום", "hello", "he", True, [])

    assert choose_interpretation(response) is None
