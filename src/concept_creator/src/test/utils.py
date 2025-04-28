import json
import networkx as nx
from typing import List, Optional, Tuple, Dict, Any


def load_graphs_from_file(file_path: str) -> List[nx.Graph]:
    """
    Load a list of networkx graphs from a JSON file.

    Args:
        file_path: Path to the JSON file containing graph data

    Returns:
        List of networkx graphs, one for each graph in the JSON
    """
    # Load the JSON data
    with open(file_path, "r") as f:
        data = json.load(f)

    graphs = []
    for graph_data in data:
        G = nx.Graph()

        # Add nodes with their attributes
        for node in graph_data.get("nodes", []):
            node_id = node.get("id")
            if not node_id:
                continue

            # Add all node attributes directly
            G.add_node(node_id, **node)

        # Add edges from the links
        for link in graph_data.get("links", []):
            source = link.get("source")
            target = link.get("target")
            if source and target:
                # Add all link attributes as edge attributes
                G.add_edge(source, target, **link)

        if G.number_of_nodes() > 0:
            graphs.append(G)

    return graphs


def find_start_point(graph: nx.Graph) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Find the start point of the graph.

    Args:
        graph: NetworkX graph

    Returns:
        Tuple of (node_id, node_data) for the start point or None if not found
    """
    # First, look for nodes with StartPoint label
    for node_id, node_data in graph.nodes(data=True):
        if "StartPoint" in node_data.get("labels", []):
            return node_id, node_data

    # If no explicit StartPoint, try vectors with quadrant=1
    for node_id, node_data in graph.nodes(data=True):
        if "Vector" in node_data.get("labels", []) and node_data.get("quadrant") == 1:
            return node_id, node_data

    # If still not found, try points connected to the most edges
    if graph.number_of_nodes() > 0:
        # Find point with highest degree (most connections)
        points = [
            (node_id, node_data)
            for node_id, node_data in graph.nodes(data=True)
            if "Point" in node_data.get("labels", [])
        ]

        if points:
            points_with_degree = [
                (node_id, graph.degree(node_id)) for node_id, _ in points
            ]
            points_with_degree.sort(key=lambda x: x[1], reverse=True)
            start_id = points_with_degree[0][0]
            return start_id, graph.nodes[start_id]

    return None
