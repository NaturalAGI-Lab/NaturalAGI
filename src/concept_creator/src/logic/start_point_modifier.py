from typing import Tuple
import numpy as np
import networkx as nx

from common.critical_point import CriticalPointType


class StartPointModifier:
    def __init__(self, start_point_characteristic: Tuple[str, np.ndarray]):
        self.start_point_characteristic = start_point_characteristic

    def change_start_point(self, graph: nx.Graph, new_start_point: int) -> nx.Graph:
        graph.nodes[new_start_point]["labels"].clear()
        graph.nodes[new_start_point]["labels"].append(
            CriticalPointType.START_POINT.value
        )
        graph.nodes[new_start_point]["labels"].append("Point")
        graph.nodes[new_start_point]["centroid"] = self.start_point_characteristic[1]
        graph.graph["start_point"] = new_start_point
        return graph
