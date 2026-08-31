from pathlib import Path
from src.offline.initializer import initialize_system
from src.online.completion import get_best_k_completions


def prepare_sample_archive(archive_path: Path, sample_dir: Path, num_files: int = 5) -> None:
    """Prepares sample archive with the first num_files in their entirety."""
    sample_dir.mkdir(parents=True, exist_ok=True)
    source_files = sorted([p for p in archive_path.rglob("*.txt") if p.is_file()])[:num_files]
    
    # Remove files in sample_dir that are not in source_files
    source_names = {f.name for f in source_files}
    for existing in sample_dir.glob("*.txt"):
        if existing.name not in source_names:
            try:
                existing.unlink()
            except Exception:
                pass

    for f in source_files:
        target = sample_dir / f.name
        if not target.exists():
            import shutil
            shutil.copy2(f, target)


def run_sample_program():
    archive_path = Path("Archive")
    sample_archive = Path("SampleArchive")
    cache_path = Path("sample_trie_cache.pkl")
    
    # Ensure 5 full files are prepared
    if archive_path.exists():
        prepare_sample_archive(archive_path, sample_archive, num_files=5)
    
    print("============================================================")
    print("🚀 LAUNCHING SAMPLE AUTO-COMPLETE CLI (5 Full Files - ~270k Lines)")
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
                print(f"  {i+1}. {suggestion.completed_sentence} ({suggestion.source_text}:{int(suggestion.offset)+1}, score={suggestion.score})")
        print()


if __name__ == "__main__":
    run_sample_program()
