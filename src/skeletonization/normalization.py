import networkx as nx
import math


def normalize_graph(graph: nx.Graph) -> nx.Graph:
    """Normalizes node coordinates between -1 and 1

    Args:
        graph (nx.Graph): Graph to normalize

    Returns:
        nx.Graph: Normalized graph
    """
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    # Find min and max coordinates from all points
    for _, node_data in graph.nodes(data=True):
        if "x" in node_data and "y" in node_data:
            x = node_data["x"]
            y = node_data["y"]
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    # Calculate center of the bounding box
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Calculate half-width and half-height of the bounding box
    half_width = (max_x - min_x) / 2
    half_height = (max_y - min_y) / 2

    # Maximum distance is from center to the corner of the bounding box
    max_distance = math.sqrt(half_width**2 + half_height**2)

    # Normalize all coordinates
    for _, node_data in graph.nodes(data=True):
        if "x" in node_data and "y" in node_data:
            normalized_x = (node_data["x"] - center_x) / max_distance
            node_data["normalized_x"] = round(normalized_x, 1)
            normalized_y = (node_data["y"] - center_y) / max_distance
            node_data["normalized_y"] = round(normalized_y, 1)
    return graph
