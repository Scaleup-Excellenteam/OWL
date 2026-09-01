# COD search-test insights

COD includes a focused search-mechanism suite. The portable subset exercises
OWL's public completion API with OWL's real suffix-trie builder and a compact
two-line corpus.

The selected checks cover the required one-edit mechanisms: replacement,
extra-character and missing-character handling, along with long queries whose
one error occurs near either end. The latter probes whether candidate selection
can retain a valid match when either the first or last query segment is damaged.

## Run result (2026-09-01)

All selected COD-derived checks pass: 6/6. OWL correctly found the intended
completion and assigned COD's expected score for every selected legal one-edit
case, including both long-query endpoint-error probes.
