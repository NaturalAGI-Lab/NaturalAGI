import logging
from typing import Tuple, List, Any

import numpy as np
import networkx as nx
from scipy.optimize import linear_sum_assignment
from node_similarity_calculator import NodeSimilarityCalculator
from common.graph_utils import GraphUtils
from common.critical_point import CriticalPointType
from services.synced_traversal_service import SyncedTraversalService
from optimal_path_matcher import OptimalPathMatcher, PathCandidate
from graph_similarity.cost_functions import node_subst_cost

from .abstract_strategy import AbstractReductionStrategy

PROPERTIES_TO_COMPARE = set(["normalized_x", "normalized_y"])


class CornerPointReductionStrategy(AbstractReductionStrategy):
    """
    This is basically the same as the corner point reduction strategy in the concept creator,
    but with the difference that we apply it to the image graph.
    """

    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        super().__init__(node_similarity_calculator)
        self.logger = logging.getLogger(__name__)
        self.traversal_service = SyncedTraversalService(
            critical_point_types={
                CriticalPointType.START_POINT,
                CriticalPointType.END_POINT,
                CriticalPointType.INTERSECTION_POINT,
                # CriticalPointType.CORNER_POINT,
            }
        )

    def reduce(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
    ) -> Tuple[nx.Graph, nx.Graph]:
        concept_corner_points = self._get_corner_points(concept_graph)
        image_corner_points = self._get_corner_points(image_graph)

        # Handle empty graph cases
        if not concept_corner_points and not image_corner_points:
            self.logger.info(
                "No corner points found in either graph. Returning original graphs."
            )
            return image_graph, concept_graph

        if not concept_corner_points and image_corner_points:
            self.logger.info(
                "No corner points found in concept graph. Reducing all corner points in image graph."
            )
            image_graph = self._apply_reduction(image_graph, image_corner_points)
            return image_graph, concept_graph

        if concept_corner_points and not image_corner_points:
            raise ValueError("Concept has corner points but image does not.")

        # Apply subpath-based reduction instead of global similarity-based reduction
        image_graph, concept_graph = self._subpath_based_reduction(
            image_graph=image_graph,
            concept_graph=concept_graph,
        )

        return image_graph, concept_graph

    def _subpath_based_reduction(
        self, image_graph: nx.Graph, concept_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        self.logger.info("Starting subpath-based corner point reduction")

        sync_list = self.traversal_service.generate_synced_traversal(
            G_c=concept_graph, G_i=image_graph
        )

        if not sync_list:
            self.logger.warning("No synchronized subpaths found between graphs")
            return image_graph, concept_graph

        segments_data = self._collect_segments_data(
            concept_graph, image_graph, sync_list
        )

        if not segments_data:
            self.logger.warning("No segments with paths found")
            return image_graph, concept_graph

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
                image_graph=image_graph,
                concept_graph=concept_graph,
                image_corner_points=image_corner_points,
                concept_corner_points=concept_corner_points,
            )

        return image_graph, concept_graph

    def _collect_segments_data(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        sync_list: List,
    ) -> List[Tuple[int, List[List[Any]], List[List[Any]]]]:
        segments_data = []
        segment_id = 0

        for subpath in sync_list:
            if len(subpath) < 2:
                continue

            self.logger.info(f"Processing subpath: {subpath}")

            for i in range(len(subpath) - 1):
                start_c, end_c = subpath[i][0], subpath[i + 1][0]
                start_i, end_i = subpath[i][1], subpath[i + 1][1]

                self.logger.info(
                    f"Processing segment between: ({start_c},{start_i}) and ({end_c},{end_i})"
                )

                if start_c == end_c and start_i == end_i:
                    self.logger.info(
                        f"Self-loop detected at ({start_c},{start_i}). Finding all cycles."
                    )
                    all_cycles_c = nx.cycle_basis(concept_graph, root=start_c)
                    all_cycles_i = nx.cycle_basis(image_graph, root=start_i)

                    concept_paths = [c for c in all_cycles_c if start_c in c]
                    image_paths = [c for c in all_cycles_i if start_i in c]

                    if not concept_paths or not image_paths:
                        self.logger.warning(
                            "No cycle paths found through intersection"
                        )
                        continue
                else:
                    concept_paths = list(
                        nx.all_simple_paths(concept_graph, start_c, end_c)
                    )
                    image_paths = list(
                        nx.all_simple_paths(image_graph, start_i, end_i)
                    )

                    if not concept_paths or not image_paths:
                        self.logger.warning(
                            f"No paths found between critical points"
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
                        concept_graph,
                        image_graph,
                        path_c,
                        path_i,
                        properties_to_compare=PROPERTIES_TO_COMPARE,
                    )
                    similarity = self._calculate_path_similarity_score(
                        similarity_matrix
                    )
                    candidates.append(
                        PathCandidate(
                            segment_id=segment_id,
                            concept_path=tuple(path_c),
                            image_path=tuple(path_i),
                            similarity=similarity,
                        )
                    )

        return candidates

    def _calculate_path_similarity_score(
        self, similarity_matrix: np.ndarray
    ) -> float:
        if similarity_matrix.size == 0:
            return 0.0

        max_similarities = np.max(similarity_matrix, axis=1)
        return float(np.mean(max_similarities))

    def _get_corner_points_in_path(
        self, graph: nx.Graph, path: List[Any]
    ) -> List[Any]:
        return [
            node
            for node in path
            if node in graph and GraphUtils.is_corner_point(graph.nodes[node])
        ]

    def _reduce_corner_points_in_subpath(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        image_corner_points: List[Any],
        concept_corner_points: List[Any],
    ) -> None:
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

        if not concept_corner_points and not image_corner_points:
            self.logger.info(
                "No corner points found in either graph. Returning original graphs."
            )
            return

        if not concept_corner_points and image_corner_points:
            self.logger.info(
                "No corner points found in concept graph. Reducing all corner points in image graph."
            )
            self._apply_reduction(image_graph, image_corner_points)
            return

        if concept_corner_points and not image_corner_points:
            raise ValueError("Concept has corner points but image does not.")

        if len_concept_corner_points > len_image_corner_points:
            raise ValueError("Concept has more corner points than image.")
        else:
            graph_large = image_graph
            graph_small = concept_graph
            points_large = image_corner_points
            points_small = concept_corner_points

        cost_matrix = self._corner_substitution_cost_matrix(
            image_nodes=points_large,
            concept_nodes=points_small,
            image_graph=graph_large,
            concept_graph=graph_small,
        )

        points_to_remove = self._identify_corner_points_to_remove(
            cost_matrix, points_large
        )

        if points_to_remove:
            self.logger.info(
                f"Removing {len(points_to_remove)} corner points from image graph in subpath"
            )
            self._apply_reduction(image_graph, points_to_remove)

    def _corner_substitution_cost_matrix(
        self,
        image_nodes: List[Any],
        concept_nodes: List[Any],
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
    ) -> np.ndarray:
        # Score each (image corner, concept corner) pair by the SAME range-membership
        # substitution cost the downstream GED uses. The corners we keep are then the ones
        # GED would actually match cheaply, instead of the ones a separate center-based
        # similarity metric happens to rank high. Image corners still carry the CornerPoint
        # label at this stage, so the concept-subset label check passes and the cost is a
        # real feature cost rather than IMPOSSIBLE.
        cost_matrix = np.zeros((len(image_nodes), len(concept_nodes)))
        for i, image_node in enumerate(image_nodes):
            for j, concept_node in enumerate(concept_nodes):
                cost_matrix[i, j] = node_subst_cost(
                    image_graph.nodes[image_node], concept_graph.nodes[concept_node]
                )
        return cost_matrix

    def _identify_corner_points_to_remove(
        self, cost_matrix: np.ndarray, nodes: List[Any]
    ) -> List[Any]:
        if cost_matrix.size == 0:
            self.logger.error("Cost matrix is empty. Raising error.", exc_info=True)
            raise ValueError("Cost matrix is empty.")

        # Keep exactly one image corner per concept corner slot via an optimal one-to-one
        # assignment that minimizes total substitution cost; demote the rest. This replaces
        # the previous greedy `max(similarity, axis=1)` selection, which had no distinct-slot
        # constraint and could keep two corners both nearest the same concept slot, starving
        # another slot and forcing GED into a high-cost substitution.
        row_ind, _ = linear_sum_assignment(cost_matrix)
        keep = set(int(r) for r in row_ind)
        nodes_to_remove = [nodes[i] for i in range(len(nodes)) if i not in keep]

        self.logger.debug(f"Nodes identified for removal: {nodes_to_remove}")
        return nodes_to_remove

    def _get_corner_points(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_corner_point(data)
        ]

    def _apply_reduction(self, graph: nx.Graph, nodes: List[Any]) -> nx.Graph:
        for node in nodes:
            if node in graph:
                labels = graph.nodes[node]["labels"]
                if CriticalPointType.CORNER_POINT.value in labels:
                    labels.remove(CriticalPointType.CORNER_POINT.value)
                    graph.nodes[node]["labels"] = labels
        return graph
