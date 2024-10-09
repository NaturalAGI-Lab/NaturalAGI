import logging
import math
from typing import Optional, List, Tuple, Any
import networkx as nx

from model.point import Point
from logic.graph_traversal import GraphTraversal
from service.visitor_result_persistence_service import VisitorResultPersistenceService
from visitors.visitor import Visitor
from model.vector import Vector


class NetworkxGraphAnalysis:
    def __init__(
        self,
        graph: nx.Graph,
        visitor_result_persistence_service: VisitorResultPersistenceService,
    ):
        self.graph = graph
        self.visitors: List[Visitor] = []
        self.graph_traversal = GraphTraversal(self.graph)
        self.visitor_result_persistence_service = visitor_result_persistence_service

    def add_visitor(self, visitor: Visitor):
        self.visitors.append(visitor)

    def analyze_graph(self, image_id: str, session_id: str):
        top_leftmost_point = self.find_top_leftmost_point()

        for node in self.graph_traversal.dfs_traversal(top_leftmost_point):
            node_data = self.graph.nodes[node]
            for visitor in self.visitors:
                visitor.visit_point(node_data)
                self.visitor_result_persistence_service.save_visitor_result(
                    visitor, node_data, image_id, session_id
                )

            for neighbor in self.graph.neighbors(node):
                edge_data = self.graph[node][neighbor]
                vector_id = edge_data["uuid"]

                source_node = self.graph.nodes[node]
                target_node = self.graph.nodes[neighbor]

                x1 = source_node["x"]
                y1 = source_node["y"]
                x2 = target_node["x"]
                y2 = target_node["y"]

                length = self.calculate_length((x1, y1), (x2, y2))

                vector = Vector(id=vector_id, x1=x1, y1=y1, x2=x2, y2=y2, length=length)

                for visitor in self.visitors:
                    visitor.visit_line(vector)
                    self.visitor_result_persistence_service.save_visitor_result(
                        visitor, vector, image_id, session_id
                    )

    def find_top_leftmost_point(self) -> Optional[Any]:
        """
        Finds the top-leftmost point in the graph based on x and y coordinates.

        Returns:
            Optional[Any]: The top-leftmost point node or None if the graph is empty.
        """
        if not self.graph.nodes:
            return None

        top_leftmost_node = min(
            self.graph.nodes,
            key=lambda n: (self.graph.nodes[n]["x"], self.graph.nodes[n]["y"])
        )
        return top_leftmost_node

    def calculate_length(
        self, coordinates1: Tuple[float, float], coordinates2: Tuple[float, float]
    ) -> float:
        dx = coordinates2[0] - coordinates1[0]
        dy = coordinates2[1] - coordinates1[1]
        return math.hypot(dx, dy)
