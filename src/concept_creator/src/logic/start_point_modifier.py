from typing import Optional, Tuple
import numpy as np
import networkx as nx

from common.critical_point import CriticalPointType


class StartPointModifier:
    def __init__(
        self,
        start_point_characteristic: Tuple[str, np.ndarray],
        expected_start_degree: Optional[int] = None,
    ):
        self.start_point_characteristic = start_point_characteristic
        self.expected_start_degree = expected_start_degree

    def change_start_point(self, graph: nx.Graph, new_start_point: int) -> nx.Graph:
        original = [
            label
            for label in graph.nodes[new_start_point]["labels"]
            if label not in ("Point", CriticalPointType.START_POINT.value)
        ]
        graph.nodes[new_start_point]["labels"] = [
            CriticalPointType.START_POINT.value,
            "Point",
            *original,
        ]
        graph.nodes[new_start_point]["centroid"] = self.start_point_characteristic[1]
        if self.expected_start_degree is not None:
            graph.nodes[new_start_point]["expected_start_degree"] = self.expected_start_degree
        graph.graph["start_point"] = new_start_point
        return graph
