import networkx as nx
import collections
import logging
from typing import Dict, Set, Tuple, List, Any
from property_handlers.property_handler_manager import PropertyHandlerManager
from node_similarity_calculator import NodeSimilarityCalculator
from critical_point_preprocessor import CriticalPointPreprocessor
from utils.graph_utils import GraphUtils
from model.critical_point import CriticalPointType


class SyncedGraphMinorFinder:
    def __init__(
        self,
        prop_manager: PropertyHandlerManager,
        similarity_calculator: NodeSimilarityCalculator,
        critical_point_preprocessor: CriticalPointPreprocessor,
        logger=None,
    ):
        self.prop_manager = prop_manager
        self.similarity_calculator = similarity_calculator
        self.logger = logger or logging.getLogger(__name__)
        self.critical_point_preprocessor = critical_point_preprocessor

    def find_max_common_minor(self, G_c: nx.Graph, G_i: nx.Graph) -> nx.Graph:
        """Finding the maximum common minor of two graphs by traversing through critical points first, generating the skeleton graph

        Args:
            G_c (nx.Graph): concept graph
            G_i (nx.Graph): image graph

        Returns:
            nx.Graph: maximum common minor of the two graphs
        """
        # Preprocess the graphs to align critical points
        G_c, G_i = self.critical_point_preprocessor.preprocess_graphs(G_c, G_i)
        if G_c.number_of_nodes() != G_i.number_of_nodes():
            raise ValueError("The number of nodes in the two graphs are not the same")

        start_c = GraphUtils.get_first_point_by_type(G_c, CriticalPointType.START_POINT)
        start_i = GraphUtils.get_first_point_by_type(G_i, CriticalPointType.START_POINT)

        # Matrix of the subpaths between intersection points
        # Inside eachh subpath we have the traversal sequence of two graphs
        # Each inner list represents a continuous path between critical points
        sync_list: List[List[Tuple[Any, Any]]] = []

        initial_path_id = 0
        sync_list.append([(start_c, start_i)])

        completed_paths = set()

        # Queue stores (node_c, node_i, path_id, prev_c, prev_i)
        # The prev_* values help avoid immediate backtracking
        queue = collections.deque([(start_c, start_i, initial_path_id, None, None)])

        # Track visited node pairs to avoid cycles
        # We use a dict to map (node_c, node_i) -> set of path_ids that have visited this pair
        # This allows revisiting a node pair on different paths (branches)
        visited = {}
        visited[(start_c, start_i)] = {initial_path_id}
        self.logger.info(f"Starting traversal with initial path {initial_path_id}")
        self.logger.info(f"Start nodes: {start_c}, {start_i}")

        while queue:
            current_c, current_i, path_id, prev_c, prev_i = queue.popleft()
            self.logger.info(
                f"Processing node {current_c}, {current_i} from path {path_id}"
            )

            # Skip if we've already processed this path
            if path_id in completed_paths:
                continue

            is_intersection_point_c = GraphUtils.is_intersection_point(
                G_c.nodes[current_c]
            )

            if is_intersection_point_c:
                self.logger.info(f"Intersection point found: {current_c}, {current_i}")
                processed_c = set(node_c for node_c, _ in visited.keys())
                processed_i = set(node_i for _, node_i in visited.keys())
                matched_points = (
                    self._get_matched_intersection_point_critical_neighbors(
                        G_c=G_c,
                        G_i=G_i,
                        intersection_c=current_c,
                        intersection_i=current_i,
                        processed_c=processed_c,
                        processed_i=processed_i,
                    )
                )

                # For the matched points, create new path branches
                for key in matched_points.keys():
                    # Create a new path ID
                    new_path_id = len(sync_list)
                    sync_list.append([(current_c, current_i)])

                    # Add the new path to the queue
                    visited[(key, matched_points[key])] = {new_path_id}
                    queue.append(
                        (
                            key,
                            matched_points[key],
                            new_path_id,
                            current_c,
                            current_i,
                        )
                    )
                continue

            next_c_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_c, current_c, prev_c
            )
            next_i_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_i, current_i, prev_i
            )

            if next_c_critical_point is None and next_i_critical_point is None:
                self.logger.info(
                    "No next critical points found for this path, continuing"
                )
                completed_paths.add(path_id)
                continue
            elif next_c_critical_point is None or next_i_critical_point is None:
                # If one of the critical points is None, we need to backtrack
                self.logger.info(
                    "No next critical points found for this path, continuing"
                )
                continue
            else:
                # If both critical points are not None, we need to add the nodes to the sync list
                sync_list[path_id].append(
                    (next_c_critical_point, next_i_critical_point)
                )

            self.logger.info(
                f"Next critical points: {next_c_critical_point}, {next_i_critical_point}"
            )
            if not GraphUtils.is_same_critical_point_type(
                G_c.nodes[next_c_critical_point], G_i.nodes[next_i_critical_point]
            ):
                self.logger.info("Critical points are not the same type, raising error")
                raise ValueError("Critical points are not the same type")

            # Add the next critical points to the queue
            queue.append(
                (
                    next_c_critical_point,
                    next_i_critical_point,
                    path_id,
                    current_c,
                    current_i,
                )
            )

            visited[(next_c_critical_point, next_i_critical_point)] = {path_id}

        # Find the maximum common minor
        return G_c

    def _get_matched_intersection_point_critical_neighbors(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        intersection_c: Any,
        intersection_i: Any,
        processed_c: Set[Any],
        processed_i: Set[Any],
    ) -> Dict[Any, Any]:
        """Getting the matched critical point-neighbors of the current intersection point"""
        neighbors_c = list(G_c.neighbors(intersection_c))
        neighbors_i = list(G_i.neighbors(intersection_i))

        # We start from the neighbors of the intersection point and find the next critical point excluding the intersection point itself
        critical_neighbors_c = []
        critical_neighbors_i = []
        for neighbor_c in neighbors_c:
            next_c_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_c, start_point=neighbor_c, prev_point=intersection_c
            )
            if (
                next_c_critical_point is not None
                and next_c_critical_point not in processed_c
            ):
                critical_neighbors_c.append(next_c_critical_point)

        for neighbor_i in neighbors_i:
            next_i_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_i, start_point=neighbor_i, prev_point=intersection_i
            )
            if (
                next_i_critical_point is not None
                and next_i_critical_point not in processed_i
            ):
                critical_neighbors_i.append(next_i_critical_point)

        if len(critical_neighbors_c) != len(critical_neighbors_i):
            raise ValueError(
                "The number of critical neighbors of the two graphs are not the same"
            )

        return self._match_critical_points(
            G_c=G_c,
            G_i=G_i,
            concept_critical_points=critical_neighbors_c,
            image_critical_points=critical_neighbors_i,
        )

    def _match_critical_points(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        concept_critical_points: List[Any],
        image_critical_points: List[Any],
    ) -> Dict[Any, Any]:
        """Matching the critical points between the two graphs"""

        # Prepare the critical points by type
        concept_node_type_to_critical_points = {}
        for cp in concept_critical_points:
            cp_type = GraphUtils.get_critical_point_type(G_c.nodes[cp])
            if cp_type not in concept_node_type_to_critical_points:
                concept_node_type_to_critical_points[cp_type] = []
            concept_node_type_to_critical_points[cp_type].append(cp)

        image_node_type_to_critical_points = {}
        for cp in image_critical_points:
            cp_type = GraphUtils.get_critical_point_type(G_i.nodes[cp])
            if cp_type not in image_node_type_to_critical_points:
                image_node_type_to_critical_points[cp_type] = []
            image_node_type_to_critical_points[cp_type].append(cp)

        critical_point_mapping = {}

        unmatched_concept_critical_points = set(concept_critical_points)
        unmatched_image_critical_points = set(image_critical_points)

        # First, match critical points where there's only one node per type
        for cp_type, concept_points in concept_node_type_to_critical_points.items():
            image_points = image_node_type_to_critical_points.get(cp_type, [])

            # If there's exactly one critical point of this type in both graphs, match them
            if len(concept_points) == 1 and len(image_points) == 1:
                concept_cp = concept_points[0]
                image_cp = image_points[0]

                critical_point_mapping[concept_cp] = image_cp

                # Remove these points from the unmatched sets
                unmatched_concept_critical_points.remove(concept_cp)
                unmatched_image_critical_points.remove(image_cp)

                self.logger.debug(
                    f"Matched unique critical points of type {cp_type}: {concept_cp} -> {image_cp}"
                )

        # For critical point types with multiple nodes, use node similarity to match them
        for cp_type, concept_points in concept_node_type_to_critical_points.items():
            image_points = image_node_type_to_critical_points.get(cp_type, [])

            # Skip if we've already matched all points of this type
            if not any(
                cp in unmatched_concept_critical_points for cp in concept_points
            ):
                continue

            # Skip if there are no image points of this type
            if not image_points:
                continue

            # Filter to only include unmatched points
            unmatched_concept_points = [
                cp for cp in concept_points if cp in unmatched_concept_critical_points
            ]
            unmatched_image_points = [
                cp for cp in image_points if cp in unmatched_image_critical_points
            ]

            if not unmatched_concept_points or not unmatched_image_points:
                continue

            self.logger.debug(
                f"Matching remaining critical points of type {cp_type}: {len(unmatched_concept_points)} concept points, {len(unmatched_image_points)} image points"
            )

            # Create a similarity calculator
            similarity_calculator = NodeSimilarityCalculator(logger=self.logger)

            # Calculate similarity matrix between unmatched points
            similarity_matrix = similarity_calculator.calculate_similarity_matrix(
                G_c, G_i, unmatched_concept_points, unmatched_image_points
            )

            # Match points greedily based on highest similarity
            while unmatched_concept_points and unmatched_image_points:
                # Find the highest similarity score
                max_similarity = -1
                best_match = None

                for i, concept_cp in enumerate(unmatched_concept_points):
                    for j, image_cp in enumerate(unmatched_image_points):
                        if similarity_matrix[i][j] > max_similarity:
                            max_similarity = similarity_matrix[i][j]
                            best_match = (concept_cp, image_cp, i, j)

                # If we found a match with reasonable similarity
                if best_match:
                    concept_cp, image_cp, _, _ = best_match
                    critical_point_mapping[concept_cp] = image_cp

                    # Remove matched points from unmatched sets
                    unmatched_concept_critical_points.remove(concept_cp)
                    unmatched_image_critical_points.remove(image_cp)

                    # Remove from our local lists too
                    unmatched_concept_points.remove(concept_cp)
                    unmatched_image_points.remove(image_cp)

                    self.logger.debug(
                        f"Matched critical points based on similarity ({max_similarity:.2f}): {concept_cp} -> {image_cp}"
                    )
                else:
                    # No more good matches found
                    break

        return critical_point_mapping
