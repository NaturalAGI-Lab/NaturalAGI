import logging
import networkx as nx
import os
import copy
from typing import Tuple
from common import CriticalGraphUtils, GraphUtils
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.reduction_strategy.endpoint_strategy import EndpointReductionStrategy
from src.reduction_strategy.intersection_strategy import (
    IntersectionPointReductionStrategy,
)
from src.reduction_strategy.corner_point_reduction_strategy import (
    CornerPointReductionStrategy,
)
from src.utils.graph_saver import GraphSaver


class CriticalPointPreprocessor:
    """
    Preprocesses graphs to ensure they have compatible critical points before graph minor matching.
    This class handles reduction and removal of critical points to ensure compatibility.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.similarity_calculator = NodeSimilarityCalculator()
        self.endpoint_reduction_strategy = EndpointReductionStrategy(
            self.similarity_calculator
        )
        self.intersection_reduction_strategy = IntersectionPointReductionStrategy(
            self.similarity_calculator
        )
        self.corner_point_reduction_strategy = CornerPointReductionStrategy(
            self.similarity_calculator
        )
        self.properties_to_compare = set(
            ["normalized_x", "normalized_y", "relative_distance"]
        )

    def preprocess_graphs(
        self, graph1: nx.Graph, graph2: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Preprocess two graphs to ensure they have compatible critical points.
        This method modifies the original graphs until their critical point structures become isomorphic.

        Args:
            graph1: First graph to preprocess
            graph2: Second graph to preprocess

        Returns:
            Tuple of (preprocessed_graph1, preprocessed_graph2) - the modified original graphs
        """
        # Make copies of the original graphs to avoid modifying the input graphs directly
        graph1_mod = copy.deepcopy(graph1)
        graph2_mod = copy.deepcopy(graph2)

        # Extract critical point graphs for initial isomorphism check
        crit_graph1, _ = CriticalGraphUtils.get_critical_graph(graph1_mod)
        crit_graph2, _ = CriticalGraphUtils.get_critical_graph(graph2_mod)

        is_isomorphic = GraphUtils.is_graph_isomorphic(crit_graph1, crit_graph2)

        if not is_isomorphic:
            self.logger.info(
                "Critical point graphs are not isomorphic, applying reductions..."
            )
            self.logger.info(f"Initial critical graph 1: {crit_graph1.nodes}")
            self.logger.info(f"Initial critical graph 2: {crit_graph2.nodes}")

            # Apply graph reduction to make graphs isomorphic
            graph1_mod, graph2_mod = self._reduce_graphs_for_isomorphism(
                graph1_mod, graph2_mod, crit_graph1, crit_graph2
            )
        else:
            self.logger.info(
                "Critical point graphs are isomorphic, no reductions needed"
            )

        return graph1_mod, graph2_mod

    def _reduce_graphs_for_isomorphism(
        self,
        graph1: nx.Graph,
        graph2: nx.Graph,
        crit_graph1: nx.Graph,
        crit_graph2: nx.Graph,
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Iteratively reduce graphs until their critical point structures become isomorphic.
        This method modifies the original graphs.

        Args:
            graph1: First graph
            graph2: Second graph

        Returns:
            Tuple of (reduced_graph1, reduced_graph2)
        """
        iteration = 0
        # Iterate until critical point graphs are isomorphic or no more reductions can be made
        while not GraphUtils.is_graph_isomorphic(crit_graph1, crit_graph2):

            # Step 1: Apply endpoints reduction
            graph1, graph2 = self.endpoint_reduction_strategy.reduce(graph1, graph2)
            # Step 2: Apply intersection reduction
            graph1, graph2 = self.intersection_reduction_strategy.reduce(graph1, graph2)
            # Step 3: Apply corner point reduction
            graph1, graph2 = self.corner_point_reduction_strategy.reduce(graph1, graph2)
            crit_graph1, _ = CriticalGraphUtils.get_critical_graph(graph1)
            crit_graph2, _ = CriticalGraphUtils.get_critical_graph(graph2)
            self.save_graphs(graph1, graph2, crit_graph1, crit_graph2, iteration)
            iteration += 1
            # To prevent infinite loops, limit the number of iterations
            if iteration > 5:  # arbitrary limit
                self.logger.warning("Reached maximum reduction iterations, stopping")
                raise ValueError("Reached maximum reduction iterations, stopping")

        return graph1, graph2

    def save_graphs(
        self,
        graph1: nx.Graph,
        graph2: nx.Graph,
        crit_graph1: nx.Graph,
        crit_graph2: nx.Graph,
        iteration: int,
    ):
        save_dir = f"saved_graphs/{iteration}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Convert the graph to a JSON-serializable format
        GraphSaver.save_graph_json(graph1, os.path.join(save_dir, "graph1.json"))
        GraphSaver.save_graph_json(graph2, os.path.join(save_dir, "graph2.json"))
        GraphSaver.save_graph_json(
            crit_graph1, os.path.join(save_dir, "crit_graph1.json")
        )
        GraphSaver.save_graph_json(
            crit_graph2, os.path.join(save_dir, "crit_graph2.json")
        )
