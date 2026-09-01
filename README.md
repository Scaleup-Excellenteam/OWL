# OWL Auto-Complete Search Engine

OWL builds an offline suffix Trie from an English text archive and uses it to
return the five highest-scoring sentence completions. It also offers an
optional multilingual mode powered by Google Cloud Translation.

## Requirements

- Python 3.10 or newer
- `pytest` for running tests
- An extracted `Archive/` directory for the complete application
- A Google Cloud Translation API key only for multilingual search

## Run the tests

```bash
python -m pytest -q
```

The Google Translation tests use fake responses and do not call Google or
consume API quota.

## Regular search

Place the text corpus under `Archive/`, then run:

```bash
python main.py
```

Choose `1` to use the original English autocomplete path. Regular search does
not require Google credentials or network access.

## Multilingual search with Google Cloud Translation

The feature uses Cloud Translation Basic v2 to translate a non-English user
query to English before passing it to the existing online Trie search. English
queries bypass Google and use the original search path unchanged, even when
multilingual mode is selected. The CLI shows the detected language and
translated query only when translation occurred; returned sentences, source
paths, offsets, and Phase A scores still come from the original archive.

For Hebrew input, multilingual mode also checks whether the text was intended
as English but typed with the Hebrew keyboard layout. For example, `פטאיםמ` is
converted to `python`, and `'ןמגם'` is converted to `window`. The correction is accepted only when the converted text
appears as a complete word or phrase in the Trie results; a substring such as
`akuo` inside `pakuo` is rejected. If both the keyboard correction and Google
translation produce results, the CLI asks the user which interpretation was
intended. This check reuses the existing Trie and does not add Offline data or
another cache.

1. Create or select a Google Cloud project.
2. Enable billing and the Cloud Translation API.
3. Create an API key and restrict it to the Cloud Translation API.
4. Export the key in the shell that runs OWL:

```bash
export GOOGLE_TRANSLATE_API_KEY='your-restricted-key'
python main.py
```

Choose `2` for multilingual search. Never commit the API key, a `.env` file,
or service-account credentials. If the key is missing, OWL clearly reports the
configuration problem and continues in regular mode. If Google is temporarily
unavailable, the current query is retained so the user can retry or reset it.
Only queries containing non-English letters while mode `2` is active are sent
to Google. English queries, archive sentences, and Trie data remain local.

## Query sessions

Input is cumulative: each new input is appended to the current query. In
multilingual mode the complete accumulated query is translated when it contains
non-English letters so Google receives the full linguistic context. Append `#`
to reset the query.

## Runtime logging

Regular execution keeps the interactive terminal output user-friendly while
writing operational events at `INFO` level or above to `logs/owl.log`:

```bash
python main.py
```

Enable detailed diagnostics in both the terminal and the log file with:

```bash
python main.py --debug
```

The local log rotates at 5 MB and retains three backups. Logs contain runtime
metadata such as durations, query lengths, result counts, and cache activity.
They do not contain API keys or full user queries. The entire `logs/` directory
is excluded from Git.

## Architecture

```text
CLI
  -> SearchService
      -> Hebrew keyboard-layout correction (multilingual mode only)
      -> GoogleTranslator (multilingual mode only)
      -> get_best_k_completions()
          -> Trie
```

The Google adapter and orchestration layer are separate from the Offline Trie
builder and the core Online search. This keeps regular search usable when the
external service is not configured or unavailable.
