import logging
from typing import Any, List, Tuple, Set, FrozenSet, Dict
import networkx as nx
import collections
from node_similarity_calculator import NodeSimilarityCalculator
from utils.graph_utils import GraphUtils
from model.critical_point import CriticalPointType


class SyncedTraversalGenerator:
    def __init__(self, critical_point_types: Set[CriticalPointType]):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.similarity_calculator = NodeSimilarityCalculator()
        self.critical_point_types = critical_point_types

    def generate_synced_traversal(
        self, G_c: nx.Graph, G_i: nx.Graph
    ) -> List[List[Tuple[Any, Any]]]:
        """Generates synchronized traversal paths between two graphs (concept and image).

        This method attempts to find corresponding paths of critical points
        between two graphs, G_c (concept) and G_i (image), starting from
        their respective START_POINT nodes.

        The algorithm proceeds as follows:
        1. Initializes a queue with the starting node pair (start_c, start_i).
        2. Iteratively processes pairs of nodes (current_c, current_i) from the queue.
        3. For each pair, it finds the next corresponding critical points
           (next_c_critical_point, next_i_critical_point) in each graph using BFS,
           avoiding immediate backtracking.
        4. If the next critical points are of the same type, the pair is added to the
           current synchronized path.
        5. If the current node pair represents an intersection point in G_c:
           - It finds all reachable, non-processed critical neighbor pairs using
             `_get_matched_intersection_point_critical_neighbors`.
           - For each matched neighbor pair, it starts a *new* synchronized path (branch)
             and adds it to the queue.
           - The current path is marked as completed.
        6. The process continues until the queue is empty.
        7. Cycle detection is implemented by tracking visited node pairs per path ID
           and processed segments (pairs of critical points forming an edge).

        Args:
            G_c: The concept graph (NetworkX graph).
            G_i: The image graph (NetworkX graph).

        Returns:
            A list of lists, where each inner list represents a synchronized path.
            Each element in the inner list is a tuple (node_c, node_i) representing
            corresponding critical points in the two graphs.

        Raises:
            ValueError: If START_POINT nodes cannot be found in either graph, or if
                        encountered critical points during traversal do not have the
                        same type.
        """
        sync_list: List[List[Tuple[Any, Any]]] = []

        start_c = GraphUtils.get_first_point_by_type(G_c, CriticalPointType.START_POINT)
        start_i = GraphUtils.get_first_point_by_type(G_i, CriticalPointType.START_POINT)

        if start_c is None or start_i is None:
            raise ValueError("Could not find start points in one or both graphs.")

        initial_path_id = 0
        sync_list.append([(start_c, start_i)])

        completed_paths = set()

        processed_segments: Set[FrozenSet[Tuple[Any, Any]]] = set()

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
            current_pair = (current_c, current_i)
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
                for concept_neighbor_cp, image_neighbor_cp in matched_points.items():
                    neighbor_pair = (concept_neighbor_cp, image_neighbor_cp)

                    segment = frozenset([current_pair, neighbor_pair])
                    if segment in processed_segments:
                        self.logger.debug(
                            f"Segment {segment} already processed, skipping branch."
                        )
                        continue
                    processed_segments.add(segment)
                    self.logger.debug(f"Added segment {segment} to processed set.")

                    # Create a new path ID
                    new_path_id = len(sync_list)
                    # Initialize the new path with the intersection point
                    sync_list.append([current_pair])

                    # Add the matched neighbor pair to the new path list
                    sync_list[new_path_id].append(neighbor_pair)

                    # Add the new path to the queue using the MATCHED PAIR
                    # Ensure the matched pair itself isn't immediately revisited on this new path
                    if neighbor_pair not in visited:
                        visited[neighbor_pair] = set()
                    visited[neighbor_pair].add(new_path_id)

                    queue.append(
                        (
                            concept_neighbor_cp,  # Matched concept neighbor
                            image_neighbor_cp,  # Matched image neighbor
                            new_path_id,
                            current_c,  # Previous concept node (intersection)
                            current_i,  # Previous image node (intersection)
                        )
                    )
                    self.logger.info(
                        f"Branched to new path {new_path_id} with segment {current_pair} -> {neighbor_pair}"
                    )
                # Mark the current path as completed since we branched
                completed_paths.add(path_id)
                self.logger.debug(
                    f"Marked path {path_id} as completed due to intersection."
                )
                continue  # Continue to next item in queue

            next_c_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_c, current_c, prev_c, self.critical_point_types
            )
            next_i_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_i, current_i, prev_i, self.critical_point_types
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

            self.logger.info(
                f"Next critical points: {next_c_critical_point}, {next_i_critical_point}"
            )
            if not GraphUtils.is_same_critical_point_type(
                G_c.nodes[next_c_critical_point], G_i.nodes[next_i_critical_point]
            ):
                raise ValueError("Critical points are not the same type")

            next_pair = (next_c_critical_point, next_i_critical_point)

            segment = frozenset([current_pair, next_pair])
            if segment in processed_segments:
                self.logger.info(
                    f"Path {path_id} ending: Segment {segment} already processed."
                )
                completed_paths.add(path_id)
                continue  # Stop this path, segment covered elsewhere
            processed_segments.add(segment)
            self.logger.debug(f"Added segment {segment} to processed set.")

            if next_pair in visited and path_id in visited[next_pair]:
                self.logger.info(
                    f"Path {path_id} ending: Detected cycle by revisiting pair {next_pair}."
                )
                # Append the closing pair to signify the cycle completion
                sync_list[path_id].append(next_pair)
                completed_paths.add(path_id)
                continue  # Stop this path, cycle detected

            sync_list[path_id].append(next_pair)
            if next_pair not in visited:
                visited[next_pair] = set()
            visited[next_pair].add(path_id)

            visited[(next_c_critical_point, next_i_critical_point)] = {path_id}

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

        return sync_list

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

        # Continue with regular neighbor finding
        for neighbor_c in neighbors_c:
            next_c_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_c,
                start_point=neighbor_c,
                prev_point=intersection_c,
                supported_types=self.critical_point_types,
            )
            if (
                next_c_critical_point is not None
                and (next_c_critical_point not in processed_c
                or next_c_critical_point == intersection_c)
            ):
                critical_neighbors_c.append(next_c_critical_point)

        for neighbor_i in neighbors_i:
            next_i_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_i,
                start_point=neighbor_i,
                prev_point=intersection_i,
                supported_types=self.critical_point_types,
            )
            if (
                next_i_critical_point is not None
                and (next_i_critical_point not in processed_i
                or next_i_critical_point == intersection_i)
            ):
                critical_neighbors_i.append(next_i_critical_point)

        # Log critical neighbors found
        self.logger.debug(
            f"Critical neighbors for concept intersection {intersection_c}: {critical_neighbors_c}"
        )
        self.logger.debug(
            f"Critical neighbors for image intersection {intersection_i}: {critical_neighbors_i}"
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

            # Calculate similarity matrix between unmatched points
            similarity_matrix = self.similarity_calculator.calculate_similarity_matrix(
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
