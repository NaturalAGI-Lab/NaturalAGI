import networkx as nx


import logging
from typing import Any, Dict, List, Optional, Set


class NodeSimilarityCalculator:
    """
    Calculates similarity between nodes based on their properties and types.
    """

    # List of properties to ignore when comparing nodes
    IGNORE_PROPERTIES = [
        "id",
        "image_id",
        "session_id",
        "visualization",
        "uuid",
        "concept_id",
        "labels",
        "direction_sequence_index",
        "half_plane",
        "x1",
        "x2",
        "y1",
        "y2",
        "length",
    ]

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def calculate_similarity_matrix(
        self, graph1: nx.Graph, graph2: nx.Graph, path1: List[Any], path2: List[Any]
    ) -> List[List[float]]:
        """
        Calculate similarity scores between nodes in two paths.

        Args:
            graph1: First graph
            graph2: Second graph
            path1: First path
            path2: Second path

        Returns:
            2D matrix of similarity scores (higher = more similar)
        """
        # Initialize similarity matrix
        similarity_matrix = [
            [0.0 for _ in range(len(path2))] for _ in range(len(path1))
        ]

        # Calculate similarity for each node pair
        for i, node1 in enumerate(path1):
            for j, node2 in enumerate(path2):
                similarity_matrix[i][j] = self.calculate_node_similarity(
                    graph1, graph2, node1, node2
                )

        return similarity_matrix

    def calculate_node_similarity(
        self,
        graph1: nx.Graph,
        graph2: nx.Graph,
        node1: Any,
        node2: Any,
        include_properties: Optional[Set[str]] = None,
    ) -> float:
        """
        Calculate similarity between two nodes based on their properties and structural role.

        Args:
            graph1: First graph
            graph2: Second graph
            node1: First node
            node2: Second node

        Returns:
            Similarity score between 0 and 1
        """
        # Get node data
        node1_data = graph1.nodes[node1]
        node2_data = graph2.nodes[node2]

        # 1. Type compatibility
        node1_types = node1_data.get("labels", [])
        node2_types = node2_data.get("labels", [])

        # Check if they share any types
        common_types = set(node1_types).intersection(set(node2_types))
        if not common_types:
            return 0.0  # Different types, no similarity

        # 2. Property similarity
        return self._calculate_property_similarity(
            node1_data, node2_data, include_properties
        )

    def _calculate_property_similarity(
        self,
        props1: Dict[str, Any],
        props2: Dict[str, Any],
        include_properties: Optional[Set[str]] = None,
    ) -> float:
        """
        Calculate similarity between two sets of properties.

        Args:
            props1: Properties of first node
            props2: Properties of second node

        Returns:
            Similarity score between 0 and 1
        """
        if include_properties:
            relevant_props = list(include_properties)
        else:
            # Get all properties from both nodes
            all_props = set(props1.keys()) | set(props2.keys())

            # Filter out ignored properties
            relevant_props = [p for p in all_props if p not in self.IGNORE_PROPERTIES]

        if not relevant_props:
            return 0.0

        matching_props = 0
        total_props = len(relevant_props)
        skipped_props = 0  # Count props not present in both nodes

        for prop in relevant_props:
            # Skip properties that don't exist in both nodes
            if prop not in props1 or prop not in props2:
                skipped_props += 1
                continue

            val1 = props1[prop]
            val2 = props2[prop]

            # Get similarity score for this property
            similarity_score = self._are_property_values_similar(val1, val2)
            matching_props += similarity_score

        effective_total_props = total_props - skipped_props
        if effective_total_props > 0:
            # Normalize the summed scores by the number of properties actually compared
            return matching_props / effective_total_props
        return 0.0

    def _are_property_values_similar(self, val1: Any, val2: Any) -> float:
        """
        Compare two property values and return a similarity score between 0.0 and 1.0.

        Args:
            val1: First value
            val2: Second value

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Exact match
        if val1 == val2:
            return 1.0

        # Number to range comparison
        is_num1 = self._is_numeric(val1)
        is_range2 = self._is_range_object(val2)
        if is_num1 and is_range2:
            return self._compare_number_to_range(float(val1), val2)

        # Range to number comparison
        is_range1 = self._is_range_object(val1)
        is_num2 = self._is_numeric(val2)
        if is_range1 and is_num2:
            return self._compare_number_to_range(float(val2), val1)

        # Numeric comparison (both simple numbers)
        if is_num1 and is_num2:
            try:
                num1 = float(val1)
                num2 = float(val2)
                # Use max absolute value for normalization, avoid division by zero
                denominator = max(abs(num1), abs(num2), 1.0)
                # Calculate relative difference
                diff = abs(num1 - num2) / denominator
                # Similarity is 1 - relative difference (capped at 0)
                return max(0.0, 1.0 - diff)
            except (ValueError, TypeError):
                # Should not happen if _is_numeric is correct, but handle defensively
                return 0.0

        # String comparison (exact match already handled)
        if isinstance(val1, str) and isinstance(val2, str):
            # For now, only exact matches count (handled above).
            # Could add Levenshtein distance or other metrics here later.
            return 0.0

        # List comparison (Jaccard similarity)
        if isinstance(val1, list) and isinstance(val2, list):
            set1 = set(val1)
            set2 = set(val2)
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            if union == 0:
                return 1.0  # Both lists are empty
            return intersection / union

        # Dictionary comparison - for non-range dictionaries
        if isinstance(val1, dict) and isinstance(val2, dict):
            # Skip if either is a range object as we've handled those cases above
            if self._is_range_object(val1) or self._is_range_object(val2):
                return 0.0

            # Compare keys and values for regular dictionaries
            common_keys = set(val1.keys()) & set(val2.keys())
            if not common_keys:
                return 0.0

            # Compare values of common keys
            similarity_sum = 0.0
            for key in common_keys:
                key_similarity = self._are_property_values_similar(val1[key], val2[key])
                similarity_sum += key_similarity

            return similarity_sum / len(common_keys)

        # Different types or no similarity found
        return 0.0

    def _is_range_object(self, val: Any) -> bool:
        """
        Check if a value is a range object with min, max, and center.

        Args:
            val: Value to check

        Returns:
            True if val is a range object, False otherwise
        """
        return (
            isinstance(val, dict)
            and all(k in val for k in ["min", "max", "center"])
            and self._is_numeric(val["min"])
            and self._is_numeric(val["max"])
            and self._is_numeric(val["center"])
        )

    def _compare_number_to_range(self, num: float, range_obj: Dict[str, Any]) -> float:
        """
        Compare a single numeric value to a range object.

        Args:
            num: Numeric value
            range_obj: Range object with min, max, and center

        Returns:
            Similarity score between 0.0 and 1.0
        """
        min_val = float(range_obj["min"])
        max_val = float(range_obj["max"])
        center = float(range_obj["center"])

        # If range has zero width, compare directly to center
        range_width = max_val - min_val
        if range_width <= 0:
            # If num equals center, perfect match
            if num == center:
                return 1.0
            # Otherwise, use relative difference
            denominator = max(abs(num), abs(center), 1.0)
            diff = abs(num - center) / denominator
            return max(0.0, 1.0 - diff)

        # Check if number is within range
        if min_val <= num <= max_val:
            # Calculate position within range (0.0 to 1.0)
            position = (num - min_val) / range_width
            # Calculate center position within range
            center_position = (center - min_val) / range_width
            # Calculate how close the number is to the center (1.0 if at center, 0.0 if at edge)
            # Convert the distance to a similarity score
            distance_from_center = abs(position - center_position)
            max_distance = max(center_position, 1.0 - center_position)
            if max_distance > 0:
                normalized_distance = distance_from_center / max_distance
                return max(0.0, 1.0 - normalized_distance)
            return 1.0

        # Number is outside range
        # Calculate distance from range boundary relative to range width
        if num < min_val:
            distance = min_val - num
        else:  # num > max_val
            distance = num - max_val

        # Calculate similarity based on distance outside range
        # The further outside the range, the lower the similarity
        # Normalize by range width to get meaningful scaling
        normalized_distance = distance / range_width
        return max(0.0, 1.0 - min(normalized_distance, 1.0))

    # TODO: remove this function
    def _get_node_types(self, node_data: Dict[str, Any]) -> List[str]:
        """
        Get the types/labels of a node.

        Args:
            node_data: Node data dictionary

        Returns:
            List of node type strings
        """
        labels = node_data.get("labels", [])

        if not isinstance(labels, list):
            if isinstance(labels, set):
                labels = list(labels)
            else:
                labels = [labels]

        return labels

    def calculate_coordinate_similarity(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> float:
        """
        Calculate similarity based solely on spatial coordinates.
        This is a standalone metric that can be used separately from general node similarity.
        Handles both direct numeric coordinates and range-based coordinates.

        Args:
            graph1: First graph
            graph2: Second graph
            node1: Node ID in first graph
            node2: Node ID in second graph

        Returns:
            Coordinate similarity score between 0 and 1
        """
        node1_data = graph1.nodes[node1]
        node2_data = graph2.nodes[node2]

        # Check for x,y coordinates
        x_sim = self._compare_specific_coordinate(node1_data, node2_data, "x")
        y_sim = self._compare_specific_coordinate(node1_data, node2_data, "y")

        # Check for normalized coordinates if regular ones are missing
        if x_sim is None:
            x_sim = self._compare_specific_coordinate(
                node1_data, node2_data, "normalized_x"
            )
        if y_sim is None:
            y_sim = self._compare_specific_coordinate(
                node1_data, node2_data, "normalized_y"
            )

        # If we have both coordinates, average them
        if x_sim is not None and y_sim is not None:
            return (x_sim + y_sim) / 2

        # If we have only one coordinate, use it
        elif x_sim is not None:
            return x_sim
        elif y_sim is not None:
            return y_sim

        # No coordinates available
        return 0.0

    def _compare_specific_coordinate(
        self, node1_data: Dict[str, Any], node2_data: Dict[str, Any], coord_name: str
    ) -> Optional[float]:
        """
        Compare a specific coordinate (x or y) between two nodes.

        Args:
            node1_data: First node data
            node2_data: Second node data
            coord_name: Name of coordinate property ('x', 'y', 'normalized_x', etc.)

        Returns:
            Similarity score between 0 and 1, or None if coordinate is missing
        """
        # Check if both nodes have the coordinate
        if coord_name not in node1_data or coord_name not in node2_data:
            return None

        val1 = node1_data[coord_name]
        val2 = node2_data[coord_name]

        # Case 1: Both are simple numeric values
        if self._is_numeric(val1) and self._is_numeric(val2):
            try:
                num1 = float(val1)
                num2 = float(val2)
                # Calculate similarity based on relative difference
                diff = abs(num1 - num2) / max(max(abs(num1), abs(num2)), 1.0)
                return max(0.0, 1.0 - min(diff, 1.0))
            except (ValueError, TypeError):
                return None

        # Case 2: Both are range maps
        elif isinstance(val1, dict) and isinstance(val2, dict):
            # Check if they have the expected structure
            if all(k in val1 for k in ["min", "max", "center"]) and all(
                k in val2 for k in ["min", "max", "center"]
            ):
                # Compare centers
                if self._is_numeric(val1["center"]) and self._is_numeric(
                    val2["center"]
                ):
                    center1 = float(val1["center"])
                    center2 = float(val2["center"])
                    center_diff = abs(center1 - center2) / max(
                        max(abs(center1), abs(center2)), 1.0
                    )
                    center_similarity = max(0.0, 1.0 - min(center_diff, 1.0))
                else:
                    return None

                # Check if min/max are numeric
                if not (
                    self._is_numeric(val1["min"])
                    and self._is_numeric(val1["max"])
                    and self._is_numeric(val2["min"])
                    and self._is_numeric(val2["max"])
                ):
                    return center_similarity

                # Compare overlapping ranges
                min1, max1 = float(val1["min"]), float(val1["max"])
                min2, max2 = float(val2["min"]), float(val2["max"])

                # Calculate overlap between ranges
                overlap_start = max(min1, min2)
                overlap_end = min(max1, max2)
                overlap = max(0, overlap_end - overlap_start)

                # Calculate range sizes
                range1 = max1 - min1
                range2 = max2 - min2

                # Overlap ratio (how much the ranges overlap relative to their sizes)
                if range1 > 0 and range2 > 0:
                    overlap_ratio = overlap / max(range1, range2)
                else:
                    overlap_ratio = 1.0 if center_similarity > 0.9 else 0.0

                # Combine center similarity and overlap ratio
                return 0.6 * center_similarity + 0.4 * overlap_ratio
            else:
                # Not the expected range structure
                return None

        # Case 3: One is numeric and one is a range
        elif self._is_numeric(val1) and isinstance(val2, dict):
            if (
                all(k in val2 for k in ["min", "max"])
                and self._is_numeric(val2["min"])
                and self._is_numeric(val2["max"])
            ):
                num = float(val1)
                min2, max2 = float(val2["min"]), float(val2["max"])
                # Check if the number is within the range
                if min2 <= num <= max2:
                    # Calculate how close it is to the center
                    range_size = max2 - min2
                    if range_size > 0:
                        position = (num - min2) / range_size  # 0 to 1
                        # How close to center (0.5)? 1 = at center, 0 = at edge
                        return 1.0 - abs(position - 0.5) * 2
                    else:
                        return 1.0 if num == min2 else 0.0
                else:
                    # Calculate distance outside range relative to range size
                    if num < min2:
                        dist = min2 - num
                    else:
                        dist = num - max2
                    range_size = max2 - min2
                    if range_size > 0:
                        relative_dist = dist / range_size
                        return max(0.0, 1.0 - min(relative_dist, 1.0))
                    else:
                        return 0.0
            else:
                return None

        elif isinstance(val1, dict) and self._is_numeric(val2):
            # Swap arguments and reuse the logic above
            return self._compare_specific_coordinate(
                {"x": val2} if coord_name == "x" else {"y": val2},
                {"x": val1} if coord_name == "x" else {"y": val1},
                coord_name,
            )

        # Case 4: Unknown types
        else:
            return None

    def _is_numeric(self, val: Any) -> bool:
        """
        Check if a value can be converted to a number.

        Args:
            val: Value to check

        Returns:
            True if value can be converted to a number, False otherwise
        """
        try:
            float(val)
            return True
        except (ValueError, TypeError):
            return False
