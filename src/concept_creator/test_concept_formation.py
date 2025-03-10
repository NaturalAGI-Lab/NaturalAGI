import networkx as nx
import matplotlib.pyplot as plt
import json
import logging
from typing import List, Dict, Any
import os
import sys

from concept_formation import ConceptFormation


# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def load_graph_from_json(file_path: str) -> nx.Graph:
    """
    Load a graph from a JSON file containing Neo4j export format.

    Args:
        file_path: Path to the JSON file

    Returns:
        NetworkX graph
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    graph = nx.Graph()

    # Create a mapping from Neo4j IDs to new node IDs
    node_mapping = {}

    # Add nodes
    for item in data:
        if "n" in item:  # This is a node
            node_data = item["n"]
            node_id = node_data["identity"]
            # Create a more friendly node ID
            new_id = f"n{node_id}"
            node_mapping[node_id] = new_id

            # Add the node with its properties
            properties = node_data.get("properties", {})
            # Include labels in properties
            properties["labels"] = node_data.get("labels", [])
            graph.add_node(new_id, **properties)

    # Add edges
    for item in data:
        if "r" in item:  # This is a relationship
            rel_data = item["r"]
            start_id = rel_data["start"]
            end_id = rel_data["end"]

            # Use the mapped IDs
            if start_id in node_mapping and end_id in node_mapping:
                start_new_id = node_mapping[start_id]
                end_new_id = node_mapping[end_id]

                # Add the edge with its properties
                properties = rel_data.get("properties", {})
                # Include type in properties
                properties["type"] = rel_data.get("type", "")
                graph.add_edge(start_new_id, end_new_id, **properties)

    return graph


def draw_graph(graph: nx.Graph, title: str = "", highlight_nodes: List = None):
    """
    Visualize a graph with optional node highlighting.

    Args:
        graph: NetworkX graph to visualize
        title: Title for the plot
        highlight_nodes: List of nodes to highlight
    """
    plt.figure(figsize=(12, 8))

    # Create position layout
    pos = nx.spring_layout(graph, seed=42)

    # Node colors based on type
    node_colors = []
    for node in graph.nodes():
        labels = graph.nodes[node].get("labels", [])
        if "IntersectionPoint" in labels:
            node_colors.append("red")
        elif "CornerPoint" in labels:
            node_colors.append("blue")
        elif "EndPoint" in labels:
            node_colors.append("green")
        elif "StartPoint" in labels:
            node_colors.append("purple")
        else:
            node_colors.append("gray")

    # Draw nodes
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=100)

    # Highlight specific nodes if provided
    if highlight_nodes:
        nx.draw_networkx_nodes(
            graph, pos, nodelist=highlight_nodes, node_color="yellow", node_size=150
        )

    # Draw edges
    nx.draw_networkx_edges(graph, pos)

    # Draw labels (use just the first 5 chars of node ID to avoid clutter)
    labels = {node: node[:5] for node in graph.nodes()}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8)

    plt.title(title)
    plt.axis("off")
    plt.tight_layout()

    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Save the figure
    filename = f"output/{title.replace(' ', '_').lower()}.png"
    plt.savefig(filename)
    print(f"Saved figure to {filename}")
    plt.close()


def main():
    # Check if JSON files are provided
    if len(sys.argv) < 2:
        print("Usage: python test_concept_formation.py <json_file1> [json_file2] ...")
        print("Using sample data from 'graph_sample.json' if available")

        # Try to use sample data if no files provided
        json_files = ["graph_sample.json"]
        if not os.path.exists(json_files[0]):
            print(
                f"Error: {json_files[0]} not found. Please provide JSON files to process."
            )
            return
    else:
        json_files = sys.argv[1:]

    # Load graphs from JSON files
    graphs = []
    for json_file in json_files:
        try:
            graph = load_graph_from_json(json_file)
            graphs.append(graph)
            print(
                f"Loaded graph from {json_file} with {len(graph.nodes())} nodes and {len(graph.edges())} edges"
            )

            # Visualize each input graph
            draw_graph(graph, f"Input Graph {len(graphs)}")
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    if not graphs:
        print("No graphs loaded. Exiting.")
        return

    # Create concept from the graphs
    concept_formation = ConceptFormation()
    concept_graph = concept_formation.create_concept(graphs)

    print(
        f"Created concept graph with {len(concept_graph.nodes())} nodes and {len(concept_graph.edges())} edges"
    )

    # Visualize the concept graph
    draw_graph(
        concept_graph,
        "Concept Graph",
        highlight_nodes=[
            n
            for n, d in concept_graph.nodes(data=True)
            if any(
                label in d.get("labels", [])
                for label in [
                    "IntersectionPoint",
                    "CornerPoint",
                    "EndPoint",
                    "StartPoint",
                ]
            )
        ],
    )

    print("Done!")


if __name__ == "__main__":
    main()
