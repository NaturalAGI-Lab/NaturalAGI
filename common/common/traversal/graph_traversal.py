from typing import Generator, Any, Tuple, Optional, List
from dataclasses import dataclass
import networkx as nx
import logging
from ..model.point import Point
from ..model.vector import Vector


@dataclass
class TraversalSequence:
    start_point: Point
    vector: Vector
    end_point: Point


class GraphTraversal:
    def __init__(self, graph: nx.Graph):
        self.graph = graph
        self.logger = logging.getLogger(__name__)

    def dfs_traversal(
        self, start_node: Any
    ) -> Generator[TraversalSequence, None, None]:
        visited_vectors = set()
        visited_nodes = set()

        def dfs_recursive(current_node: Any, path: List[Any]) -> None:
            if current_node in visited_nodes:
                return

            visited_nodes.add(current_node)
            path.append(current_node)

            # If we have a sequence of 3 nodes, check if it follows point-vector-point pattern
            if len(path) >= 3:
                start_node_id = path[-3]
                vector_node_id = path[-2]
                end_node_id = path[-1]

                start_data = self.graph.nodes[start_node_id]
                vector_data = self.graph.nodes[vector_node_id]
                end_data = self.graph.nodes[end_node_id]

                # Check if sequence follows point-vector-point pattern
                if (
                    self._is_point(start_data)
                    and self._is_vector(vector_data)
                    and self._is_point(end_data)
                    and vector_node_id not in visited_vectors
                ):
                    self.logger.info(
                        f"Found sequence: {start_node_id} -> {vector_node_id} -> {end_node_id}"
                    )
                    visited_vectors.add(vector_node_id)

                    start_point = Point.from_node_data(start_data)
                    vector = Vector.from_node_data(vector_data)
                    end_point = Point.from_node_data(end_data)

                    yield TraversalSequence(start_point, vector, end_point)

            # Continue DFS to neighbors
            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in visited_nodes:
                    yield from dfs_recursive(neighbor, path.copy())

        yield from dfs_recursive(start_node, [])

    def _is_vector(self, node_data: dict) -> bool:
        return "Vector" in node_data["labels"]

    def _is_point(self, node_data: dict) -> bool:
        return "Point" in node_data["labels"]
