import logging
import math
from typing import Optional, List, Tuple
import networkx as nx

from model.point import Point
from logic.graph_traversal import GraphTraversal
from visitors.visitor import Visitor
from model.vector import Vector

class NetworkxGraphAnalysis:
    def __init__(self, graph: nx.Graph):
        self.graph = graph
        self.visitors: List[Visitor] = []
        self.graph_traversal = GraphTraversal(self.graph)

    def add_visitor(self, visitor: Visitor):
        self.visitors.append(visitor)

    def analyze_graph(self):
        top_leftmost_point = self.find_top_leftmost_point()
        
        for node in self.graph_traversal.dfs_traversal(top_leftmost_point):
            node_data = self.graph.nodes[node]
            for visitor in self.visitors:
                visitor.visit_point(node_data)
            
            for neighbor in self.graph.neighbors(node):
                edge_data = self.graph[node][neighbor]
                segment_id = edge_data.get('segment_id', '')

                source_node = self.graph.nodes[node]
                target_node = self.graph.nodes[neighbor]

                x1 = source_node['x']
                y1 = source_node['y']
                x2 = target_node['x']
                y2 = target_node['y']
                
                length = self.calculate_length((x1, y1), (x2, y2))
                
                vector = Vector(
                    id=segment_id,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    length=length
                )
                
                for visitor in self.visitors:
                    visitor.visit_line(vector)

    def find_top_leftmost_point(self) -> Optional[Point]:
        """
        Finds the top-leftmost point in the graph based on x and y coordinates.

        Args:
            graph (nx.Graph): The contour graph.

        Returns:
            Optional[Point]: The top-leftmost point or None if the graph is empty.
        """
        points = [data | {"id": node} for node, data in self.graph.nodes(data=True)]
        if not points:
            return None
        # Sort points first by y ascending (top), then by x ascending (left)
        top_leftmost = min(points, key=lambda p: 2 * p["x"] + p["y"])
        return Point(
            x=top_leftmost["x"], y=top_leftmost["y"], id=str(top_leftmost["id"])
        )
        
    def calculate_length(self, coordinates1: Tuple[float, float], coordinates2: Tuple[float, float]) -> float:
        dx = coordinates2[0] - coordinates1[0]
        dy = coordinates2[1] - coordinates1[1]
        return math.hypot(dx, dy)
