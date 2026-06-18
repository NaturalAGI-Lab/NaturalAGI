import logging
from typing import List, Any, Optional, Set, Tuple
import numpy as np
import networkx as nx
from scipy.optimize import linear_sum_assignment


class DistanceMatrixCalculator:
    """Calculates distance matrices based on coordinate properties for graph node matching."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def extract_coordinate_value(self, coord_value: Any) -> Optional[float]:
        """Extract numeric coordinate value, handling both simple values and range objects."""
        if coord_value is None:
            return None

        if isinstance(coord_value, dict) and "center" in coord_value:
            return float(coord_value["center"])

        if isinstance(coord_value, (int, float)):
            return float(coord_value)

        return None

    def calculate_distance_matrix(
        self,
        graph_large: nx.Graph,
        graph_small: nx.Graph,
        points_large: List[Any],
        points_small: List[Any],
        properties_to_compare: Set[str],
        position_weight: float = 0.8,
        direction_weight: float = 0.2,
        structural_weight: float = 0.0,
    ) -> np.ndarray:
        """Calculate Euclidean distance matrix based on coordinate properties.

        Args:
            graph_large: Graph containing the larger set of points
            graph_small: Graph containing the smaller set of points
            points_large: List of node IDs from graph_large
            points_small: List of node IDs from graph_small
            properties_to_compare: Set of property names to use for distance calculation
                                  (e.g., {"normalized_x", "normalized_y"})

        Returns:
            Distance matrix of shape (len(points_large), len(points_small))
        """
        distance_matrix = np.zeros((len(points_large), len(points_small)))

        for i, node_large in enumerate(points_large):
            node_large_data = graph_large.nodes[node_large]
            coordinates_large = [
                self.extract_coordinate_value(node_large_data.get(prop))
                for prop in properties_to_compare
            ]

            if any(coord is None for coord in coordinates_large):
                self.logger.warning(
                    f"Node {node_large} missing required properties {properties_to_compare}, using large distance"
                )
                distance_matrix[i, :] = np.inf
                continue

            for j, node_small in enumerate(points_small):
                node_small_data = graph_small.nodes[node_small]
                coordinates_small = [
                    self.extract_coordinate_value(node_small_data.get(prop))
                    for prop in properties_to_compare
                ]

                if any(coord is None for coord in coordinates_small):
                    self.logger.warning(
                        f"Node {node_small} missing required properties {properties_to_compare}, using large distance"
                    )
                    distance_matrix[i, j] = np.inf
                    continue

                pos_props = ["normalized_x", "normalized_y"]
                dir_props = ["direction_x", "direction_y"]
                struct_props = ["branch_corner_density"]

                has_position = any(prop in properties_to_compare for prop in pos_props)
                has_direction = any(prop in properties_to_compare for prop in dir_props)
                has_structural = any(prop in properties_to_compare for prop in struct_props)

                if has_position and (has_direction or has_structural):
                    pos_coords_large = [self.extract_coordinate_value(node_large_data.get(prop)) for prop in pos_props if prop in properties_to_compare and self.extract_coordinate_value(node_large_data.get(prop)) is not None]
                    pos_coords_small = [self.extract_coordinate_value(node_small_data.get(prop)) for prop in pos_props if prop in properties_to_compare and self.extract_coordinate_value(node_small_data.get(prop)) is not None]
                    dir_coords_large = [self.extract_coordinate_value(node_large_data.get(prop)) for prop in dir_props if prop in properties_to_compare and self.extract_coordinate_value(node_large_data.get(prop)) is not None]
                    dir_coords_small = [self.extract_coordinate_value(node_small_data.get(prop)) for prop in dir_props if prop in properties_to_compare and self.extract_coordinate_value(node_small_data.get(prop)) is not None]

                    pos_dist = 0.0
                    dir_dist = 0.0

                    if len(pos_coords_large) == len(pos_coords_small) and len(pos_coords_large) > 0:
                        pos_squared_diffs = [(c1 - c2) ** 2 for c1, c2 in zip(pos_coords_large, pos_coords_small)]
                        pos_max_dist = np.sqrt(len(pos_squared_diffs) * 4)
                        pos_dist = np.sqrt(sum(pos_squared_diffs)) / pos_max_dist

                    if len(dir_coords_large) == len(dir_coords_small) and len(dir_coords_large) > 0:
                        dir_squared_diffs = [(c1 - c2) ** 2 for c1, c2 in zip(dir_coords_large, dir_coords_small)]
                        dir_max_dist = np.sqrt(len(dir_squared_diffs) * 4)
                        dir_dist = np.sqrt(sum(dir_squared_diffs)) / dir_max_dist

                    struct_dist = 0.0
                    if has_structural:
                        struct_coords_large = [self.extract_coordinate_value(node_large_data.get(prop)) for prop in struct_props if prop in properties_to_compare and self.extract_coordinate_value(node_large_data.get(prop)) is not None]
                        struct_coords_small = [self.extract_coordinate_value(node_small_data.get(prop)) for prop in struct_props if prop in properties_to_compare and self.extract_coordinate_value(node_small_data.get(prop)) is not None]

                        if len(struct_coords_large) == len(struct_coords_small) and len(struct_coords_large) > 0:
                            struct_squared_diffs = [(c1 - c2) ** 2 for c1, c2 in zip(struct_coords_large, struct_coords_small)]
                            struct_max_dist = np.sqrt(len(struct_squared_diffs))
                            struct_dist = np.sqrt(sum(struct_squared_diffs)) / struct_max_dist

                    distance = position_weight * pos_dist + direction_weight * dir_dist + structural_weight * struct_dist
                else:
                    squared_diffs = [
                        (coord_large - coord_small) ** 2
                        for coord_large, coord_small in zip(coordinates_large, coordinates_small)
                    ]
                    max_distance = np.sqrt(len(squared_diffs) * 4)
                    distance = np.sqrt(sum(squared_diffs)) / max_distance
                
                distance_matrix[i, j] = distance

        return distance_matrix
    
    def find_points_above_distance_threshold(
        self, 
        distance_matrix: np.ndarray, 
        points: List[Any],
        threshold: float,
        axis: int = 1,
    ) -> List[Any]:
        """Find points where minimum distance is above threshold.

        Args:
            distance_matrix (np.ndarray): Distance matrix
            points (List[Any]): List of point IDs corresponding to the rows/columns of the distance matrix
            threshold (float): Maximum distance threshold.
            axis (int, optional): 0 for columns, 1 for rows

        Returns:
            List[Any]: List of point IDs where minimum distance is above threshold
        """
        if distance_matrix.size == 0:
            self.logger.error("Distance matrix is empty. Raising error.")
            raise ValueError("Distance matrix is empty.")

        min_distances = np.min(distance_matrix, axis=axis)
        
        points_above_threshold = []
        for i, point in enumerate(points):
            if round(min_distances[i], 2) > threshold:
                self.logger.info(f"Point {point} has minimum distance {min_distances[i]} above threshold {threshold}. Adding to list of points to remove.")
                points_above_threshold.append(point)
                
        return points_above_threshold
    
    def find_points_for_difference(
        self,
        distance_matrix: np.ndarray,
        points: List[Any],
        difference: int,
        axis: int = 1,
    ) -> List[Any]:
        """Find points with worst match quality to remove.

        Args:
            distance_matrix (np.ndarray): Distance matrix
            points (List[Any]): List of point IDs corresponding to the rows/columns of the distance matrix
            difference (int): Number of points to remove
            axis (int, optional): 0 for columns, 1 for rows

        Returns:
            List[Any]: List of point IDs with worst match quality
        """
        if difference <= 0:
            return []
            
        if distance_matrix.size == 0:
            self.logger.error("Distance matrix is empty. Raising error.")
            raise ValueError("Distance matrix is empty.")
            
        row_ind, col_ind = linear_sum_assignment(distance_matrix)
        matched_distances = distance_matrix[row_ind, col_ind]
        
        point_qualities = []
        
        if axis == 0:
            matched_indices = set(col_ind)
            all_indices = set(range(distance_matrix.shape[1]))
            unmatched_indices = all_indices - matched_indices
            
            for idx in matched_indices:
                col_position = np.where(col_ind == idx)[0][0]
                distance = matched_distances[col_position]
                point_qualities.append((idx, distance))
            
            for idx in unmatched_indices:
                min_distance = np.min(distance_matrix[:, idx])
                point_qualities.append((idx, min_distance))
        else:
            matched_indices = set(row_ind)
            all_indices = set(range(distance_matrix.shape[0]))
            unmatched_indices = all_indices - matched_indices
            
            for idx in matched_indices:
                row_position = np.where(row_ind == idx)[0][0]
                distance = matched_distances[row_position]
                point_qualities.append((idx, distance))
            
            for idx in unmatched_indices:
                min_distance = np.min(distance_matrix[idx, :])
                point_qualities.append((idx, min_distance))
        
        point_qualities.sort(key=lambda x: x[1], reverse=True)
        worst_indices = [idx for idx, _ in point_qualities[:difference]]
        points_for_difference = [points[i] for i in worst_indices]
        
        self.logger.info(f"Points identified for removal (worst match quality): {points_for_difference}")
        for idx, dist in point_qualities[:difference]:
            self.logger.info(f"  Point {points[idx]}: distance={dist:.4f}")

        return points_for_difference

    def find_ordered_points_for_difference(
        self,
        distance_matrix: np.ndarray,
        points_large: List[Any],
        difference: int,
    ) -> List[Any]:
        """Find points to remove using orientation-agnostic order-preserving matching.

        The monotone DP respects the sequential order of points along a path, but
        that only yields the right matching when both sequences share one traversal
        orientation. The two loops of a figure-8 can be emitted in opposite angular
        order, where the geometrically correct match is a crossing the forward DP
        cannot express. We therefore run the DP on both orientations of the large
        set and keep the one with the lower matched cost.

        Args:
            distance_matrix: Shape (m, n) where m > n. Rows = large set, cols = small set.
            points_large: Point IDs for the larger set (rows), in path order.
            difference: Number of points to remove (m - n).

        Returns:
            List of point IDs from points_large that were not matched.
        """
        if difference <= 0:
            return []

        if distance_matrix.size == 0:
            raise ValueError("Distance matrix is empty.")

        m, _ = distance_matrix.shape

        fwd_cost, fwd_matched = self._ordered_match(distance_matrix)
        rev_cost, rev_matched = self._ordered_match(distance_matrix[::-1])
        # Reversed matches are in flipped-row space; map back to original indices.
        rev_matched = {m - 1 - i for i in rev_matched}

        if rev_cost < fwd_cost:
            matched_indices, chosen = rev_matched, "reversed"
        else:
            matched_indices, chosen = fwd_matched, "forward"

        unmatched_points = [
            points_large[i] for i in range(m) if i not in matched_indices
        ]

        self.logger.info(
            f"Order-preserving matching ({chosen}): "
            f"{len(matched_indices)} matched, {len(unmatched_points)} to remove"
        )
        for idx in range(m):
            status = "matched" if idx in matched_indices else "REMOVE"
            min_dist = float(np.min(distance_matrix[idx, :]))
            self.logger.info(f"  Point {points_large[idx]}: min_dist={min_dist:.4f} [{status}]")

        return unmatched_points

    @staticmethod
    def _ordered_match(distance_matrix: np.ndarray) -> Tuple[float, Set[int]]:
        """Minimum-cost monotone matching of every column to a subsequence of rows.

        Returns (total_matched_cost, matched_row_indices).
        """
        m, n = distance_matrix.shape

        # dp[i][j] = min cost to match first j cols using a subset of first i rows
        dp = np.full((m + 1, n + 1), np.inf)
        dp[:, 0] = 0.0
        for i in range(1, m + 1):
            for j in range(1, min(i, n) + 1):
                skip = dp[i - 1][j]
                match = dp[i - 1][j - 1] + distance_matrix[i - 1][j - 1]
                dp[i][j] = min(skip, match)

        matched_indices: Set[int] = set()
        i, j = m, n
        while j > 0:
            if i == 0:
                break
            if dp[i][j] == dp[i - 1][j]:
                i -= 1
            else:
                matched_indices.add(i - 1)
                i -= 1
                j -= 1

        return float(dp[m][n]), matched_indices