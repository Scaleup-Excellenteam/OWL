# Phase A: Online/Offline Contract & Architecture

## Overview
This document defines the contract and division of labor between the Offline (Initialization) and Online (Completion) phases for Phase A of the Auto-Complete Sentences project.

## Division of Labor

### 🧑‍💻 Developer 1: Offline / Initialization (Data Pipeline & Trie Building)
**Responsibilities:**
- File system traversal (reading all files from the dataset).
- Data normalization (lowercase, stripping punctuation, collapsing spaces).
- Constructing the **Suffix Trie**.
- Persisting (using Python's `pickle`) the data structures to disk so it doesn't need to be rebuilt every time.

### 🧑‍💻 Developer 2: Online / Completion (Search & Scoring Algorithms)
**Responsibilities:**
- Normalizing user input.
- Implementing the recursive fuzzy search algorithm (DFS) on the Suffix Trie with a 1-character error budget.
- Calculating the score based on the specific penalty rules.
- Retrieving the original sentences for the top 5 results from the file system.
- Sorting ties alphabetically if multiple results share the exact same score.

### 🧑‍💻 Developer 3: CLI & Offline Assistance
**Responsibilities:**
- Interactive Command Line Interface (CLI) loop.
- Formatting the output to exactly match the 2026 format: `1. <Sentence> (<Source>:<Offset>, score=<Score>)`.
- After completing the CLI and output formatting logic, transition to assist **Developer 1** with the offline initialization tasks (e.g., file reading, caching, or Trie insertion).

---

## Shared Data Models

Both developers will rely on the following shared data models to ensure memory efficiency.

```python
from dataclasses import dataclass
from pathlib import Path

# A global registry mapping a unique integer ID to a file path.
# Index is the file_id, value is the file_path.
# Example: [Path("Archive/tech/python.txt"), Path("Archive/science/space.txt")]
file_registry: list[Path] = []

@dataclass
class AutoCompleteData:
    completed_sentence: str
    source_text: str
    offset: int
    score: int
    # Additional methods can be added by Developer 2

@dataclass
class SentenceMetadata:
    file_id: int
    line_number: int  # 0-based offset

class TrieNode:
    def __init__(self, char: str = ""):
        # Store the character this node represents for easier debugging
        self.char: str = char
        # Maps a character to the next TrieNode
        self.children: dict[str, 'TrieNode'] = {}
        # Set of metadata for all sentences that share this suffix path
        self.sentence_refs: set[SentenceMetadata] = set()
```

---

## The Contract (API Handoff)

### 1. Initialization and Caching (The "Init if not initialized" flow)
To avoid rebuilding the Trie on every startup, we will use Python's `pickle` module to save the data. We need a shared initialization function that the CLI will call when the app starts.

```python
# Defined by Developer 1 (Offline)
def initialize_system(archive_path: Path) -> tuple['TrieNode', list[Path]]:
    """
    Checks if a cached version of the Trie exists (e.g., 'trie_cache.pkl').
    If it exists:
        Load the Trie and file_registry from disk and return them.
    If it does NOT exist:
        Parse the archive, build the Trie, populate file_registry, 
        save them to disk via pickle, and return them.
    """
    pass
```

### 2. Search Function
This is the core completion logic used by the CLI.

```python
# Defined by Developer 2 (Online)
def get_best_k_completions(prefix: str) -> list['AutoCompleteData']:
    """
    Takes the user's normalized prefix. 
    (Note: trie_root must be accessed via global state/singleton to match the required API signature).
    Performs the fuzzy search (handling max 1 mistake) and returns the top 5 completions,
    sorted alphabetically in case of a tied score.
    """
    pass
```

### 3. Shared Utility: Text Normalization
Both the file ingestion and the user input must be normalized identically.

```python
# Can be written by either developer
def normalize_text(text: str) -> str:
    """
    Converts to lowercase, removes punctuation, and collapses multiple spaces into one.
    """
    pass
```

### 4. Fetching the Original Sentence
Because we only store `file_id` and `line_number` in the Trie to save memory, the Online phase needs a way to fetch the original string for the final 5 matches to display to the user.

```python
# Can be written by either developer (likely Developer 2 during result formatting)
def get_original_sentence(metadata: SentenceMetadata, registry: list[Path]) -> str:
    """
    Given the metadata and the registry, opens the target file,
    reads the specific 0-based line, and returns the raw, un-normalized string.
    """
    pass
```

---

## Recommended Workflow for Parallel Development
- **Developer 1** can start immediately on file traversal, the normalization function, and the Trie insertion logic.
- **Developer 2** can manually create a small "Mock Trie" with 2 or 3 hardcoded sentences and start developing the fuzzy search DFS algorithm and the scoring logic against the mock data before the full ingestion pipeline is ready.
- **Developer 3** can immediately start building the CLI shell and output formatter using fake mock data. Once the UI works smoothly, they join Developer 1 to accelerate the offline initialization code.
