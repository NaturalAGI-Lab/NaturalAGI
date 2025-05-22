import logging
from typing import Set
import numpy as np
import networkx as nx

from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils


class StartPointService:
    def __init__(
        self,
        centroid: np.ndarray,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.centroid = centroid
        self.logger = logger
        self.critical_point_labels: Set[str] = {
            CriticalPointType.END_POINT.value,
            CriticalPointType.CORNER_POINT.value,
            CriticalPointType.INTERSECTION_POINT.value,
            CriticalPointType.START_POINT.value,
        }

    def get_start_point(self, graph: nx.Graph) -> int:
        """
        Returns the node_id of the most appropriate starting point in the given graph.
        Simply finds the closest point of the appropriate type to the characteristic centroid.

        For open contours: Uses StartPoint or EndPoint
        For closed contours: Uses CornerPoint or IntersectionPoint

        Args:
            graph: The graph to analyze

        Returns:
            The node_id of the selected start point or None if no suitable point found
        """
        if self.centroid is None:
            raise ValueError("Centroid not set.")

        structure_type = self._determine_structure_type(graph)

        # Define appropriate labels based on structure type
        appropriate_labels = []
        if structure_type == "Open":
            appropriate_labels = [
                CriticalPointType.END_POINT.value,
                CriticalPointType.START_POINT.value,
            ]
        else:  # Closed structure
            appropriate_labels = [
                CriticalPointType.CORNER_POINT.value,
                CriticalPointType.INTERSECTION_POINT.value,
            ]

        # Find the closest point of the appropriate type
        candidates = []

        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            norm_x = data.get("normalized_x")
            norm_y = data.get("normalized_y")

            if norm_x is None or norm_y is None:
                continue

            # Check if node has any of the appropriate labels for this structure type
            if any(label in appropriate_labels for label in node_labels):
                # Calculate distance to centroid
                node_coords = np.array([norm_x, norm_y])
                distance = np.linalg.norm(node_coords - self.centroid)
                candidates.append((node_id, distance))

        # Sort by distance (closest first)
        candidates.sort(key=lambda x: x[1])

        # Return the closest appropriate point
        if candidates:
            return candidates[0][0]

        # Fallback: just find the closest critical point of any type
        fallback_candidates = []
        for node_id, data in graph.nodes(data=True):
            if GraphUtils.is_critical_point(data):
                norm_x = data.get("normalized_x")
                norm_y = data.get("normalized_y")
                if norm_x is not None and norm_y is not None:
                    node_coords = np.array([norm_x, norm_y])
                    distance = np.linalg.norm(node_coords - self.centroid)
                    fallback_candidates.append((node_id, distance))

        fallback_candidates.sort(key=lambda x: x[1])
        if fallback_candidates:
            self.logger.warning(
                "No points with appropriate labels found. Using any critical point."
            )
            return fallback_candidates[0][0]

        self.logger.error("No suitable start point found in the graph")
        return None

    def change_start_point(self, graph: nx.Graph, new_start_point: int) -> nx.Graph:
        old_start_point = self._get_old_start_point(graph)
        if old_start_point is None:
            raise ValueError("Old start point not found")

        graph.nodes[old_start_point]["labels"].remove(
            CriticalPointType.START_POINT.value
        )
        if nx.degree(graph, old_start_point) == 1:
            graph.nodes[old_start_point]["labels"].append(
                CriticalPointType.END_POINT.value
            )

        graph.nodes[new_start_point]["labels"].clear()
        graph.nodes[new_start_point]["labels"].append(
            CriticalPointType.START_POINT.value
        )
        graph.nodes[new_start_point]["labels"].append("Point")
        return graph

    def _get_old_start_point(self, graph: nx.Graph) -> int:
        for node, data in graph.nodes(data=True):
            if CriticalPointType.START_POINT.value in data["labels"]:
                return node
        return None

    def _determine_structure_type(self, graph: nx.Graph) -> str:
        return "Open" if any(nx.degree(graph, node) == 1 for node in graph.nodes) else "Closed"
