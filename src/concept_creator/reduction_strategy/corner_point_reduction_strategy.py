import logging
from typing import Tuple, List, Any

import numpy as np
import networkx as nx
from node_similarity_calculator import NodeSimilarityCalculator
from utils.graph_utils import GraphUtils
from model.critical_point import CriticalPointType

from .abstract_strategy import AbstractReductionStrategy

CONCEPT = "concept"
IMAGE = "image"


class CornerPointReductionStrategy(AbstractReductionStrategy):
    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        super().__init__(node_similarity_calculator)
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = 0.2

    def reduce(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        concept_corner_points = self._get_corner_points(concept_graph)
        image_corner_points = self._get_corner_points(image_graph)

        if not concept_corner_points and not image_corner_points:
            self.logger.info(
                "No corner points found in either graph. Returning original graphs."
            )
            return concept_graph, image_graph

        if not concept_corner_points and image_corner_points:
            self.logger.info(
                "No corner points found in concept graph. Reducing all corner points in image graph."
            )
            image_graph = self._apply_reduction(image_graph, image_corner_points)
            return concept_graph, image_graph

        if concept_corner_points and not image_corner_points:
            self.logger.info(
                "No corner points found in image graph. Reducing all corner points in concept graph."
            )
            concept_graph = self._apply_reduction(concept_graph, concept_corner_points)
            return concept_graph, image_graph

        similarity_matrix = self.calculate_similarity_matrix(
            concept_graph, image_graph, concept_corner_points, image_corner_points
        )

        concept_corner_points_below_threshold = (
            self._find_corner_points_below_threshold(
                similarity_matrix, concept_corner_points, axis=1
            )
        )
        image_corner_points_below_threshold = self._find_corner_points_below_threshold(
            similarity_matrix.T, image_corner_points, axis=1
        )

        if concept_corner_points_below_threshold:
            self.logger.info(
                f"Concept corner points below threshold ({len(concept_corner_points_below_threshold)}): {concept_corner_points_below_threshold}"
            )
            concept_graph = self._apply_reduction(
                concept_graph, concept_corner_points_below_threshold
            )

        if image_corner_points_below_threshold:
            self.logger.info(
                f"Image corner points below threshold ({len(image_corner_points_below_threshold)}): {image_corner_points_below_threshold}"
            )
            image_graph = self._apply_reduction(
                image_graph, image_corner_points_below_threshold
            )

        concept_corner_points = self._get_corner_points(concept_graph)
        image_corner_points = self._get_corner_points(image_graph)

        # --- Handle cases where first reduction removed all corner points ---
        if not concept_corner_points and not image_corner_points:
            self.logger.info(
                "No corner points remain in either graph after threshold reduction. Returning."
            )
            return concept_graph, image_graph

        if not concept_corner_points:
            self.logger.info(
                "No corner points left in concept graph. Removing all remaining corner points from image graph."
            )
            image_graph = self._apply_reduction(image_graph, image_corner_points)
            # Now both have 0 corner points, counts match.
            return concept_graph, image_graph

        if not image_corner_points:
            self.logger.info(
                "No corner points left in image graph. Removing all remaining corner points from concept graph."
            )
            concept_graph = self._apply_reduction(concept_graph, concept_corner_points)
            # Now both have 0 corner points, counts match.
            return concept_graph, image_graph

        len_concept_corner_points = len(concept_corner_points)
        len_image_corner_points = len(image_corner_points)

        if len_concept_corner_points == len_image_corner_points:
            self.logger.info(
                "Concept and image have the same number of corner points. No reduction needed."
            )
            return concept_graph, image_graph

        if len_concept_corner_points > len_image_corner_points:
            graph_large = concept_graph
            graph_small = image_graph
            points_large = concept_corner_points
            points_small = image_corner_points
            graph_to_reduce = CONCEPT
        else:
            graph_large = image_graph
            graph_small = concept_graph
            points_large = image_corner_points
            points_small = concept_corner_points
            graph_to_reduce = IMAGE

        similarity_matrix = self.calculate_similarity_matrix(
            graph_large, graph_small, points_large, points_small
        )

        excess_corner_points_to_reduce = self._identify_excess_corner_points_to_reduce(
            similarity_matrix,
            points_large,
            abs(len_concept_corner_points - len_image_corner_points),
        )

        if excess_corner_points_to_reduce:
            self.logger.info(
                f"Excess corner points to reduce ({len(excess_corner_points_to_reduce)}): {excess_corner_points_to_reduce}"
            )

            if graph_to_reduce == CONCEPT:
                concept_graph = self._apply_reduction(
                    concept_graph, excess_corner_points_to_reduce
                )
            else:
                image_graph = self._apply_reduction(
                    image_graph, excess_corner_points_to_reduce
                )

        return concept_graph, image_graph

    def _get_corner_points(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_corner_point(data)
        ]

    def _find_corner_points_below_threshold(
        self, similarity_matrix: np.ndarray, nodes: List[Any], axis: int
    ) -> List[Any]:
        corner_points_below_threshold = []
        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        for i, node in enumerate(nodes):
            if np.all(similarity_matrix[i, :] < self.similarity_threshold):
                self.logger.info(
                    f"Corner point {node} below threshold ({similarity_matrix[i, :]})"
                )
                corner_points_below_threshold.append(node)
        return corner_points_below_threshold

    def _apply_reduction(self, graph: nx.Graph, nodes: List[Any]) -> nx.Graph:
        for node in nodes:
            if node in graph:
                labels = graph.nodes[node]["labels"]
                labels.remove(CriticalPointType.CORNER_POINT.value)
                graph.nodes[node]["labels"] = labels
        return graph

    def _identify_excess_corner_points_to_reduce(
        self, similarity_matrix: np.ndarray, nodes: List[Any], difference: int
    ) -> List[Any]:
        if difference <= 0:
            self.logger.error("Difference is less than or equal to 0. Raising error.")
            raise ValueError("Difference is less than or equal to 0.")

        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        # Find the maximum similarity for each endpoint in the larger set (each row in the matrix)
        max_similarities_per_large_endpoint = np.max(similarity_matrix, axis=1)

        # Create a list of (index_in_large_list, max_similarity)
        indexed_similarities = list(enumerate(max_similarities_per_large_endpoint))

        # Sort by max_similarity in ascending order (lowest similarity first)
        indexed_similarities.sort(key=lambda x: x[1])

        # Get the indices of the 'difference' endpoints with the lowest max similarity
        indices_to_remove = [idx for idx, sim in indexed_similarities[:difference]]

        # Get the actual node IDs corresponding to these indices
        nodes_to_remove = [nodes[i] for i in indices_to_remove]

        self.logger.debug(
            f"Indices identified for removal based on lowest max similarity: {indices_to_remove}"
        )
        self.logger.debug(f"Nodes identified for removal: {nodes_to_remove}")

        return nodes_to_remove
