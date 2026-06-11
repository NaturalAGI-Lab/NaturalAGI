import logging
import os
from typing import Any, List, Tuple, Set, FrozenSet, Dict
import networkx as nx
import collections
import numpy as np
from scipy.optimize import linear_sum_assignment
from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils
from src.node_similarity_calculator import NodeSimilarityCalculator


class SyncedTraversalGenerator:
    def __init__(self, critical_point_types: Set[CriticalPointType]):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.similarity_calculator = NodeSimilarityCalculator()
        self.critical_point_types = critical_point_types
        self.max_pair_distance = float(
            os.getenv("CONCEPT_PAIR_DISTANCE_THRESHOLD", "0.35")
        )

    def _pair_distance(self, node_c_data: Dict, node_i_data: Dict) -> float:
        c_x = self._get_node_coord(node_c_data, "x")
        c_y = self._get_node_coord(node_c_data, "y")
        i_x = self._get_node_coord(node_i_data, "x")
        i_y = self._get_node_coord(node_i_data, "y")
        return float(np.sqrt((c_x - i_x) ** 2 + (c_y - i_y) ** 2))

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
        # Track which exits from intersection/multi-branch nodes have been processed.
        # Key: (intersection_concept_node, exit_neighbor_concept_node)
        # This allows parallel paths between the same pair of critical points
        # (e.g., two arcs of a figure-8 upper loop) to be traversed separately.
        processed_intersection_exits: Set[Tuple[Any, Any]] = set()

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
            is_multi_branch_start = prev_c is None and G_c.degree(current_c) >= 2

            if is_intersection_point_c or is_multi_branch_start:
                if is_multi_branch_start:
                    self.logger.info(
                        f"Multi-branch start point: {current_c}, {current_i} (degree={G_c.degree(current_c)})"
                    )
                self.logger.info(f"Intersection point found: {current_c}, {current_i}")
                matched_branches = (
                    self._get_matched_intersection_point_critical_neighbors(
                        G_c=G_c,
                        G_i=G_i,
                        intersection_c=current_c,
                        intersection_i=current_i,
                    )
                )

                # For the matched branches, create new path branches
                for concept_neighbor_cp, image_neighbor_cp, exit_c, exit_i in matched_branches:
                    neighbor_pair = (concept_neighbor_cp, image_neighbor_cp)

                    exit_key = (current_c, exit_c)
                    if exit_key in processed_intersection_exits:
                        self.logger.debug(
                            f"Exit branch ({current_c}, {exit_c}) already processed, skipping."
                        )
                        continue
                    processed_intersection_exits.add(exit_key)
                    self.logger.debug(f"Processing exit branch ({current_c}, {exit_c}) -> {concept_neighbor_cp}.")

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
                self.logger.info(
                    f"Path {path_id} ending: Critical point type mismatch - "
                    f"concept={G_c.nodes[next_c_critical_point].get('labels')}, "
                    f"image={G_i.nodes[next_i_critical_point].get('labels')}"
                )
                completed_paths.add(path_id)
                continue

            pair_distance = self._pair_distance(
                G_c.nodes[next_c_critical_point], G_i.nodes[next_i_critical_point]
            )
            if pair_distance > self.max_pair_distance:
                self.logger.info(
                    f"Path {path_id} ending: spatial mismatch {pair_distance:.2f} for pair "
                    f"({next_c_critical_point}, {next_i_critical_point})"
                )
                completed_paths.add(path_id)
                continue

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
    ) -> List[Tuple[Any, Any, Any, Any]]:
        """Get matched critical point-neighbor branches of the current intersection point.

        Returns a list of branch tuples preserving multiplicity — multiple branches
        to the same critical point (parallel paths) are kept as separate entries.

        Returns:
            List of (concept_dest_cp, image_dest_cp, exit_neighbor_c, exit_neighbor_i).
        """
        neighbors_c = list(G_c.neighbors(intersection_c))
        neighbors_i = list(G_i.neighbors(intersection_i))

        # Build branch info: (exit_neighbor, destination_critical_point)
        branches_c: List[Tuple[Any, Any]] = []
        for neighbor_c in neighbors_c:
            next_c_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_c,
                start_point=neighbor_c,
                prev_point=intersection_c,
                supported_types=self.critical_point_types,
            )
            if next_c_critical_point is not None:
                branches_c.append((neighbor_c, next_c_critical_point))

        branches_i: List[Tuple[Any, Any]] = []
        for neighbor_i in neighbors_i:
            next_i_critical_point = GraphUtils.find_next_critical_point_bfs(
                G_i,
                start_point=neighbor_i,
                prev_point=intersection_i,
                supported_types=self.critical_point_types,
            )
            if next_i_critical_point is not None:
                branches_i.append((neighbor_i, next_i_critical_point))

        self.logger.debug(
            f"Concept branches from {intersection_c}: "
            f"{[(exit_n, dest) for exit_n, dest in branches_c]}"
        )
        self.logger.debug(
            f"Image branches from {intersection_i}: "
            f"{[(exit_n, dest) for exit_n, dest in branches_i]}"
        )

        return self._match_branches(G_c, G_i, branches_c, branches_i)

    def _match_branches(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        branches_c: List[Tuple[Any, Any]],
        branches_i: List[Tuple[Any, Any]],
    ) -> List[Tuple[Any, Any, Any, Any]]:
        """Match concept and image branches by destination type and exit neighbor similarity.

        When multiple branches lead to the same critical point type (parallel paths),
        uses exit neighbor spatial properties with Hungarian algorithm to pair them.

        Args:
            branches_c: List of (exit_neighbor, destination_cp) from concept intersection.
            branches_i: List of (exit_neighbor, destination_cp) from image intersection.

        Returns:
            List of (concept_dest_cp, image_dest_cp, exit_c, exit_i) tuples.
        """
        groups_c: Dict[CriticalPointType, List[Tuple[Any, Any]]] = {}
        for exit_n, dest_cp in branches_c:
            cp_type = GraphUtils.get_critical_point_type(G_c.nodes[dest_cp])
            if cp_type not in groups_c:
                groups_c[cp_type] = []
            groups_c[cp_type].append((exit_n, dest_cp))

        groups_i: Dict[CriticalPointType, List[Tuple[Any, Any]]] = {}
        for exit_n, dest_cp in branches_i:
            cp_type = GraphUtils.get_critical_point_type(G_i.nodes[dest_cp])
            if cp_type not in groups_i:
                groups_i[cp_type] = []
            groups_i[cp_type].append((exit_n, dest_cp))

        matched: List[Tuple[Any, Any, Any, Any]] = []

        for cp_type, c_group in groups_c.items():
            i_group = groups_i.get(cp_type, [])
            if not i_group:
                continue

            if len(c_group) == 1 and len(i_group) == 1:
                exit_c, dest_c = c_group[0]
                exit_i, dest_i = i_group[0]
                pair_distance = self._pair_distance(
                    G_c.nodes[exit_c], G_i.nodes[exit_i]
                )
                if pair_distance > self.max_pair_distance:
                    self.logger.info(
                        f"Rejecting branch of type {cp_type}: spatial mismatch "
                        f"{pair_distance:.2f} for exits ({exit_c}, {exit_i})"
                    )
                    continue
                matched.append((dest_c, dest_i, exit_c, exit_i))
                self.logger.debug(
                    f"Matched unique branch of type {cp_type}: {dest_c} -> {dest_i}"
                )
            else:
                # Multiple branches of the same type: match by exit neighbor similarity
                n_c, n_i = len(c_group), len(i_group)
                distance_matrix = np.zeros((n_c, n_i))

                for idx_c, (exit_c, _) in enumerate(c_group):
                    for idx_i, (exit_i, _) in enumerate(i_group):
                        c_x = self._get_node_coord(G_c.nodes[exit_c], 'x')
                        c_y = self._get_node_coord(G_c.nodes[exit_c], 'y')
                        i_x = self._get_node_coord(G_i.nodes[exit_i], 'x')
                        i_y = self._get_node_coord(G_i.nodes[exit_i], 'y')
                        distance_matrix[idx_c, idx_i] = np.sqrt(
                            (c_x - i_x) ** 2 + (c_y - i_y) ** 2
                        )

                max_distance = np.sqrt(2 * (2 ** 2))
                similarity_matrix = 1.0 - (distance_matrix / max_distance)
                cost_matrix = -similarity_matrix
                row_ind, col_ind = linear_sum_assignment(cost_matrix)

                for r, c_idx in zip(row_ind, col_ind):
                    exit_c, dest_c = c_group[r]
                    exit_i, dest_i = i_group[c_idx]
                    sim = similarity_matrix[r, c_idx]
                    if distance_matrix[r, c_idx] > self.max_pair_distance:
                        self.logger.info(
                            f"Rejecting branch of type {cp_type}: spatial mismatch "
                            f"{distance_matrix[r, c_idx]:.2f} for exits ({exit_c}, {exit_i})"
                        )
                        continue
                    matched.append((dest_c, dest_i, exit_c, exit_i))
                    self.logger.debug(
                        f"Matched branch of type {cp_type} (similarity={sim:.2f}): "
                        f"exit {exit_c} -> {dest_c} with exit {exit_i} -> {dest_i}"
                    )

        return matched

    @staticmethod
    def _get_node_coord(node_data: Dict, axis: str) -> float:
        """Extract a representative coordinate from a node (Point or Vector)."""
        # Try normalized coordinates first
        norm_key = f'normalized_{axis}'
        if norm_key in node_data:
            val = node_data[norm_key]
            if isinstance(val, dict):
                return val.get('center', val.get('min', 0))
            return val

        # For vectors: use midpoint of endpoints
        key1 = f'{axis}1'
        key2 = f'{axis}2'
        if key1 in node_data and key2 in node_data:
            v1, v2 = node_data[key1], node_data[key2]
            if isinstance(v1, dict):
                v1 = v1.get('center', v1.get('min', 0))
            if isinstance(v2, dict):
                v2 = v2.get('center', v2.get('min', 0))
            return (v1 + v2) / 2

        # Fallback: raw coordinate
        if axis in node_data:
            val = node_data[axis]
            if isinstance(val, dict):
                return val.get('center', val.get('min', 0))
            return val

        return 0
