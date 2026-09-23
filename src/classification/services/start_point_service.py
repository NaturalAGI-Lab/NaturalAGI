import logging
from typing import Optional, Set
import numpy as np
import networkx as nx

from common.critical_point import CriticalPointType


class StartPointService:
    TYPE_PRIORITY = {
        CriticalPointType.INTERSECTION_POINT.value: 2,
        CriticalPointType.CORNER_POINT.value: 1,
    }

    def __init__(
        self,
        centroid: np.ndarray,
        expected_start_degree: Optional[int] = None,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.centroid = centroid
        self.expected_start_degree = expected_start_degree
        self.logger = logger
        self.critical_point_labels: Set[str] = {
            CriticalPointType.END_POINT.value,
            CriticalPointType.CORNER_POINT.value,
            CriticalPointType.INTERSECTION_POINT.value,
            CriticalPointType.START_POINT.value,
        }

    def get_start_point(self, graph: nx.Graph) -> int:
        if self.centroid is None:
            raise ValueError("Centroid not set.")

        structure_type = self._determine_structure_type(graph)

        appropriate_labels = []
        if structure_type == "Open":
            appropriate_labels = [
                CriticalPointType.END_POINT.value,
                CriticalPointType.START_POINT.value,
            ]
        else:
            appropriate_labels = [
                CriticalPointType.CORNER_POINT.value,
                CriticalPointType.INTERSECTION_POINT.value,
            ]

        centroid_norm = np.linalg.norm(self.centroid)
        if centroid_norm > 0:
            centroid_direction = self.centroid / centroid_norm
        else:
            centroid_direction = np.array([0.0, 0.0])

        node_type_map = {}
        candidates = []

        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            norm_x = data.get("normalized_x")
            norm_y = data.get("normalized_y")

            if norm_x is None or norm_y is None:
                continue

            if any(label in appropriate_labels for label in node_labels):
                node_coords = np.array([norm_x, norm_y])
                projection = np.dot(node_coords, centroid_direction)
                node_type = None
                for label_type in [
                    CriticalPointType.INTERSECTION_POINT.value,
                    CriticalPointType.CORNER_POINT.value,
                    CriticalPointType.END_POINT.value,
                    CriticalPointType.START_POINT.value,
                ]:
                    if label_type in node_labels:
                        node_type = label_type
                        break
                node_type_map[node_id] = node_type
                candidates.append((node_id, projection))

        if structure_type == "Closed":
            exp_deg = self.expected_start_degree
            candidates.sort(
                key=lambda x: (
                    self.TYPE_PRIORITY.get(node_type_map.get(x[0]), 0),
                    -abs(graph.degree(x[0]) - exp_deg) if exp_deg is not None else 0,
                    x[1],
                ),
                reverse=True,
            )
        else:
            candidates.sort(key=lambda x: x[1], reverse=True)

        if candidates:
            return candidates[0][0]

        fallback_candidates = []
        for node_id, data in graph.nodes(data=True):
            node_labels = data.get("labels", [])
            if any(label in self.critical_point_labels for label in node_labels):
                norm_x = data.get("normalized_x")
                norm_y = data.get("normalized_y")
                if norm_x is not None and norm_y is not None:
                    node_coords = np.array([norm_x, norm_y])
                    projection = np.dot(node_coords, centroid_direction)
                    fallback_candidates.append((node_id, projection))

        fallback_candidates.sort(key=lambda x: x[1], reverse=True)
        if fallback_candidates:
            self.logger.warning(
                "No points with appropriate labels found. Using any critical point."
            )
            return fallback_candidates[0][0]

        self.logger.error("No suitable start point found in the graph", exc_info=True)
        return None

    def change_start_point(self, graph: nx.Graph, new_start_point: int) -> nx.Graph:
        old_start_point = self._get_old_start_point(graph)
        if old_start_point is not None:
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
        graph.graph["start_point"] = new_start_point
        return graph

    def _get_old_start_point(self, graph: nx.Graph) -> int:
        for node, data in graph.nodes(data=True):
            if CriticalPointType.START_POINT.value in data["labels"]:
                return node
        return None

    def _determine_structure_type(self, graph: nx.Graph) -> str:
        # Concept-driven regime: the concept's expected_start_degree says whether its anchor
        # is a junction (>1 -> "Closed") or a tail (==1 -> "Open"). Honoring it keeps the
        # image's anchor consistent with the concept's, so a single noise spur cannot flip a
        # closed double-loop ("8") into the open regime and pin the start on the spur.
        if self.expected_start_degree is not None:
            return "Open" if int(self.expected_start_degree) <= 1 else "Closed"
        return (
            "Open"
            if any(nx.degree(graph, node) == 1 for node in graph.nodes)
            else "Closed"
        )
