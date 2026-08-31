from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions


def run_sample_program():
    sample_archive = Path("SampleArchive")
    cache_path = Path("sample_trie_cache.pkl")
    
    print("============================================================")
    print("🚀 LAUNCHING SAMPLE AUTO-COMPLETE CLI")
    print("============================================================")
    print("Loading the files and preparing the system...")
    
    trie, file_registry = initialize_system(sample_archive, cache_path=cache_path)

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

        top_5 = get_best_k_completions(current_query)

        print(f"\nSuggestions for '{current_query}':")
        if not top_5:
            print("  (No suggestions yet - Developer 2 completion engine not deployed)")
        else:
            for i, suggestion in enumerate(top_5):
                print(f"  {i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{suggestion.offset}, score={suggestion.score})")
        print()


if __name__ == "__main__":
    run_sample_program()
