from abc import ABC, abstractmethod
from typing import Tuple, List, Any
from node_similarity_calculator import NodeSimilarityCalculator
import numpy as np
import networkx as nx
import logging

class AbstractReductionStrategy(ABC):

    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        self.node_similarity_calculator = node_similarity_calculator
        self.logger = logging.getLogger(__name__)
        self.properties_to_compare = set(
            ["normalized_x", "normalized_y", "relative_distance"]
        )

    @abstractmethod
    def reduce(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
    ) -> Tuple[nx.Graph, nx.Graph]:
        pass

    def calculate_similarity_matrix(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_nodes: List[Any],
        image_nodes: List[Any],
    ) -> np.ndarray:
        similarity_matrix = np.zeros((len(concept_nodes), len(image_nodes)))
        for i, concept_node in enumerate(concept_nodes):
            for j, image_node in enumerate(image_nodes):
                similarity = self.node_similarity_calculator.calculate_node_similarity(
                    concept_graph,
                    image_graph,
                    concept_node,
                    image_node,
                    self.properties_to_compare,
                )
                self.logger.info(f"Similarity between {concept_node} and {image_node}: {similarity}")
                similarity_matrix[i, j] = similarity
        return similarity_matrix
