from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions


def run_program():
    archive_path = Path("Archive") 
    trie, file_registry = initialize_system(archive_path)

    while True:
        user_input = input("The system is ready. Enter your text:\n")
        top_5 = get_best_k_completions(user_input)
        
        print("Here are the Top 5 suggestions:")
        for i, suggestion in enumerate(top_5):
            print(f"{i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{suggestion.offset}, score={suggestion.score})")


def main():
    run_program()


if __name__ == "__main__":
    main()