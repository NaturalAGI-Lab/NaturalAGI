import collections
from functools import singledispatch
from typing import Any, Dict, Set

import networkx as nx

from .critical_point import CriticalPointType



LABELS_KEY = "labels"

CRITICAL_POINT_TYPES = [
    CriticalPointType.INTERSECTION_POINT,
    CriticalPointType.CORNER_POINT,
    CriticalPointType.END_POINT,
    CriticalPointType.START_POINT,
]


class GraphUtils:
    """
    Utility class for graph operations
    """

    @staticmethod
    def get_first_point_by_type(
        graph: nx.Graph, critical_point_type: CriticalPointType
    ) -> Any:
        """Getting the first point of the graph by type"""
        for node, data in graph.nodes(data=True):
            labels = data.get(LABELS_KEY, [])
            if critical_point_type.value in labels:
                return node
        raise ValueError(f"No {critical_point_type} found in the graph")

    @staticmethod
    def is_critical_point(
        node_data: Dict[str, Any],
        supported_types: Set[CriticalPointType] = CRITICAL_POINT_TYPES,
    ) -> bool:
        """
        Check if a node is a critical point based on its labels.
        """
        labels = node_data.get(LABELS_KEY, [])
        return any(supported_type.value in labels for supported_type in supported_types)

    @staticmethod
    def find_next_critical_point_bfs(
        graph: nx.Graph,
        start_point: Any,
        prev_point: Any,
        supported_types: Set[CriticalPointType] = CRITICAL_POINT_TYPES,
    ) -> Any:
        """
        Find the next critical point in the graph using BFS.
        """
        queue = collections.deque([start_point])
        visited = set()
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if (
                GraphUtils.is_critical_point(graph.nodes[current], supported_types)
                and current != prev_point
                and current != start_point
            ):
                return current
            for neighbor in graph.neighbors(current):
                if neighbor not in visited and neighbor != prev_point:
                    queue.append(neighbor)

        if prev_point is None:
            return None
        
        # Check if there is a loop back to the previous point, so it's not considered of backtracking, but rather a loop that returns back to the previous point
        number_of_paths_back = len(
            list(nx.all_simple_paths(graph, prev_point, start_point))
        )
        if number_of_paths_back > 1:
            return prev_point
        return None

    @staticmethod
    def is_same_critical_point_type(
        node_c_data: Dict[str, Any], node_i_data: Dict[str, Any]
    ) -> bool:
        """
        Check if two nodes are the same critical point type.
        """
        labels_c = node_c_data.get(LABELS_KEY, [])
        labels_i = node_i_data.get(LABELS_KEY, [])
        return set(labels_c) == set(labels_i)

    @staticmethod
    def is_intersection_point(node_data: Dict[str, Any]) -> bool:
        """
        Check if a node is an intersection point.
        """
        return CriticalPointType.INTERSECTION_POINT.value in node_data.get(
            LABELS_KEY, []
        )

    @staticmethod
    def is_endpoint(node_data: Dict[str, Any]) -> bool:
        """
        Check if a node is an endpoint.
        """
        return CriticalPointType.END_POINT.value in node_data.get(LABELS_KEY, [])

    @staticmethod
    def is_corner_point(node_data: Dict[str, Any]) -> bool:
        """
        Check if a node is a corner point.
        """
        return CriticalPointType.CORNER_POINT.value in node_data.get(LABELS_KEY, [])

    @staticmethod
    def get_critical_point_type(node_data: Dict[str, Any]) -> CriticalPointType:
        """
        Get the critical point type of a node.
        """
        labels = node_data.get(LABELS_KEY, [])
        for point_type in CriticalPointType:
            if point_type.value in labels:
                return point_type
        raise ValueError(f"No critical point type found in the node {node_data}")

    @staticmethod
    def is_graph_isomorphic(graph1: nx.Graph, graph2: nx.Graph) -> bool:
        def node_match(node1, node2):
            return set(node1[LABELS_KEY]) == set(node2[LABELS_KEY])

        return nx.is_isomorphic(graph1, graph2, node_match=node_match)
