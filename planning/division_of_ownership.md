# Division of Ownership & Responsibilities

## Overview
This document defines the roles, primary file ownership, and collaborative workflows among team members for Phase A.

---

## 👥 Developer Roles & Primary Responsibilities

### 🧑‍💻 Developer 1: Offline / Initialization Lead
* **Primary Scope**: Ingestion pipeline, Suffix Trie architecture, and Trie construction.
* **Core Tasks**:
  * Suffix extraction and insertion logic into the `TrieNode` graph.
  * Ensuring memory efficiency when building data structures.
  * Initializing and constructing the full dataset Trie.

---

### 🧑‍💻 Developer 2: Online / Search & Scoring Lead
* **Primary Scope**: Search algorithms, fuzzy matching, scoring penalties, and ranking.
* **Core Tasks**:
  * Recursive DFS fuzzy search on the Suffix Trie with a max 1-character mistake budget.
  * Implementing exact penalty deduction rules based on error type and character position.
  * Retrieving original sentences for the top 5 matches.
  * Deterministic alphabetical tie-breaking on identical scores.

---

### 🧑‍💻 Developer 3: CLI Lead & Offline Pipeline Assistant
* **Primary Scope**: Interactive CLI interface, output formatting, and offline pipeline assistance.
* **Core Tasks**:
  * Building the interactive CLI loop and matching output format `1. <Sentence> (<Source>:<Offset>, score=<Score>)`.
  * Implementing shared utilities (`normalize_text`, `get_original_sentence`).
  * Building dataset traversal and file ingestion (`file_reader.py`).
  * Implementing persistence / caching logic (`pickle` load/save inside `initializer.py`).

---

## 📋 File Ownership Matrix

| File / Component | Primary Owner | Secondary / Collaborator | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| `src/models.py` | **All Developers** | — | Shared data structures (`TrieNode`, `SentenceMetadata`, `AutoCompleteData`, `file_registry`). |
| `src/utils.py` | **Developer 3** | Developer 1 | `normalize_text()` and `get_original_sentence()`. |
| `src/offline/file_reader.py` | **Developer 3** | Developer 1 | Dataset file discovery (`rglob`), line reading, indexing files into `file_registry`. |
| `src/offline/trie_builder.py` | **Developer 1** | Developer 3 | Generating sentence suffixes and inserting into the Trie. |
| `src/offline/initializer.py` | **Developer 3** | Developer 1 | `initialize_system()`, cache check, `pickle` save and load workflow. |
| `src/online/search.py` | **Developer 2** | — | Fuzzy DFS traversal logic on `TrieNode`. |
| `src/online/scoring.py` | **Developer 2** | — | Penalty computation for letter substitutions, deletions, and insertions. |
| `src/online/completion.py` | **Developer 2** | — | Top-5 ranking, tie-breaking, and assembling `AutoCompleteData` list. |
| `main.py` | **Developer 3** | — | CLI interface loop and presentation formatting. |
| `tests/` | **All Developers** | — | Respective unit tests (`test_utils.py`, `test_offline.py`, `test_online.py`). |

---

## 🔄 Parallel Development Workflow

1. **Step 1 (Independent Foundations)**:
   * **Dev 3** implements `main.py` formatting and shared `src/utils.py`.
   * **Dev 1** builds `trie_builder.py` using mock sentences.
   * **Dev 2** builds fuzzy search DFS in `src/online/search.py` using a small mock Trie.
2. **Step 2 (Offline Acceleration)**:
   * **Dev 3** joins **Dev 1** to complete `src/offline/file_reader.py` and `src/offline/initializer.py` (caching).
3. **Step 3 (Integration & Testing)**:
   * Connect offline Trie output with online search engine.
   * Verify end-to-end performance and accuracy with `tests/`.
