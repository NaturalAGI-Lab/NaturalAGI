from typing import Generator, Any, Tuple, Optional
import networkx as nx

from ..model.point import Point
from ..model.vector import Vector


class GraphTraversal:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def dfs_traversal(
        self, start_node: Any
    ) -> Generator[Tuple[Point, Optional[Vector]], None, None]:
        for edge in nx.dfs_edges(self.graph, start_node):
            source_node, target_node = edge

            # Convert to your Point and Vector objects
            source_data = self.graph.nodes[source_node]
            target_data = self.graph.nodes[target_node]

            point = None
            vector = None

            if self._is_point(source_data):
                point = Point.from_node_data(source_data)
            elif self._is_vector(source_data):
                vector = Vector.from_node_data(source_data)

            if self._is_point(target_data):
                point = Point.from_node_data(target_data)
            elif self._is_vector(target_data):
                vector = Vector.from_node_data(target_data)

            if point is None and vector is None:
                raise ValueError(f"Invalid node data: {source_data} or {target_data}")

            yield point, vector

    def _is_vector(self, node_data: dict) -> bool:
        return "Vector" in node_data["labels"]

    def _is_point(self, node_data: dict) -> bool:
        return "Point" in node_data["labels"]
