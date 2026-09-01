# Project Structure & Architecture

## Overview
This document describes the directory tree, modules, and organizational architecture for the OWL Auto-Complete engine.

---

## 📁 Directory Layout

```text
OWL/
├── Archive/                    # Dataset directory containing source text files (.txt)
│
├── planning/                   # Architecture, specs, and contract documentation
│   ├── phase_a_contract.md     # Core API contract & shared data models
│   ├── project_structure.md    # Repository layout and module descriptions
│   └── division_of_ownership.md# Team roles, responsibilities, and file ownership
│
├── src/                        # Main application source code
│   ├── __init__.py             # Package marker
│   ├── models.py               # Shared data structures (TrieNode, SentenceMetadata, AutoCompleteData, file_registry)
│   ├── utils.py                # Shared utilities (normalize_text, get_original_sentence)
│   │
│   ├── offline/                # Offline initialization & ingestion pipeline
│   │   ├── __init__.py         # Package marker
│   │   ├── file_reader.py      # Dataset traversal & raw file ingestion
│   │   ├── trie_builder.py     # Suffix generation & Trie construction
│   │   ├── initializer.py      # Cache management (pickle) & initialize_system() entrypoint
│   │   └── snapshot_store.py   # ZDT: versioned snapshots + atomic "current" pointer
│   │
│   └── online/                 # Online search & completion engine
│       ├── __init__.py         # Package marker
│       ├── search.py           # Fuzzy DFS traversal on Trie (1-character error budget)
│       ├── scoring.py          # Penalty deduction & score calculation
│       ├── completion.py       # get_best_k_completions() entrypoint
│       └── snapshot_watcher.py # ZDT: polls the pointer, hot-swaps the live snapshot
│
├── tests/                      # Automated test suite (pytest)
│   ├── __init__.py             # Package marker
│   ├── test_utils.py           # Unit tests for text normalization & sentence retrieval
│   ├── test_offline.py         # Unit tests for file reading, Trie construction & caching
│   └── test_online.py          # Unit tests for fuzzy search, scoring & completions
│
├── main.py                     # Interactive CLI entrypoint & formatted output
├── build_snapshot.py           # ZDT: builds & publishes a new versioned snapshot
├── .gitignore                  # Git ignore rules for virtual environments, caches, and pickle files
├── requirements.txt            # Project dependencies
└── README.md                   # Project summary and run instructions
```

---

## 📦 Module Descriptions

### `src/models.py`
Shared data definitions used across both offline and online phases:
* `file_registry: list[Path]`: Global mapping from `file_id` (integer index) to file `Path`.
* `AutoCompleteData`: Dataclass returned by search containing `completed_sentence`, `source_text`, `offset`, and `score`.
* `SentenceMetadata`: Compact representation storing `file_id` and `line_number`.
* `TrieNode`: Trie node representing characters, child nodes dictionary, and `sentence_refs` set.

### `src/utils.py`
Shared helper functions:
* `normalize_text(text: str) -> str`: Lowercases text, strips punctuation, and collapses multiple spaces.
* `get_original_sentence(metadata: SentenceMetadata, registry: list[Path]) -> str`: Reads the raw line from disk for top-k results.

### `src/offline/`
* `file_reader.py`: Recursively traverses the dataset directory and yields `(file_id, line_number, raw_line)`.
* `trie_builder.py`: Extracts all suffixes of normalized lines and inserts them into the Trie.
* `initializer.py`: Checks for existing `trie_cache.pkl`; loads if present or builds and persists if missing. Also exposes `build_trie_and_registry()`, the pure build step shared with `snapshot_store.py`.
* `snapshot_store.py` (ZDT): `build_snapshot()` builds a new Trie/registry into its own versioned `snapshots/<version>/` directory (never overwriting the currently-published one) and, only once the write has been validated by reading it back, atomically flips `snapshots/current` to it via write-then-`os.replace()`. `read_current_version()` / `load_snapshot()` are the read-side counterparts.

### `src/online/`
* `search.py`: Implements recursive DFS fuzzy search on `TrieNode` handling match, substitution, deletion, and insertion (max 1 mistake).
* `scoring.py`: Computes score based on match length and penalty rules for mistakes.
* `completion.py`: Coordinates search, score calculation, top-5 filtering, alphabetical tie-breaking, and raw sentence retrieval. `configure_completion()` is the single swap point that hot-loads a new Trie/registry into the running process.
* `snapshot_watcher.py` (ZDT): `SnapshotWatcher` polls `snapshot_store.read_current_version()` and, on change, loads the new snapshot and calls `configure_completion()` to swap it in -- in-flight and subsequent queries keep being served from the previous snapshot until that swap. `start_snapshot_service()` builds an initial snapshot if none exists yet and starts the watcher in a background thread.

### `main.py`
Provides an interactive command-line loop:
* Initializes the system via `initialize_system()` (legacy single-cache-file mode), or, when `OWL_SNAPSHOTS_DIR` is set, via `start_snapshot_service()` (ZDT mode -- see `README.md`).
* Prompts user for prefix input.
* Calls `get_best_k_completions()`.
* Formats results as `1. <Sentence> (<Source>:<Offset>, score=<Score>)`.

### `build_snapshot.py` (ZDT)
Root-level CLI, mirroring `build_trie.py`'s convention: builds and publishes one new versioned snapshot from an `Archive/`-shaped directory into a snapshot store, safe to run at any time against a store a live `main.py` process (in ZDT mode) is watching.
