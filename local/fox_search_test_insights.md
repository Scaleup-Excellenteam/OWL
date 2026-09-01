# FOX search-test insights

FOX's linked `main` branch is empty, but its `feature/search-core` branch
contains relevant search-mechanism tests. The portable subset runs OWL's public
completion API over a real OWL suffix trie.

The selected checks require the search to retain the highest-scoring legal
alignment when multiple one-edit alignments exist, including substitution,
extra-character, and missing-character ambiguity. They also cover a normalized
official scoring example and rejection of a two-edit query.

## Run result (2026-09-01)

The selected FOX-derived contracts produced 5 passing and 1 failing case.
OWL preserves the best substitution and missing-character alignments, the
normalization example, and two-edit rejection. It fails the best
extra-character-alignment case: querying `xabcdef` against
`abcdef and xabcde` returns score 2, although the later `xabcde` alignment
requires only deletion of the final query character and should score 10.
