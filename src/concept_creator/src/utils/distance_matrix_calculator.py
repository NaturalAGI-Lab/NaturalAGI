import logging
from typing import List, Any, Optional, Set
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

                squared_diffs = [
                    (coord_large - coord_small) ** 2
                    for coord_large, coord_small in zip(coordinates_large, coordinates_small)
                ]
                distance = np.sqrt(sum(squared_diffs))
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
            if min_distances[i] > threshold:
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
        """Find points for a difference in the distance matrix.

        Args:
            distance_matrix (np.ndarray): Distance matrix
            points (List[Any]): List of point IDs corresponding to the rows/columns of the distance matrix
            difference (int): Difference in number of points
            axis (int, optional): 0 for columns, 1 for rows

        Returns:
            List[Any]: List of point IDs for the difference
        """
        if difference <= 0:
            return []
            
        if distance_matrix.size == 0:
            self.logger.error("Distance matrix is empty. Raising error.")
            raise ValueError("Distance matrix is empty.")
            
        row_ind, col_ind = linear_sum_assignment(distance_matrix)
    
        if axis == 0:
            matched_indices = set(col_ind)
            all_indices = set(range(distance_matrix.shape[1]))
        else:
            matched_indices = set(row_ind)
            all_indices = set(range(distance_matrix.shape[0]))
        
        unmatched_indices = all_indices - matched_indices
        points_for_difference = [points[i] for i in unmatched_indices]
        
        self.logger.debug(f"Points identified for difference: {points_for_difference}")
        return points_for_difference