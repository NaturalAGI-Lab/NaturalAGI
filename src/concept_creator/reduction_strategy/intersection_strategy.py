import logging
from typing import Any, List, Tuple
from .abstract_strategy import AbstractReductionStrategy
from utils.graph_utils import GraphUtils
from node_similarity_calculator import NodeSimilarityCalculator
import numpy as np
from model.critical_point import CriticalPointType
import networkx as nx


class IntersectionPointReductionStrategy(AbstractReductionStrategy):

    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        self.node_similarity_calculator = node_similarity_calculator
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = 0.5

    def reduce(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        concept_graph = self._apply_degree_reduction(concept_graph)
        image_graph = self._apply_degree_reduction(image_graph)
        return concept_graph, image_graph

    def _apply_degree_reduction(self, graph: nx.Graph) -> nx.Graph:
        for node, data in graph.nodes(data=True):
            if GraphUtils.is_intersection_point(data):
                if not graph.degree(node) > 2:
                    self.logger.info(f"Removing IntersectionPoint label from {node} with degree {graph.degree(node)}")
                    labels = graph.nodes[node]["labels"]
                    labels.remove(CriticalPointType.INTERSECTION_POINT.value)
                    graph.nodes[node]["labels"] = labels
        return graph

    def _get_intersection_points(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_intersection_point(data)
        ]
