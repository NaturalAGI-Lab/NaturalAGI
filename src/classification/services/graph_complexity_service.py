import logging
from typing import Any, List

import networkx as nx

from common import GraphUtils
from common.critical_point import CriticalPointType


class GraphComplexityService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.critical_point_to_complexity = {
            CriticalPointType.INTERSECTION_POINT: 3,
            CriticalPointType.CORNER_POINT: 1,
            CriticalPointType.END_POINT: 2,
            CriticalPointType.START_POINT: 2,
        }

    def get_default_graph_complexity(self, graph: nx.Graph) -> int:
        return len(graph.nodes) + len(graph.edges)

    def get_critical_point_graph_complexity(self, graph: nx.Graph) -> int:
        critical_points = self.get_graph_critical_points(graph)
        return sum(
            self.critical_point_to_complexity[
                GraphUtils.get_critical_point_type(graph.nodes[node])
            ]
            for node in critical_points
        )

    def get_graph_critical_points(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node in graph.nodes
            if GraphUtils.is_critical_point(graph.nodes[node])
        ]
