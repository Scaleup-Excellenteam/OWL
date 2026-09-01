# Universal Online Completion Test Instructions

## Purpose

The bounded system suite evaluates only the Phase A online completion behavior.
It does not grade directory traversal, trie construction, persistence, cache
format, or any other offline implementation choice.

Every team may prepare the bounded corpus using its own offline implementation.
Once prepared, the tests call the required online API and compare its complete
ordered result with an independent brute-force oracle.

## Universal Test Set

Run both bounded test modules:

```bash
.venv/bin/python -m pytest \
  tests/system/test_bounded_corpus.py \
  tests/system/test_bounded_edge_cases.py
```

The two files have complementary roles:

- `test_bounded_corpus.py` tests complete top-five ranking and determinism over
  realistic copied documentation lines. It includes high-fanout queries,
  duplicate sentences, normalization, every edit type, and matches in the
  middle of sentences and words.
- `test_bounded_edge_cases.py` contains controlled contract cases. It covers
  score penalty bands, query and sentence boundaries, short and empty input,
  normalization variants, fewer than five results, no results, duplicate
  occurrences, repeated-character ambiguity, competing occurrences within one
  sentence, result fields, and the scoring examples from the specification.

Both modules are part of the universal online suite. Do not run only the edge
case module when deciding whether an implementation is correct.

`test_full_cache.py` is explicitly excluded. It is a project-specific
regression and measurement test tied to one team's archive, serialized cache,
paths, and reviewed golden snapshot.

## Required Team Adapter

Implementations may use different modules, data structures, and initialization
flows. Before running the suite for another team, adapt only the wiring needed
to do the following:

1. Load that team's online system with the files listed in
   `tests/system/data/sample_manifest.json`.
2. Expose the required `get_best_k_completions(prefix)` call to both bounded
   test modules.
3. Convert returned values, if necessary, to the four required fields:
   `completed_sentence`, `source_text`, `offset`, and `score`.
4. Canonicalize source paths to the corresponding `Archive/<relative-path>`
   value used by the oracle.

The adapter must not alter scores, filter candidates, reorder results, or fill
in missing output values. Those behaviors belong to the implementation under
test.

The current project performs this wiring through `tests/system/conftest.py` and
`configure_completion()`. Other teams do not need to use those names or the
saved pickle format.

## Oracle Rules

`tests/system/oracle.py` is intentionally independent of production search,
normalization, and scoring code. Do not replace its calculations with calls to
the implementation under test.

For every corpus line, the oracle:

1. Normalizes the query and sentence.
2. Checks every possible substring start.
3. Considers exact matching and every valid single substitution, extra
   character, or missing character.
4. Keeps the highest score available for each physical sentence occurrence.
5. Sorts by descending score and then alphabetically, using source and offset
   only to make otherwise identical occurrences deterministic.
6. Returns at most five results.

Because matching may start anywhere, an apparent correction can have a better
interpretation. For example, removing the first or last character of a target
can leave an exact substring. The expected score is always the highest score
among all valid interpretations.

The appendix-example tests lock the oracle to the scores stated in the Part A
specification.

## Corpus and Cache Maintenance

The controlled source lines live in
`tests/system/data/corpus/online_contract_cases.txt`. The remaining bounded
files are copied documentation samples. The manifest and source hashes prevent
silent fixture drift.

Normal test runs must not rebuild or mutate the sample data. After an
intentional corpus or manifest change, this project regenerates its bounded
fixture with:

```bash
.venv/bin/python -m tests.system.build_sample_cache
```

Another team may use an equivalent preparation command appropriate to its own
storage format.

## Pass Criteria

An online implementation passes only when both bounded modules pass in full.
Determinism tests and fixture guards do not compensate for failed top-five
correctness cases. A returned result being individually valid is also
insufficient: the implementation must return the exact best ordered results and
must not omit a higher-ranked corpus occurrence.
