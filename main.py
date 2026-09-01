import sys
from pathlib import Path

from src.google_features import (
    GoogleTranslator,
    TranslationConfigurationError,
    TranslationServiceError,
)
from src.offline.initializer import initialize_system
from src.search_service import SearchAlternative, SearchResponse, SearchService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


import os

def load_env():
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'\"")


def choose_multilingual_mode() -> bool:
    """Ask which search experience to use for the current CLI session."""
    print("Choose search mode:")
    print("  1. Regular English search")
    print("  2. Multilingual search (Google Translation)")
    return input("Mode [1]: ").strip() == "2"


def choose_interpretation(response: SearchResponse) -> SearchAlternative | None:
    """Ask only when keyboard correction and translation are both plausible."""
    if not response.alternatives:
        return None

    print("\nDid you mean:")
    for index, option in enumerate(response.alternatives, start=1):
        print(f"  {index}. {option.searched_query} ({option.description})")

    while True:
        choice = input("Choose an option: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(response.alternatives):
            return response.alternatives[int(choice) - 1]
        print("Please choose one of the listed options.")


def run_program():
    load_env()
    archive_path = Path("Archive")
    print("============================================================")
    print("🚀 AUTO-COMPLETE SEARCH ENGINE")
    print("============================================================")
    print("Loading the files and preparing the system...")
    initialize_system(archive_path)

    multilingual = choose_multilingual_mode()
    translator = None
    if multilingual:
        try:
            translator = GoogleTranslator.from_environment()
        except TranslationConfigurationError as exc:
            print(f"Multilingual search is unavailable: {exc}")
            print("Continuing in regular English search mode.\n")
            multilingual = False

    search_service = SearchService(translator)

    current_query = ""
    print("The system is ready. Enter your text (append '#' to reset):\n")

    while True:
        try:
            user_input = input(current_query) if current_query else input()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        # Check if the input triggers a session reset
        if user_input.endswith("#"):
            current_query = ""
            print("\n--- Resetting Query ---")
            print("The system is ready. Enter your text:\n")
            continue

        current_query += user_input
        if not current_query.strip():
            continue

        try:
            response = search_service.search(
                current_query,
                multilingual=multilingual,
            )
        except TranslationServiceError as exc:
            print(f"\nTranslation failed: {exc}")
            print("Retry, append '#' to reset, or restart in regular mode.\n")
            continue

        try:
            chosen = choose_interpretation(response)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break
        if chosen is None:
            searched_query = response.searched_query
            detected_language = response.detected_language
            translated = response.translated
            keyboard_corrected = response.keyboard_corrected
            completions = response.completions
        else:
            searched_query = chosen.searched_query
            detected_language = chosen.detected_language
            translated = chosen.translated
            keyboard_corrected = chosen.keyboard_corrected
            completions = chosen.completions

        if keyboard_corrected:
            print(
                f"\nKeyboard layout corrected: "
                f"'{current_query}' -> '{searched_query}'"
            )
        elif translated:
            language = detected_language or "unknown"
            print(f"\nDetected language: {language}")
            print(f"Searching in English for: '{searched_query}'")

        print(f"\nSuggestions for '{current_query}':")
        if not completions:
            print("  (No matching suggestions found)")
        else:
            for i, suggestion in enumerate(completions):
                # 1-based line offset for user-friendly display
                line_no = int(suggestion.offset) + 1
                print(f"  {i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{line_no}, score={suggestion.score})")
        print()


def main():
    run_program()


if __name__ == "__main__":
    main()
