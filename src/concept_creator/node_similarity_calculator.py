import networkx as nx


import logging
from typing import Any, Dict, List


class NodeSimilarityCalculator:
    """
    Calculates similarity between nodes based on their properties and types.
    """

    # List of properties to ignore when comparing nodes
    IGNORE_PROPERTIES = [
        "id",
        "image_id",
        "session_id",
        "visualization",
        "uuid",
        "concept_id",
        "labels",
        "direction_sequence_index",
        "half_plane",
        "x1",
        "x2",
        "y1",
        "y2",
        "length",
    ]

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def calculate_similarity_matrix(
        self, graph1: nx.Graph, graph2: nx.Graph, path1: List[Any], path2: List[Any]
    ) -> List[List[float]]:
        """
        Calculate similarity scores between nodes in two paths.

        Args:
            graph1: First graph
            graph2: Second graph
            path1: First path
            path2: Second path

        Returns:
            2D matrix of similarity scores (higher = more similar)
        """
        # Initialize similarity matrix
        similarity_matrix = [
            [0.0 for _ in range(len(path2))] for _ in range(len(path1))
        ]

        # Calculate similarity for each node pair
        for i, node1 in enumerate(path1):
            for j, node2 in enumerate(path2):
                similarity_matrix[i][j] = self.calculate_node_similarity(
                    graph1, graph2, node1, node2
                )

        return similarity_matrix

    def calculate_node_similarity(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> float:
        """
        Calculate similarity between two nodes based on their properties and structural role.

        Args:
            graph1: First graph
            graph2: Second graph
            node1: First node
            node2: Second node

        Returns:
            Similarity score between 0 and 1
        """
        # Get node data
        node1_data = graph1.nodes[node1]
        node2_data = graph2.nodes[node2]

        # 1. Type compatibility
        node1_types = node1_data.get("labels", [])
        node2_types = node2_data.get("labels", [])

        # Check if they share any types
        common_types = set(node1_types).intersection(set(node2_types))
        if not common_types:
            return 0.0  # Different types, no similarity

        # 2. Property similarity
        return self._calculate_property_similarity(node1_data, node2_data)

    def _calculate_property_similarity(
        self, props1: Dict[str, Any], props2: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity between two sets of properties.

        Args:
            props1: Properties of first node
            props2: Properties of second node

        Returns:
            Similarity score between 0 and 1
        """
        # Get all properties from both nodes
        all_props = set(props1.keys()) | set(props2.keys())

        # Filter out ignored properties
        relevant_props = [p for p in all_props if p not in self.IGNORE_PROPERTIES]

        if not relevant_props:
            return 0.0

        matching_props = 0
        total_props = len(relevant_props)

        for prop in relevant_props:
            # Skip properties that don't exist in both nodes
            if prop not in props1 or prop not in props2:
                continue

            val1 = props1[prop]
            val2 = props2[prop]

            # Handle different property types
            if self._are_property_values_similar(val1, val2):
                matching_props += 1

        if total_props > 0:
            return matching_props / total_props
        return 0.0

    def _are_property_values_similar(self, val1: Any, val2: Any) -> bool:
        """
        Compare two property values to determine if they're similar.

        Args:
            val1: First value
            val2: Second value

        Returns:
            True if values are considered similar, False otherwise
        """
        # Same value
        if val1 == val2:
            return True

        # Try numeric comparison
        try:
            num1 = float(val1)
            num2 = float(val2)
            # Consider similar if within 20% difference
            diff = abs(num1 - num2) / max(max(abs(num1), abs(num2)), 1.0)
            return diff < 0.2
        except (ValueError, TypeError):
            pass

        # String comparison
        if isinstance(val1, str) and isinstance(val2, str):
            return val1 == val2

        # List comparison
        if isinstance(val1, list) and isinstance(val2, list):
            return len(set(val1) & set(val2)) > 0

        # Different types or no similarity found
        return False

    # TODO: remove this function
    def _get_node_types(self, node_data: Dict[str, Any]) -> List[str]:
        """
        Get the types/labels of a node.

        Args:
            node_data: Node data dictionary

        Returns:
            List of node type strings
        """
        labels = node_data.get("labels", [])

        if not isinstance(labels, list):
            if isinstance(labels, set):
                labels = list(labels)
            else:
                labels = [labels]

        return labels
