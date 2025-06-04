from typing import Any, List, Optional, Tuple
import networkx as nx
import numpy as np

from common.critical_point import CriticalPointType


class StartPointSelector:
    def __init__(self):
        self.critical_point_labels = {
            CriticalPointType.END_POINT.value,
            CriticalPointType.CORNER_POINT.value,
            CriticalPointType.INTERSECTION_POINT.value,
            CriticalPointType.START_POINT.value,
        }

    def find_start_point_by_centroid(
        self,
        graph: nx.Graph,
        centroid: np.ndarray,
        preferred_labels: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """
        Finds the best start point in a graph based on proximity to a centroid.

        Args:
            graph: The NetworkX graph to analyze
            centroid: Target centroid coordinates as numpy array [x, y]
            preferred_labels: List of preferred node labels to prioritize

        Returns:
            The node_id of the selected start point or None if no suitable point found
        """
        candidates = self._find_candidates_with_labels(graph, preferred_labels, centroid)

        if candidates:
            return candidates[0][0]

        fallback_candidates = self._find_fallback_candidates(graph, centroid)
        if fallback_candidates:
            return fallback_candidates[0][0]

        return None

    def find_start_point_for_structure_type(
        self, graph: nx.Graph, centroid: np.ndarray, structure_type: str
    ) -> Optional[Any]:
        """
        Finds start point based on structure type (Open/Closed).

        Args:
            graph: The NetworkX graph to analyze
            centroid: Target centroid coordinates
            structure_type: "Open" or "Closed"

        Returns:
            The node_id of the selected start point or None if no suitable point found
        """
        if structure_type == "Open":
            preferred_labels = [
                CriticalPointType.END_POINT.value,
                CriticalPointType.START_POINT.value,
            ]
        elif structure_type == "Closed":
            preferred_labels = [
                CriticalPointType.CORNER_POINT.value,
                CriticalPointType.INTERSECTION_POINT.value,
            ]
        else:
            raise ValueError(f"Unknown structure type: {structure_type}")

        return self.find_start_point_by_centroid(graph, centroid, preferred_labels)

    def _find_candidates_with_labels(
        self, graph: nx.Graph, labels: List[str], centroid: np.ndarray
    ) -> List[Tuple[Any, float]]:
        """Find candidates with specific labels, sorted by distance to centroid."""
        candidates = []

        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            norm_x = data.get("normalized_x")
            norm_y = data.get("normalized_y")

            if norm_x is None or norm_y is None:
                continue

            if any(label in labels for label in node_labels):
                node_coords = np.array([norm_x, norm_y])
                distance = np.linalg.norm(node_coords - centroid)
                candidates.append((node_id, distance))

        candidates.sort(key=lambda x: x[1])
        return candidates

    def _find_fallback_candidates(
        self, graph: nx.Graph, centroid: np.ndarray
    ) -> List[Tuple[Any, float]]:
        """Find any critical points as fallback, sorted by distance to centroid."""
        fallback_candidates = []

        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            if any(label in self.critical_point_labels for label in node_labels):
                norm_x = data.get("normalized_x")
                norm_y = data.get("normalized_y")
                if norm_x is not None and norm_y is not None:
                    node_coords = np.array([norm_x, norm_y])
                    distance = np.linalg.norm(node_coords - centroid)
                    fallback_candidates.append((node_id, distance))

        fallback_candidates.sort(key=lambda x: x[1])
        return fallback_candidates

    def determine_structure_type(self, graph: nx.Graph) -> str:
        """
        Determines if the graph structure is Open (has endpoints) or Closed.

        Args:
            graph: The NetworkX graph to analyze

        Returns:
            "Open" if graph has endpoints (degree 1 nodes), "Closed" otherwise
        """
        for node_id in graph.nodes:
            if nx.degree(graph, node_id) == 1:
                return "Open"
        return "Closed"
