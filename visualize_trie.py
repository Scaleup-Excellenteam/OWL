"""
Trie Visualization Tool with Graphviz.

Visualizes the Suffix Trie hierarchy, character transitions,
and sentence metadata references as a Graphviz diagram.
"""

import os
import pickle
import subprocess
import sys
from pathlib import Path

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SentenceMetadata, TrieNode
from src.offline.trie_builder import build_suffix_trie
from src.utils import get_original_sentence


def export_trie_to_dot(
    root: TrieNode,
    output_dot_path: Path,
    registry: list[Path] | None = None,
    max_depth: int = 4,
    max_nodes: int = 80,
    filter_prefix: str | None = None,
) -> int:
    """
    Traverses the Trie and exports it to a Graphviz .dot file.
    
    Args:
        root: The root TrieNode.
        output_dot_path: Destination .dot file path.
        registry: Optional file registry to decode sentence previews.
        max_depth: Maximum depth to display from the starting node.
        max_nodes: Safety limit to prevent Graphviz from freezing on huge trees.
        filter_prefix: If specified, focuses the visualization starting from this prefix.
    """
    # If a prefix filter is provided, navigate down to that node
    start_node = root
    start_label = "ROOT"
    if filter_prefix:
        for char in filter_prefix.lower():
            if char in start_node.children:
                start_node = start_node.children[char]
            else:
                print(f"Prefix '{filter_prefix}' not found in Trie.")
                return 0
        start_label = f"Prefix: '{filter_prefix}'"

    lines = [
        "digraph Trie {",
        '    rankdir=TB;',
        '    node [shape=circle, fontname="Helvetica", fontsize=11, style=filled, fillcolor="#F8F9FA", color="#343A40"];',
        '    edge [fontname="Helvetica", fontsize=10, color="#6C757D", arrowsize=0.7];',
        "",
    ]

    node_counter = 0
    node_id_map: dict[int, str] = {}

    def get_node_id(node: TrieNode) -> str:
        nonlocal node_counter
        obj_id = id(node)
        if obj_id not in node_id_map:
            node_counter += 1
            node_id_map[obj_id] = f"node_{node_counter}"
        return node_id_map[obj_id]

    # Queue for BFS traversal: (node, depth, path_string)
    root_id = get_node_id(start_node)
    
    # Style start node
    lines.append(f'    {root_id} [label="{start_label}", shape=doublecircle, fillcolor="#4DABF7", fontcolor=white, penwidth=2];')

    queue = [(start_node, 0, filter_prefix or "")]
    visited_nodes = {id(start_node)}
    total_rendered = 1

    while queue and total_rendered < max_nodes:
        curr_node, depth, path_str = queue.pop(0)

        if depth >= max_depth:
            continue

        for char, child in sorted(curr_node.children.items()):
            if total_rendered >= max_nodes:
                break

            child_id = get_node_id(child)
            new_path = path_str + char

            if id(child) not in visited_nodes:
                visited_nodes.add(id(child))
                total_rendered += 1

                # Node formatting based on sentence references
                has_refs = bool(child.sentence_refs)
                num_refs = len(child.sentence_refs)
                
                # Safe display for spaces and characters
                display_char = f"␣ ({char})" if char == " " else char
                
                if has_refs:
                    # Highlight nodes with matches
                    ref_label = f"\\n[{num_refs} match{'es' if num_refs > 1 else ''}]"
                    fill_color = "#D3F9D8"  # Soft green
                    border_color = "#2B8A3E"
                    shape = "ellipse"
                else:
                    ref_label = ""
                    fill_color = "#FFFFFF"
                    border_color = "#ADB5BD"
                    shape = "circle"

                node_label = f"{display_char}{ref_label}"
                lines.append(
                    f'    {child_id} [label="{node_label}", shape={shape}, fillcolor="{fill_color}", color="{border_color}"];'
                )

                queue.append((child, depth + 1, new_path))

            # Add edge
            edge_label = "␣" if char == " " else char
            lines.append(f'    {get_node_id(curr_node)} -> {child_id} [label=" {edge_label} "];')

    lines.append("}")
    
    output_dot_path.write_text("\n".join(lines), encoding="utf-8")
    return total_rendered


def render_dot(dot_path: Path, output_image_path: Path) -> bool:
    """Attempts to render the .dot file to an image (PNG/SVG) using Graphviz CLI."""
    try:
        ext = output_image_path.suffix.lstrip(".")
        cmd = ["dot", f"-T{ext}", str(dot_path), "-o", str(output_image_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Visualize Suffix Trie using Graphviz.")
    parser.add_argument("--prefix", "-p", type=str, default=None, help="Focus visualization starting from a specific prefix (e.g. 'the', 'py').")
    parser.add_argument("--depth", "-d", type=int, default=4, help="Maximum tree depth to render (default: 4).")
    parser.add_argument("--max-nodes", "-m", type=int, default=80, help="Maximum nodes to render (default: 80).")
    parser.add_argument("--output", "-o", type=str, default="trie_visualization.dot", help="Output .dot file path.")
    args = parser.parse_args()

    sample_cache = Path("sample_trie_cache.pkl")
    dot_output = Path(args.output)
    png_output = dot_output.with_suffix(".png")
    svg_output = dot_output.with_suffix(".svg")

    print("=" * 60)
    print("🌲 TRIE GRAPHVIZ VISUALIZER")
    print("=" * 60)

    # 1. Load or build a sample Trie
    if sample_cache.exists():
        print(f"Loading sample Trie from '{sample_cache}'...")
        with open(sample_cache, "rb") as f:
            trie_root, registry = pickle.load(f)
    else:
        print("Building demo Trie from sample sentences...")
        demo_sentences = [
            (0, 1, "the osi model is a conceptual framework"),
            (0, 2, "the seven layers of the osi model"),
            (1, 10, "python is a high level programming language"),
            (1, 15, "intel x86 assembly language instructions"),
        ]
        trie_root = build_suffix_trie(demo_sentences)
        registry = [Path("sample_network.txt"), Path("sample_code.txt")]

    # 2. Export to DOT
    print(f"\nGenerating Graphviz DOT file: '{dot_output}' (prefix={args.prefix}, depth={args.depth}, max_nodes={args.max_nodes})...")
    node_count = export_trie_to_dot(
        root=trie_root,
        output_dot_path=dot_output,
        registry=registry,
        max_depth=args.depth,
        max_nodes=args.max_nodes,
        filter_prefix=args.prefix,
    )
    
    if node_count > 0:
        print(f"✅ Exported {node_count} nodes to '{dot_output}'")

        # 3. Attempt to render to PNG / SVG
        rendered = render_dot(dot_output, svg_output)
        if rendered:
            print(f"🖼️  Rendered diagram successfully to: '{svg_output}'")
        else:
            if render_dot(dot_output, png_output):
                print(f"🖼️  Rendered diagram successfully to: '{png_output}'")
            else:
                print("\n💡 Graphviz CLI ('dot') is not installed on system PATH.")
                print("   You can easily view the generated diagram by:")
                print("   1. Installing the 'Graphviz (dot) Preview' extension in VS Code.")
                print("   2. Pasting the contents of 'trie_visualization.dot' into: https://dreampuf.github.io/GraphvizOnline")

    print("\n" + "=" * 60)



if __name__ == "__main__":
    main()
