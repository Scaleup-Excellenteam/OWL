import sys
from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run_program():
    archive_path = Path("Archive") 
    print("============================================================")
    print("🚀 AUTO-COMPLETE SEARCH ENGINE")
    print("============================================================")
    print("Loading the files and preparing the system...")
    initialize_system(archive_path)

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
            print("  (No matching suggestions found)")
        else:
            for i, suggestion in enumerate(top_5):
                # 1-based line offset for user-friendly display
                line_no = int(suggestion.offset) + 1
                print(f"  {i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{line_no}, score={suggestion.score})")
        print()


def main():
    run_program()


if __name__ == "__main__":
    main()