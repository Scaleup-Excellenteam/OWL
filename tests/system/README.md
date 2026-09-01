# Autocomplete system tests

The bounded suite loads the committed `data/sample_trie_cache.pkl` and compares
the public `get_best_k_completions()` API with an independent scan of the copied
corpus. Normal test runs never rebuild the sample cache.

Run the bounded suite:

```bash
.venv/bin/python -m pytest tests/system/test_bounded_corpus.py
```

Only regenerate the sample cache after intentionally changing the manifest or
copied corpus:

```bash
.venv/bin/python -m tests.system.build_sample_cache
```

The full-cache suite is separate because it loads the existing 554 MB project
cache. It never builds, deletes, replaces, or modifies that cache.

Generate an ignored snapshot candidate and validation/latency report:

```bash
.venv/bin/python -m tests.system.review_full_cache
```

Review only the returned source lines, scores, paths, offsets, and ordering in
`data/full_cache_golden.candidate.json`. Copy an approved candidate to
`data/full_cache_golden.json`; normal tests never update the golden file.

Run the reviewed full-cache regression test explicitly:

```bash
.venv/bin/python -m pytest tests/system/test_full_cache.py -s
```
