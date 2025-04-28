import logging
from typing import Tuple, List, Any, Dict, Set

import numpy as np
import networkx as nx
from node_similarity_calculator import NodeSimilarityCalculator
from utils.graph_utils import GraphUtils
from model.critical_point import CriticalPointType
from logic.synced_traversal_generator import SyncedTraversalGenerator

from .abstract_strategy import AbstractReductionStrategy

CONCEPT = "concept"
IMAGE = "image"


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
        """Reduces corner points based on matched subpaths between critical points."""
        self.logger.info("Starting subpath-based corner point reduction")

        # Generate critical point matching between graphs
        sync_list = self.traversal_generator.generate_synced_traversal(
            concept_graph, image_graph
        )

        if not sync_list:
            self.logger.warning("No synchronized subpaths found between graphs")
            return concept_graph, image_graph

        # Process each subpath between matched critical points
        for subpath in sync_list:
            if len(subpath) < 2:  # Need at least two critical points for a path
                continue

            self.logger.info(f"Processing subpath: {subpath}")

            # Process each segment between consecutive critical points
            for i in range(len(subpath) - 1):
                start_c, end_c = subpath[i][0], subpath[i + 1][0]
                start_i, end_i = subpath[i][1], subpath[i + 1][1]

                self.logger.info(
                    f"Processing segment between: ({start_c},{start_i}) and ({end_c},{end_i})"
                )

                if start_c == end_c and start_i == end_i:
                    self.logger.info(
                        f"Self-loop detected between: ({start_c},{start_i}) and ({end_c},{end_i}). Trying to find cycle paths."
                    )
                    cycle_paths_c = list(nx.find_cycle(concept_graph, start_c, end_c))
                    cycle_paths_i = list(nx.find_cycle(image_graph, start_i, end_i))

                    if not cycle_paths_c or not cycle_paths_i:
                        self.logger.warning(
                            f"No cycle paths found between critical points"
                        )
                        continue
                    concept_paths = [[edge[0] for edge in cycle_paths_c]]
                    image_paths = [[edge[0] for edge in cycle_paths_i]]
                else:
                    # Get all paths between these critical points
                    concept_paths = list(
                        nx.all_simple_paths(concept_graph, start_c, end_c)
                    )
                    image_paths = list(nx.all_simple_paths(image_graph, start_i, end_i))

                    if not concept_paths or not image_paths:
                        self.logger.warning(f"No paths found between critical points")
                        continue

                # Find best matching paths
                best_concept_path, best_image_path = self._find_best_matching_paths(
                    concept_graph, image_graph, concept_paths, image_paths
                )

                # Extract corner points from these paths
                concept_corner_points = self._get_corner_points_in_path(
                    concept_graph, best_concept_path
                )
                image_corner_points = self._get_corner_points_in_path(
                    image_graph, best_image_path
                )

                # Reduce excess corner points in the subpath with more corner points
                self._reduce_corner_points_in_subpath(
                    concept_graph,
                    image_graph,
                    concept_corner_points,
                    image_corner_points,
                )

        return concept_graph, image_graph

    def _find_best_matching_paths(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_paths: List[List[Any]],
        image_paths: List[List[Any]],
    ) -> Tuple[List[Any], List[Any]]:
        """Find the best matching paths between two sets of paths using node similarity."""
        best_score = -1
        best_pair = (concept_paths[0], image_paths[0])  # Default to first paths

        # Compare each path pair and find the one with highest similarity
        for path_c in concept_paths:
            for path_i in image_paths:
                # Calculate similarity matrix between the paths
                similarity_matrix = self.calculate_similarity_matrix(
                    concept_graph, image_graph, path_c, path_i
                )

                # Calculate overall path similarity score (average of maximum similarities per row)
                path_score = self._calculate_path_similarity_score(similarity_matrix)

                if path_score > best_score:
                    best_score = path_score
                    best_pair = (path_c, path_i)
                    self.logger.debug(
                        f"New best path pair found with score {best_score:.3f}"
                    )

        self.logger.info(f"Best path pair found with score {best_score:.3f}")
        return best_pair

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

        # Calculate similarity only between corner points of the two subpaths
        similarity_matrix = self.calculate_similarity_matrix(
            graph_large, graph_small, points_large, points_small
        )

        # Calculate how many corner points to remove
        difference = abs(len_concept_corner_points - len_image_corner_points)

        # Identify which corner points to remove
        points_to_remove = self._identify_corner_points_to_remove(
            similarity_matrix, points_large, difference
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

    def _identify_corner_points_to_remove(
        self, similarity_matrix: np.ndarray, nodes: List[Any], difference: int
    ) -> List[Any]:
        """Identify corner points to remove based on similarity scores."""
        if difference <= 0:
            return []

        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        # Find the maximum similarity for each corner point in the larger set
        max_similarities_per_large_point = np.max(similarity_matrix, axis=1)

        # Create a list of (index_in_large_list, max_similarity)
        indexed_similarities = list(enumerate(max_similarities_per_large_point))

        # Sort by max_similarity in ascending order (lowest similarity first)
        indexed_similarities.sort(key=lambda x: x[1])

        # Get the indices of the 'difference' points with the lowest similarity
        indices_to_remove = [idx for idx, sim in indexed_similarities[:difference]]

        # Get the actual node IDs corresponding to these indices
        nodes_to_remove = [nodes[i] for i in indices_to_remove]

        self.logger.debug(f"Nodes identified for removal: {nodes_to_remove}")
        return nodes_to_remove

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
