from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions


def run_program():
    archive_path = Path("Archive") 
    print("Loading the files and preparing the system...")
    trie, file_registry = initialize_system(archive_path)

    current_query = ""
    print("The system is ready. Enter your text:")

    while True:
        user_input = input(current_query) if current_query else input()

        # Check if the input triggers a session reset
        if user_input.endswith("#"):
            # Reset query state
            current_query = ""
            print("The system is ready. Enter your text:")
            continue

        current_query += user_input
        if not current_query.strip():
            continue

        top_5 = get_best_k_completions(current_query)

        print("Here are the Top 5 suggestions:")
        for i, suggestion in enumerate(top_5):
            print(f"{i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{suggestion.offset}, score={suggestion.score})")


def main():
    run_program()


if __name__ == "__main__":
    main()