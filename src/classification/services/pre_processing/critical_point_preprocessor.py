import logging
import copy
import networkx as nx
from typing import Tuple

from common import CriticalGraphUtils, GraphUtils
from reduction_strategy.endpoint_strategy import EndpointReductionStrategy
from reduction_strategy.intersection_strategy import IntersectionPointReductionStrategy
from reduction_strategy.corner_point_reduction_strategy import (
    CornerPointReductionStrategy,
)


class CriticalPointPreprocessor:
    """
    Preprocesses graphs to ensure they have compatible critical points before graph minor matching.
    This class handles reduction and removal of critical points to ensure compatibility.
    """

    def __init__(
        self,
        endpoint_reduction_strategy: EndpointReductionStrategy,
        intersection_reduction_strategy: IntersectionPointReductionStrategy,
        corner_point_reduction_strategy: CornerPointReductionStrategy,
        max_iterations: int = 5,
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.endpoint_reduction_strategy = endpoint_reduction_strategy
        self.intersection_reduction_strategy = intersection_reduction_strategy
        self.corner_point_reduction_strategy = corner_point_reduction_strategy
        self.max_iterations = max_iterations

    def preprocess_graphs(
        self, inference_graph: nx.Graph, concept_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Preprocess two graphs to ensure they have compatible critical points.

        Args:
            inference_graph: Graph to preprocess
            concept_graph: Graph to preprocess

        Returns:
            Tuple of (preprocessed_inference_graph, preprocessed_concept_graph)
        """
        self.logger.info("Preprocessing graphs for critical point compatibility")

        # Create copies to avoid modifying original graphs
        inference_graph = copy.deepcopy(inference_graph)
        concept_graph = copy.deepcopy(concept_graph)

        # Extract critical points from both graphs
        inference_critical_graph, _ = CriticalGraphUtils.get_critical_graph(
            inference_graph
        )
        concept_critical_graph, _ = CriticalGraphUtils.get_critical_graph(concept_graph)

        is_isomorphic = GraphUtils.is_graph_isomorphic(
            inference_critical_graph, concept_critical_graph
        )

        if is_isomorphic:
            self.logger.info(
                "Critical point graphs are isomorphic, no reductions needed"
            )
            return inference_graph, concept_graph

        self.logger.info(
            "Critical point graphs are not isomorphic, applying reductions..."
        )
        self.logger.info(f"Initial critical graph 1: {inference_critical_graph.nodes}")
        self.logger.info(f"Initial critical graph 2: {concept_critical_graph.nodes}")

        # Apply graph reduction to make graphs isomorphic
        inference_graph, concept_graph = self._reduce_graphs_for_isomorphism(
            inference_graph,
            concept_graph,
            inference_critical_graph,
            concept_critical_graph,
        )

        return inference_graph, concept_graph

    def _reduce_graphs_for_isomorphism(
        self,
        inference_graph: nx.Graph,
        concept_graph: nx.Graph,
        inference_critical_graph: nx.Graph,
        concept_critical_graph: nx.Graph,
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Iteratively reduce image graph until its critical point structures become isomorphic to concept graph.
        This method modifies the original image graph.

        Args:
            inference_graph: Graph to preprocess
            concept_graph: Graph to compare to
            inference_critical_graph: Critical graph of inference graph
            concept_critical_graph: Critical graph of concept graph

        Returns:
            Tuple of (reduced_inference_graph, concept_graph)
        """
        # Iterate until critical point graphs are isomorphic or no more reductions can be made
        for i in range(self.max_iterations):
            self.logger.info(f"Iteration {i+1} of {self.max_iterations}")
            self.logger.info(
                f"Inference critical graph: {inference_critical_graph.nodes}"
            )
            self.logger.info(f"Concept critical graph: {concept_critical_graph.nodes}")

            # Apply endpoint reduction
            inference_graph, concept_graph = self.endpoint_reduction_strategy.reduce(
                image_graph=inference_graph,
                concept_graph=concept_graph,
            )

            # Apply intersection reduction
            inference_graph, concept_graph = (
                self.intersection_reduction_strategy.reduce(
                    image_graph=inference_graph,
                    concept_graph=concept_graph,
                )
            )

            # Apply corner point reduction
            inference_graph, concept_graph = (
                self.corner_point_reduction_strategy.reduce(
                    image_graph=inference_graph,
                    concept_graph=concept_graph,
                )
            )

            # Extract critical points from both graphs
            inference_critical_graph, _ = CriticalGraphUtils.get_critical_graph(
                inference_graph
            )
            concept_critical_graph, _ = CriticalGraphUtils.get_critical_graph(
                concept_graph
            )

            is_isomorphic = GraphUtils.is_graph_isomorphic(
                inference_critical_graph, concept_critical_graph
            )

            if is_isomorphic:
                self.logger.info("Critical point graphs are isomorphic, stopping")
                return inference_graph, concept_graph

        raise ValueError("Reached maximum reduction iterations, stopping")
