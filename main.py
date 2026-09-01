import sys
from pathlib import Path

from src.google_features import (
    GoogleTranslator,
    TranslationConfigurationError,
    TranslationServiceError,
)
from src.offline.initializer import initialize_system
from src.search_service import SearchService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def choose_multilingual_mode() -> bool:
    """Ask which search experience to use for the current CLI session."""
    print("Choose search mode:")
    print("  1. Regular English search")
    print("  2. Multilingual search (Google Translation)")
    return input("Mode [1]: ").strip() == "2"


def run_program():
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

        if multilingual:
            language = response.detected_language or "unknown"
            print(f"\nDetected language: {language}")
            print(f"Searching in English for: '{response.searched_query}'")

        print(f"\nSuggestions for '{current_query}':")
        if not response.completions:
            print("  (No matching suggestions found)")
        else:
            for i, suggestion in enumerate(response.completions):
                # 1-based line offset for user-friendly display
                line_no = int(suggestion.offset) + 1
                print(f"  {i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{line_no}, score={suggestion.score})")
        print()


def main():
    run_program()


if __name__ == "__main__":
    main()
