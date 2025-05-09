from typing import Tuple
import numpy as np
import networkx as nx

from src.model.critical_point import CriticalPointType

class StartPointModifier:
    def __init__(self, start_point_characteristic: Tuple[str, np.ndarray]):
        self.start_point_characteristic = start_point_characteristic

    def change_start_point(self, graph: nx.Graph, new_start_point: int) -> nx.Graph:
        old_start_point = self._get_old_start_point(graph)
        if old_start_point is None:
            raise ValueError("Old start point not found")
        
        graph.nodes[old_start_point]["labels"].remove(CriticalPointType.START_POINT.value)
        if nx.degree(graph, old_start_point) == 1:
            graph.nodes[old_start_point]["labels"].append(CriticalPointType.END_POINT.value)

        graph.nodes[new_start_point]["labels"].clear()
        graph.nodes[new_start_point]["labels"].append(CriticalPointType.START_POINT.value)
        return graph
    
    def _get_old_start_point(self, graph: nx.Graph) -> int:
        for node, data in graph.nodes(data=True):
            if CriticalPointType.START_POINT.value in data["labels"]:
                return node
        return None
