# HEN search-test insights

HEN's search suite is coupled to its own `autocomplete` package, so its files
cannot run directly against OWL. Its behavioral checks are still applicable.

The portable checks now run through OWL's public `SearchService` in regular
mode and compare the returned completions to OWL's independent bounded-corpus
oracle. They cover exact matching, one-character replacement/deletion/
insertion, normalization of case/punctuation/whitespace, and empty-equivalent
queries.

This keeps the test independent of HEN implementation details while guarding
the user-facing facade: regular searches must remain untranslated and preserve
the engine's complete ranked results.

## Run result (2026-09-01)

`tests/system/test_hen_search_contract.py` produced 3 passing and 5 failing
cases. The empty-query contracts pass. Exact matching, the three one-character
edit cases, and normalization disagree with the independent oracle.

The same disagreement occurs in the pre-existing direct completion-oracle
suite (`tests/system/test_bounded_corpus.py`): 7 of 26 tests fail, including
the same Base64 and normalized-query scenarios. The fault is therefore below
`SearchService`, in the core completion/search behavior rather than the new
facade test.

Observed symptoms include missing valid inside-word matches and selecting a
different tied result from the oracle. The adapted test intentionally remains
failing so that this existing regression is visible through the user-facing
regular-search path.
