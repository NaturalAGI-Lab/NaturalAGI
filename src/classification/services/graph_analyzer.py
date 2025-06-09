import logging
from typing import List
from common.traversal.graph_traversal import GraphTraversal
from common.traversal.visitors import Visitor
import networkx as nx
from common.decorator import timed


class GraphAnalyzer:
    """
    Traverse the graph from the selected start point and creates comparison features between structural elements.
    The features are used to create a concept.
    """

    def __init__(
        self,
        graph: nx.Graph,
        visitors: List[Visitor],
    ):
        self.graph = graph
        self.visitors = visitors
        self.graph_traversal = None
        self.logger = logging.getLogger(__name__)

    def analyze(self):
        self.graph_traversal = GraphTraversal(self.graph)
        self._perform_traversal()

    @timed(label="perform_traversal")
    def _perform_traversal(self):
        start_point = self.graph.graph["start_point"]

        if start_point is None:
            raise ValueError("Start point is not set")

        for traversal_sequence in self.graph_traversal.dfs_traversal(start_point):
            start_point = traversal_sequence.start_point
            vector = traversal_sequence.vector
            end_point = traversal_sequence.end_point
            self.logger.info(
                f"Point: {start_point}, Vector: {vector}, End point: {end_point}"
            )
            visited_points = set()
            for visitor in self.visitors:
                visitor.visit_line(vector, start_point)
                if start_point.id not in visited_points:
                    visitor.visit_point(start_point)
                    visited_points.add(start_point.id)
                if end_point.id not in visited_points:
                    visitor.visit_point(end_point)
                    visited_points.add(end_point.id)
