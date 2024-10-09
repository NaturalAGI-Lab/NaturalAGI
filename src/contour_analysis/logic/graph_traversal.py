from typing import Generator, Any, Tuple, Optional
import networkx as nx

from model.point import Point
from model.vector import Vector


class GraphTraversal:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def dfs_traversal(self, start_node: Any) -> Generator[Tuple[Any, Optional[dict]], None, None]:
        """
        Generator for DFS traversal.
        
        Args:
            start_node (Any): The starting node for DFS.
        
        Yields:
            Tuple[Any, Optional[dict]]: A tuple containing the current node and its incoming edge (or None for the start node).
        """
        visited_nodes = set()
        visited_edges = set()

        def _dfs(node_id: str, incoming_vector: Optional[Vector] = None):
            if node_id not in visited_nodes:
                visited_nodes.add(node_id)
                node_data = self.graph.nodes[node_id]
                point = Point(id=node_data["uuid"], x=node_data['x'], y=node_data['y'])
                yield point, incoming_vector

                for neighbor_id in sorted(self.graph.neighbors(node_id)):
                    edge = tuple(sorted([node_id, neighbor_id]))
                    if edge not in visited_edges:
                        visited_edges.add(edge)
                        edge_data = self.graph.edges[edge]
                        vector = Vector(
                            id=edge_data['uuid'],
                            x1=edge_data['x1'],
                            y1=edge_data['y1'],
                            x2=edge_data['x2'],
                            y2=edge_data['y2'],
                            length=edge_data['length']
                        )
                        yield from _dfs(neighbor_id, vector)

        yield from _dfs(start_node)
