# Peer search-test summary

## Results

| Peer repository | Passed | Tested | Result |
| --- | ---: | ---: | --- |
| HEN | 3 | 8 | 3/8 passed |
| COD | 6 | 6 | 6/6 passed |
| **Total** | **9** | **14** | **9/14 passed** |

## What the tests found

COD's selected search-mechanism tests pass. OWL correctly handles the checked
replacement, missing-character, and extra-character cases, including long
queries with the error near the beginning or the end.

HEN's oracle-backed tests expose a different core-search problem: for several
real-corpus queries, OWL does not return the independently correct top five.
The failures include valid inside-word matches being omitted and ties being
resolved to a different result than the oracle's deterministic ordering. The
same discrepancies occur when testing `get_best_k_completions()` directly, so
they are not caused by the `SearchService` multilingual/facade layer.

In short: the one-edit scoring mechanics covered by COD work on the compact
corpus, but the production completion engine has recall and/or ranking issues
on the broader saved corpus. HEN's exact, typo, and normalization cases make
those failures visible.
