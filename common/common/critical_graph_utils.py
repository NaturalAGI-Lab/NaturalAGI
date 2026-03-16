from typing import List, Set, Tuple, Any
import networkx as nx

from .critical_point import CriticalPointType

CRITICAL_POINT_TYPES = [
    CriticalPointType.INTERSECTION_POINT,
    CriticalPointType.CORNER_POINT,
    CriticalPointType.END_POINT,
    CriticalPointType.START_POINT,
]


class CriticalGraphUtils:
    """Utility class for critical graph operations"""
    
    @staticmethod
    def _is_critical_graph_isomorphic(
        graph1: nx.Graph, graph2: nx.Graph, critical_point_types: Set[CriticalPointType]
    ) -> bool:
        """Check if two critical graphs are isomorphic"""
        crit_graph1, _ = CriticalGraphUtils.get_critical_graph(graph1, critical_point_types)
        crit_graph2, _ = CriticalGraphUtils.get_critical_graph(graph2, critical_point_types)
        return nx.is_isomorphic(crit_graph1, crit_graph2)
    
    
    @staticmethod
    def get_critical_graph(
        graph: nx.Graph, critical_point_types: Set[CriticalPointType] = CRITICAL_POINT_TYPES
    ) -> Tuple[nx.Graph, List[Any]]:
        """Get the critical graph from the graph.

        Constructs a graph containing only nodes of the specified critical_point_types.
        An edge exists between two critical nodes in the result graph if there is a path
        between them in the original graph consisting only of non-critical nodes
        (excluding the start and end critical nodes themselves).

        Args:
            graph: The original graph.
            critical_point_types: A list of CriticalPointType enums to include in the critical graph.

        Returns:
            Tuple of (New graph with only critical points and preserved topology, List of critical points)
        """
        # Create a new graph
        critical_graph = nx.Graph()

        # Identify critical points
        critical_points = []
        for node, data in graph.nodes(data=True):
            labels = data.get("labels", "")
            if any(critical_point_type.value in labels for critical_point_type in critical_point_types):
                critical_points.append(node)
                # Copy node and its attributes to the new graph
                critical_graph.add_node(node, **data)

        # Connect critical points if there's a path between them in the original graph
        for i, source in enumerate(critical_points):
            for target in critical_points[i + 1 :]:
                if source != target:
                    # Check if there's a path between these critical points in the original graph
                    # that doesn't go through other critical points
                    if CriticalGraphUtils._has_path_excluding_others(
                        graph, source, target, critical_points
                    ):
                        # Add edge between these critical points in the new graph
                        critical_graph.add_edge(source, target)

        return critical_graph, critical_points

    @staticmethod
    def _has_path_excluding_others(
        graph: nx.Graph, source: Any, target: Any, critical_points: List[Any]
    ) -> bool:
        """
        Check if there's a path between source and target that doesn't go through other critical points.

        Args:
            graph: Original graph
            source: Source node
            target: Target node
            critical_points: List of all critical points

        Returns:
            True if there's a valid path, False otherwise
        """
        # Create a subgraph excluding other critical points
        excluded_nodes = [
            node for node in critical_points if node != source and node != target
        ]
        subgraph = graph.copy()
        subgraph.remove_nodes_from(excluded_nodes)

        try:
            nx.shortest_path(subgraph, source, target)
            return True
        except nx.NetworkXNoPath:
            return False