import logging
from typing import Tuple, List, Any

import numpy as np
import networkx as nx
from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.logic.synced_traversal_generator import SyncedTraversalGenerator
from src.logic.optimal_path_matcher import OptimalPathMatcher, PathCandidate
from src.utils.distance_matrix_calculator import DistanceMatrixCalculator

from .abstract_strategy import AbstractReductionStrategy

CONCEPT = "concept"
IMAGE = "image"

PROPERTIES_TO_COMPARE = set(["normalized_x", "normalized_y"])

class CornerPointReductionStrategy(AbstractReductionStrategy):
    """Reduces corner points in concept and image graphs to align them.

    This strategy employs a subpath-based reduction process:

    Subpath-Based Reduction:
    - Identifies paths between non-corner critical points (e.g., Start, End,
      Intersection) in both concept and image graphs.
    - Matches corresponding paths between the two graphs.
    - For each matched pair of subpaths:
      - Compares the number of *corner points* specifically within these two subpaths.
      - If the counts differ, it targets the subpath with more corner points.
      - Calculates similarity *only between the corner points of the paired subpaths*.
      - Removes the 'excess' number of corner points from the longer subpath's corner points,
        prioritizing the removal of those with the *lowest* maximum similarity
        to the corner points in the shorter paired subpath.

    The goal is to retain the most relevant and corresponding corner points
    between the concept and image graphs while discarding dissimilar or
    unmatched ones, considering the local context of paths between other
    critical points.

    Handles edge cases such as graphs initially having no corner points or
    one graph having no corner points in a particular subpath.
    """

    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        super().__init__(node_similarity_calculator)
        self.logger = logging.getLogger(__name__)
        self.distance_matrix_calculator = DistanceMatrixCalculator(self.logger)
        self.traversal_generator = SyncedTraversalGenerator(
            critical_point_types={
                CriticalPointType.START_POINT,
                CriticalPointType.END_POINT,
                CriticalPointType.INTERSECTION_POINT,
                # CriticalPointType.CORNER_POINT,
            }
        )

    def reduce(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        concept_corner_points = self._get_corner_points(concept_graph)
        image_corner_points = self._get_corner_points(image_graph)

        # Handle empty graph cases
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

        # Apply subpath-based reduction instead of global similarity-based reduction
        concept_graph, image_graph = self._subpath_based_reduction(
            concept_graph, image_graph
        )

        return concept_graph, image_graph

    def _subpath_based_reduction(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        self.logger.info("Starting subpath-based corner point reduction")

        sync_list = self.traversal_generator.generate_synced_traversal(
            concept_graph, image_graph
        )

        if not sync_list:
            self.logger.warning("No synchronized subpaths found between graphs")
            return concept_graph, image_graph

        segments_data = self._collect_segments_data(
            concept_graph, image_graph, sync_list
        )

        if not segments_data:
            self.logger.warning("No segments with paths found")
            return concept_graph, image_graph

        candidates = self._build_path_candidates(
            concept_graph, image_graph, segments_data
        )

        matcher = OptimalPathMatcher()
        matched = matcher.find_optimal_matches(candidates)

        self.logger.info(f"Optimal matching found {len(matched)} path pairs")

        for concept_path_tuple, image_path_tuple in matched.items():
            concept_path = list(concept_path_tuple)
            image_path = list(image_path_tuple)

            concept_corner_points = self._get_corner_points_in_path(
                concept_graph, concept_path
            )
            image_corner_points = self._get_corner_points_in_path(
                image_graph, image_path
            )

            self._reduce_corner_points_in_subpath(
                concept_graph,
                image_graph,
                concept_corner_points,
                image_corner_points,
            )

        return concept_graph, image_graph

    def _collect_segments_data(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        sync_list: List[List[Tuple[Any, Any]]],
    ) -> List[Tuple[int, List[List[Any]], List[List[Any]]]]:
        segments_data = []
        segment_id = 0

        for subpath in sync_list:
            if len(subpath) < 2:
                continue

            for i in range(len(subpath) - 1):
                start_c, end_c = subpath[i][0], subpath[i + 1][0]
                start_i, end_i = subpath[i][1], subpath[i + 1][1]

                if start_c == end_c and start_i == end_i:
                    self.logger.info(
                        f"Self-loop detected at ({start_c},{start_i}). Finding all cycles."
                    )
                    all_cycles_c = nx.cycle_basis(concept_graph, root=start_c)
                    all_cycles_i = nx.cycle_basis(image_graph, root=start_i)

                    concept_paths = [c for c in all_cycles_c if start_c in c]
                    image_paths = [c for c in all_cycles_i if start_i in c]

                    if not concept_paths or not image_paths:
                        self.logger.warning("No cycle paths found through intersection")
                        continue
                else:
                    concept_paths = list(
                        nx.all_simple_paths(concept_graph, start_c, end_c)
                    )
                    image_paths = list(nx.all_simple_paths(image_graph, start_i, end_i))

                    if not concept_paths or not image_paths:
                        self.logger.warning(
                            f"No paths found between ({start_c},{end_c}) and ({start_i},{end_i})"
                        )
                        continue

                segments_data.append((segment_id, concept_paths, image_paths))
                segment_id += 1

        return segments_data

    def _build_path_candidates(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        segments_data: List[Tuple[int, List[List[Any]], List[List[Any]]]],
    ) -> List[PathCandidate]:
        candidates = []

        for segment_id, concept_paths, image_paths in segments_data:
            for path_c in concept_paths:
                for path_i in image_paths:
                    similarity_matrix = self.calculate_similarity_matrix(
                        concept_graph, image_graph, path_c, path_i, properties_to_compare=PROPERTIES_TO_COMPARE
                    )
                    similarity = self._calculate_path_similarity_score(similarity_matrix)
                    candidates.append(
                        PathCandidate(
                            segment_id=segment_id,
                            concept_path=tuple(path_c),
                            image_path=tuple(path_i),
                            similarity=similarity,
                        )
                    )

        return candidates

    def _calculate_path_similarity_score(self, similarity_matrix: np.ndarray) -> float:
        """Calculate path similarity score based on node similarity matrix."""
        if similarity_matrix.size == 0:
            return 0.0

        # Average the maximum similarities for each node
        max_similarities = np.max(similarity_matrix, axis=1)
        return float(np.mean(max_similarities))

    def _get_corner_points_in_path(self, graph: nx.Graph, path: List[Any]) -> List[Any]:
        """Extract corner points from a path."""
        return [
            node
            for node in path
            if node in graph and GraphUtils.is_corner_point(graph.nodes[node])
        ]

    def _reduce_corner_points_in_subpath(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_corner_points: List[Any],
        image_corner_points: List[Any],
    ) -> None:
        """Reduce excess corner points in the subpath with more corners."""
        len_concept_corner_points = len(concept_corner_points)
        len_image_corner_points = len(image_corner_points)

        self.logger.info(
            f"Corner points in subpath: concept={len_concept_corner_points}, image={len_image_corner_points}"
        )

        if len_concept_corner_points == len_image_corner_points:
            self.logger.info(
                "Concept and image have the same number of corner points in this subpath. No reduction needed."
            )
            return
        
        # Handle empty graph cases
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

        # Calculate distance matrix based on actual coordinate values from PROPERTIES_TO_COMPARE
        distance_matrix = self.distance_matrix_calculator.calculate_distance_matrix(
            graph_large, graph_small, points_large, points_small, PROPERTIES_TO_COMPARE
        )

        # Calculate how many corner points to remove
        difference = abs(len_concept_corner_points - len_image_corner_points)

        # Identify which corner points to remove using Hungarian algorithm
        points_to_remove = self.distance_matrix_calculator.find_points_for_difference(
            distance_matrix, points_large, difference
        )

        if points_to_remove:
            self.logger.info(
                f"Removing {len(points_to_remove)} corner points from {graph_to_reduce} graph in subpath"
            )

            # Apply the reduction
            if graph_to_reduce == CONCEPT:
                concept_graph = self._apply_reduction(concept_graph, points_to_remove)
            else:
                image_graph = self._apply_reduction(image_graph, points_to_remove)

    def _get_corner_points(self, graph: nx.Graph) -> List[Any]:
        """Get all corner points in a graph."""
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_corner_point(data)
        ]

    def _apply_reduction(self, graph: nx.Graph, nodes: List[Any]) -> nx.Graph:
        """Remove the corner point label from specified nodes."""
        for node in nodes:
            if node in graph:
                labels = graph.nodes[node]["labels"]
                if CriticalPointType.CORNER_POINT.value in labels:
                    labels.remove(CriticalPointType.CORNER_POINT.value)
                    graph.nodes[node]["labels"] = labels
        return graph
