"""Peer-derived regular-search contracts exercised through ``SearchService``.

The cases originate from HEN's search-only suite, but use OWL's public facade
and independent bounded-corpus oracle instead of HEN implementation modules.
"""

from __future__ import annotations

import pytest

from src.search_service import SearchService
from tests.system.conftest import canonicalize_sample_results
from tests.system.oracle import CorpusLine, top_five


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("base64", id="exact-match"),
        pytest.param("baze64", id="one-character-replacement"),
        pytest.param("bse64", id="one-character-deletion"),
        pytest.param("basex64", id="one-character-insertion"),
        pytest.param("  THIS,   DOCUMENT!!! ", id="normalization"),
    ],
)
def test_regular_search_service_matches_independent_oracle(
    query: str,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Keep the user-facing regular-search path aligned with core ranking."""
    del configured_sample_system

    response = SearchService().search(query)

    assert response.original_query == query
    assert response.searched_query == query
    assert response.translated is False
    assert response.detected_language is None
    assert canonicalize_sample_results(response.completions) == top_five(
        query, bounded_corpus
    )


@pytest.mark.parametrize("query", ["", "   ", "!!! @#$ ..."])
def test_regular_search_service_rejects_empty_normalized_queries(
    query: str,
    configured_sample_system: object,
) -> None:
    """Empty-equivalent queries must not produce a completion through the facade."""
    del configured_sample_system

    response = SearchService().search(query)

    assert response.completions == []
    assert response.translated is False
