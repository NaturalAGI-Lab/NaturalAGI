import math
from typing import Optional, List, Tuple, Any, Type
import networkx as nx

from logic.graph_traversal import GraphTraversal
from service.visitor_result_persistence_service import VisitorResultPersistenceService
from service.analysis_result_persistence_service import AnalysisResultPersistenceService
from service.graph_analysis.analyzers.base_analyzer import BaseAnalyzer
from visitors.visitor import Visitor


class NetworkxGraphAnalysis:
    def __init__(
        self,
        graph: nx.Graph,
        visitor_result_persistence_service: VisitorResultPersistenceService,
        analysis_result_persistence_service: AnalysisResultPersistenceService,
    ):
        self.graph = graph
        self.visitors: List[Visitor] = []
        self.analyzers: List[BaseAnalyzer] = []
        self.graph_traversal = GraphTraversal(self.graph)
        self.visitor_result_persistence_service = visitor_result_persistence_service
        self.analysis_result_persistence_service = analysis_result_persistence_service

    def add_visitor(self, visitor: Visitor):
        self.visitors.append(visitor)

    def add_analyzer(self, analyzer_class: Type[BaseAnalyzer]):
        analyzer = analyzer_class(self.graph)
        self.analyzers.append(analyzer)

    def analyze_graph(self, image_id: str, session_id: str):
        print("Starting graph analysis with visitors: ", [type(visitor).__name__ for visitor in self.visitors])
        print("Starting graph analysis with analyzers: ", [type(analyzer).__name__ for analyzer in self.analyzers])
        # Graph traversal
        self.perform_graph_traversal(image_id, session_id)

        # Graph exposition analysis
        for analyzer in self.analyzers:
            result = analyzer.analyze()
            self.analysis_result_persistence_service.save_analysis_result(
                analyzer, result, image_id, session_id
            )

    def perform_graph_traversal(self, image_id: str, session_id: str):
        top_leftmost_point = self.find_top_leftmost_point()

        for point, vector in self.graph_traversal.dfs_traversal(top_leftmost_point):
            print(f"Node: {point}, Edge: {vector}")
            for visitor in self.visitors:
                result = visitor.visit_point(point)
                if result:
                    self.visitor_result_persistence_service.save_visitor_result(
                        visitor, result, image_id, session_id
                    )

            if vector:
                for visitor in self.visitors:
                    result = visitor.visit_line(vector)
                    if result:
                        self.visitor_result_persistence_service.save_visitor_result(
                            visitor, result, image_id, session_id
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
            [node for node in self.graph.nodes if self.graph.degree[node] == 1],
            key=lambda n: (self.graph.nodes[n]["x"] + self.graph.nodes[n]["y"]),
        )
        return top_leftmost_node

    def calculate_length(
        self, coordinates1: Tuple[float, float], coordinates2: Tuple[float, float]
    ) -> float:
        dx = coordinates2[0] - coordinates1[0]
        dy = coordinates2[1] - coordinates1[1]
        return math.hypot(dx, dy)
