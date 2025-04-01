import logging
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional, Set

from concept_creator.node_similarity_calculator import NodeSimilarityCalculator
from property_handlers.property_handler_manager import PropertyHandlerManager
from concept_creator.critical_point_preprocessor import CriticalPointPreprocessor


class GraphMinorFinder:
    """
    Finds maximum common minor between graphs by comparing critical points
    and creating intersection graphs.

    This implements the core algorithm for concept formation in NaturalAGI by finding
    the intersection graph from multiple training samples.
    """

    def __init__(self):
        self.prop_manager = PropertyHandlerManager()
        self.similarity_calculator = NodeSimilarityCalculator()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.preprocessor = CriticalPointPreprocessor()

        # Define the type reduction hierarchy - only for vector types
        # Critical point reductions are now handled by the preprocessor
        self.type_reduction_map = {
            "VerticalVector": "Vector",
            "HorizontalVector": "Vector",
        }

    def find_max_common_minor(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> nx.Graph:
        """
        Find the maximum common minor between two graphs by:
        1. Preprocessing graphs to ensure critical point compatibility
        2. Identifying critical points in both.
        3. Matching critical points by type compatibility (with type reduction).
        4. Matching paths between compatible critical points.
        5. Reducing the structure of matched paths to the common minimum.
        6. Merging properties of matched nodes.

        Args:
            concept_graph: The current concept graph.
            image_graph: The new image graph (training sample).

        Returns:
            The updated concept graph representing the merged structure.
        """
        self.logger.info(
            f"Finding maximum common minor between graphs: concept ({len(concept_graph.nodes)} nodes) and image ({len(image_graph.nodes)} nodes)"
        )

        # 1. Preprocess graphs to ensure critical point compatibility
        preprocessed_concept, preprocessed_image = self.preprocessor.preprocess_graphs(
            concept_graph, image_graph
        )

        # 2. Identify critical points (after preprocessing)
        concept_critical_points = self._identify_critical_points(preprocessed_concept)
        image_critical_points = self._identify_critical_points(preprocessed_image)

        concept_critical_count = sum(len(p) for p in concept_critical_points.values())
        image_critical_count = sum(len(p) for p in image_critical_points.values())

        self.logger.debug(
            f"Critical points in preprocessed concept graph: {concept_critical_count}"
        )
        self.logger.debug(
            f"Critical points in preprocessed image graph: {image_critical_count}"
        )

        # Detailed logging of critical points by type
        for cp_type, points in concept_critical_points.items():
            self.logger.debug(f"Concept graph {cp_type} count: {len(points)}")
        for cp_type, points in image_critical_points.items():
            self.logger.debug(f"Image graph {cp_type} count: {len(points)}")

        # 3. Find start points
        start_c = self._find_start_point(preprocessed_concept, concept_critical_points)
        start_i = self._find_start_point(preprocessed_image, image_critical_points)
        if not start_c or not start_i:
            self.logger.error(
                "Start point not found in one or both graphs. Cannot proceed."
            )
            raise ValueError("Start point not found in one or both graphs.")
        self.logger.info(f"Using start points: concept={start_c}, image={start_i}")

        # 4. Perform critical points matching - create map from concept critical points to image critical points
        critical_point_mapping = self._match_critical_points(
            preprocessed_concept,
            preprocessed_image,
            concept_critical_points,
            image_critical_points,
        )

        # Log the resulting mapping of critical points
        self.logger.info(
            f"Successfully mapped {len(critical_point_mapping)} out of {concept_critical_count} concept critical points"
        )

        # If mapping is empty or doesn't include start points, we can't proceed
        if not critical_point_mapping or start_c not in critical_point_mapping:
            self.logger.error("Failed to map essential critical points between graphs")
            if start_c not in critical_point_mapping:
                self.logger.error(f"Start point {start_c} could not be mapped")
            if start_i not in critical_point_mapping.values():
                self.logger.error(f"Start point {start_i} was not mapped to")
            raise ValueError("Critical point mapping failed - cannot find common minor")

        # 5. Create result graph
        result_graph = nx.Graph()

        # 6. Build the reduced intersection graph starting from the start points
        self._build_reduced_intersection(
            result_graph,
            preprocessed_concept,
            preprocessed_image,
            start_c,
            start_i,
            concept_critical_points,
            image_critical_points,
            critical_point_mapping,
            set(),  # Visited critical point pairs tracking
        )

        self.logger.info(
            f"Completed common minor finding. Result graph has {len(result_graph.nodes)} nodes and {len(result_graph.edges)} edges."
        )
        return result_graph

    def _identify_critical_points(self, graph: nx.Graph) -> Dict[str, List[Any]]:
        """
        Identify critical points in a graph (intersection points, corner points, end points, start points).
        Delegates to the preprocessor to ensure consistency.

        Args:
            graph: The graph to analyze

        Returns:
            Dictionary mapping point types to lists of node IDs
        """
        self.logger.debug(
            f"Identifying critical points in graph with {len(graph.nodes)} nodes"
        )
        # Delegate to the preprocessor's implementation
        critical_points = self.preprocessor._identify_critical_points(graph)

        self.logger.debug(
            f"Found critical points: {', '.join(f'{k}={len(v)}' for k, v in critical_points.items())}"
        )
        return critical_points

    def _find_start_point(
        self, graph: nx.Graph, critical_points: Dict[str, List[Any]]
    ) -> Any:
        """
        Find the start point in a graph. If multiple start points exist, pick the first one.

        StartPoints are essential anchor points for matching across samples and cannot be reduced.

        Args:
            graph: The graph to analyze
            critical_points: Dictionary of critical points by type

        Returns:
            Node ID of the start point, or None if not found
        """
        start_points = critical_points.get("StartPoint", [])
        if start_points:
            self.logger.debug(f"Found start point: {start_points[0]}")
            return start_points[0]

        self.logger.warning("No start point found")
        return None

    def _reduce_vector_type(self, vector_type: str) -> str:
        """
        Reduce a vector type to a more general one according to defined reduction rules.

        Type reduction hierarchy:
        - VerticalVector -> Vector
        - HorizontalVector -> Vector

        Args:
            vector_type: The original vector type

        Returns:
            The reduced vector type, or the original if no reduction is possible
        """
        return self.type_reduction_map.get(vector_type, vector_type)

    def _match_critical_points(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        concept_critical_points: Dict[str, List[Any]],
        image_critical_points: Dict[str, List[Any]],
    ) -> Dict[Any, Any]:
        """
        Match critical points between concept and image graphs based on compatibility.
        Since the preprocessor has already aligned the critical point counts,
        this method focuses on finding the best matching pairs based on similarity.

        Args:
            concept_graph: Concept graph
            image_graph: Image graph
            concept_critical_points: Dictionary of critical point types to nodes in concept graph
            image_critical_points: Dictionary of critical point types to nodes in image graph

        Returns:
            Dictionary mapping concept critical points to image critical points
        """
        # Dictionary to store the mapping from concept critical points to image critical points
        critical_point_mapping = {}

        # Log critical point counts (which should now match between graphs)
        concept_critical_count = sum(len(p) for p in concept_critical_points.values())
        image_critical_count = sum(len(p) for p in image_critical_points.values())

        self.logger.info(
            f"Matching {concept_critical_count} concept critical points to {image_critical_count} image critical points"
        )

        for cp_type, concept_points in concept_critical_points.items():
            self.logger.debug(
                f"Matching critical points of type {cp_type}: {len(concept_points)} in concept, {len(image_critical_points.get(cp_type, []))} in image"
            )
            image_points = image_critical_points.get(cp_type, [])

            # The preprocessor should have ensured that counts match, but let's verify
            if len(concept_points) != len(image_points):
                self.logger.warning(
                    f"Critical point count mismatch for {cp_type} after preprocessing: {len(concept_points)} vs {len(image_points)}"
                )

            # Calculate similarity between all points of this type
            available_image_points = set(image_points)

            # Handle each concept point
            for concept_cp in concept_points:
                best_match = None
                best_score = 0

                # Find the best match among available image points
                for image_cp in available_image_points:
                    similarity = self._calculate_critical_point_similarity(
                        concept_graph, image_graph, concept_cp, image_cp
                    )

                    if similarity > best_score:
                        best_score = similarity
                        best_match = image_cp

                # Use a good match if found
                if (
                    best_match and best_score > 0.3
                ):  # Lower threshold since preprocess aligned points
                    critical_point_mapping[concept_cp] = best_match
                    available_image_points.remove(best_match)
                    self.logger.debug(
                        f"Matched {cp_type} {concept_cp} to {best_match} with score {best_score:.2f}"
                    )
                else:
                    # Just pick the first available one if none has good similarity
                    if available_image_points:
                        fallback_match = next(iter(available_image_points))
                        critical_point_mapping[concept_cp] = fallback_match
                        available_image_points.remove(fallback_match)
                        self.logger.debug(
                            f"Fallback match for {cp_type} {concept_cp} to {fallback_match} (no good similarity)"
                        )
                    else:
                        self.logger.warning(
                            f"Could not find match for {cp_type} {concept_cp} - no available points left"
                        )

        # Log the results of matching
        self.logger.info(
            f"Successfully mapped {len(critical_point_mapping)} out of {concept_critical_count} concept critical points"
        )

        # Log which points were not matched (should be none if preprocessor worked correctly)
        unmapped_points = set()
        for points in concept_critical_points.values():
            for cp in points:
                if cp not in critical_point_mapping:
                    unmapped_points.add(cp)

        if unmapped_points:
            self.logger.warning(f"Failed to map {len(unmapped_points)} critical points")
            for cp in unmapped_points:
                for cp_type, points in concept_critical_points.items():
                    if cp in points:
                        self.logger.warning(f"  - Unmapped {cp_type}: {cp}")

        return critical_point_mapping

    def _calculate_critical_point_similarity(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> float:
        """
        Calculate similarity between two critical points based on:
        1. Type compatibility
        2. Properties (position, angle, etc.)
        3. Neighborhood structure

        Args:
            graph1: First graph
            graph2: Second graph
            node1: Node ID in first graph
            node2: Node ID in second graph

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not self._check_node_type_compatibility(graph1, graph2, node1, node2):
            return 0.0

        # Extract node data
        node1_data = graph1.nodes[node1]
        node2_data = graph2.nodes[node2]

        # Compare spatial properties
        position_similarity = 0.0
        if "normalized_x" in node1_data and "normalized_x" in node2_data:
            x1, y1 = node1_data.get("normalized_x", 0), node1_data.get(
                "normalized_y", 0
            )
            x2, y2 = node2_data.get("normalized_x", 0), node2_data.get(
                "normalized_y", 0
            )

            # Euclidean distance, converted to similarity (1.0 when identical, decreasing as distance increases)
            distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            position_similarity = max(0, 1.0 - min(distance, 1.0))

        # Compare angle if available
        angle_similarity = 0.0
        if "angle" in node1_data and "angle" in node2_data:
            angle1 = node1_data["angle"]
            angle2 = node2_data["angle"]

            # Angular distance, normalized to similarity
            angle_diff = abs(angle1 - angle2)
            angle_diff = min(angle_diff, 360 - angle_diff)  # Consider the shorter arc
            angle_similarity = max(0, 1.0 - angle_diff / 180.0)

        # Compare segments if available
        segment_similarity = 0.0
        if "segments" in node1_data and "segments" in node2_data:
            segments1 = set(node1_data["segments"])
            segments2 = set(node2_data["segments"])

            # Jaccard similarity of segments
            if segments1 or segments2:
                segment_similarity = len(segments1.intersection(segments2)) / len(
                    segments1.union(segments2)
                )

        # Combine similarities with weights
        # Position is most important, then segments, then angle
        if angle_similarity and segment_similarity:
            combined_similarity = (
                0.5 * position_similarity
                + 0.3 * segment_similarity
                + 0.2 * angle_similarity
            )
        elif segment_similarity:
            combined_similarity = 0.7 * position_similarity + 0.3 * segment_similarity
        elif angle_similarity:
            combined_similarity = 0.8 * position_similarity + 0.2 * angle_similarity
        else:
            combined_similarity = position_similarity

        return combined_similarity

    def _build_reduced_intersection(
        self,
        result_graph: nx.Graph,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        start_c: Any,
        start_i: Any,
        concept_critical_points: Dict[str, List[Any]],
        image_critical_points: Dict[str, List[Any]],
        critical_point_mapping: Dict[Any, Any],
        visited_critical_pairs: Set[Tuple[Any, Any]],
    ) -> None:
        """
        Builds the intersection graph by matching paths between critical points,
        reducing substructures, and merging properties.

        Args:
            result_graph: The result graph being constructed.
            concept_graph: The concept graph.
            image_graph: The image graph.
            start_c: Starting critical point node ID in the concept graph.
            start_i: Starting critical point node ID in the image graph.
            concept_critical_points: Dictionary of critical points in the concept graph.
            image_critical_points: Dictionary of critical points in the image graph.
            critical_point_mapping: Mapping of concept critical points to image critical points.
            visited_critical_pairs: Set of (concept_cp, image_cp) pairs already processed.
        """
        queue = [(start_c, start_i)]
        processed_pairs = {(start_c, start_i)}  # Tracks pairs added to queue

        # Track which nodes have been matched to prevent reusing nodes in multiple path matches
        matched_nodes_c = set()  # Concept graph nodes that have been matched
        matched_nodes_i = set()  # Image graph nodes that have been matched

        # Critical points are allowed to be reused in multiple paths
        # We'll track them separately to avoid over-constraining
        critical_points_c = {
            node for points in concept_critical_points.values() for node in points
        }
        critical_points_i = {
            node for points in image_critical_points.values() for node in points
        }

        # Get all matched critical points from concept graph
        matched_critical_points_c = set(critical_point_mapping.keys())

        # Filter paths to only include matched critical points
        self.logger.info(
            f"Processing {len(matched_critical_points_c)} matched critical points out of {len(critical_points_c)} total"
        )

        while queue:
            current_c, current_i = queue.pop(0)
            pair_id = (current_c, current_i)  # Use exact pair for visited tracking

            if pair_id in visited_critical_pairs:
                continue
            visited_critical_pairs.add(pair_id)

            self.logger.debug(
                f"Processing critical point pair: concept={current_c}, image={current_i}"
            )

            # Ensure the critical point pair is compatible
            # (this should be guaranteed by our critical_point_mapping)
            if not self._check_node_type_compatibility(
                concept_graph, image_graph, current_c, current_i
            ):
                self.logger.warning(
                    f"Critical points {current_c}, {current_i} not compatible. This shouldn't happen with proper mapping. Skipping."
                )
                continue

            # Track these critical points as matched but allow reuse
            matched_nodes_c.add(current_c)
            matched_nodes_i.add(current_i)

            # Add the critical point to the result graph if not already present
            if current_c not in result_graph:
                merged_props = self.prop_manager.process_node_properties(
                    {}, concept_graph.nodes[current_c], image_graph.nodes[current_i]
                )
                result_graph.add_node(current_c, **merged_props)
                self.logger.debug(f"Added critical node {current_c} to result graph")

            # Find all paths starting from current_c to next critical points
            paths_c = self._find_paths_to_next_critical(
                concept_graph, current_c, concept_critical_points
            )

            # Filter paths to only include destination critical points that were matched
            paths_c = [
                (end_c, path_c)
                for end_c, path_c in paths_c
                if end_c in matched_critical_points_c
            ]

            # Find all paths starting from current_i to next critical points
            paths_i = self._find_paths_to_next_critical(
                image_graph, current_i, image_critical_points
            )

            self.logger.debug(
                f"Found {len(paths_c)} paths from {current_c}, {len(paths_i)} paths from {current_i}"
            )

            # Find optimal path matches based on critical point mapping
            path_pairs = self._find_optimal_path_matches_with_mapping(
                concept_graph,
                image_graph,
                paths_c,
                paths_i,
                matched_nodes_c,
                matched_nodes_i,
                critical_point_mapping,
            )

            for (next_c, path_c), (next_i, path_i) in path_pairs:
                self.logger.debug(
                    f"Found optimal path pair: ({current_c} -> {next_c}) and ({current_i} -> {next_i})"
                )

                # Create the reduced path in the result graph
                intermediate_c_nodes = set(
                    path_c[1:-1]
                )  # Exclude start/end critical points
                intermediate_i_nodes = set(path_i[1:-1])

                # Mark non-critical point nodes as matched to prevent reuse
                for node in intermediate_c_nodes:
                    if node not in critical_points_c:
                        matched_nodes_c.add(node)
                for node in intermediate_i_nodes:
                    if node not in critical_points_i:
                        matched_nodes_i.add(node)

                self._create_reduced_path_in_result(
                    result_graph,
                    concept_graph,
                    image_graph,
                    current_c,
                    next_c,
                    path_c,
                    current_i,
                    next_i,
                    path_i,
                )

                # Add the next pair to the queue if not already visited or queued
                next_pair = (next_c, next_i)
                if (
                    next_pair not in visited_critical_pairs
                    and next_pair not in processed_pairs
                ):
                    self.logger.debug(
                        f"Adding next critical pair to queue: {next_pair}"
                    )
                    queue.append(next_pair)
                    processed_pairs.add(next_pair)

    def _find_optimal_path_matches_with_mapping(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        paths_c: List[Tuple[Any, List[Any]]],
        paths_i: List[Tuple[Any, List[Any]]],
        matched_nodes_c: Set[Any],
        matched_nodes_i: Set[Any],
        critical_point_mapping: Dict[Any, Any],
    ) -> List[Tuple[Tuple[Any, List[Any]], Tuple[Any, List[Any]]]]:
        """
        Finds optimal matches between paths using pre-computed critical point mapping.
        Prioritizes paths connecting mapped critical points.

        Args:
            concept_graph: The concept graph
            image_graph: The image graph
            paths_c: List of (end_point, path) tuples from concept graph
            paths_i: List of (end_point, path) tuples from image graph
            matched_nodes_c: Set of already matched concept graph nodes
            matched_nodes_i: Set of already matched image graph nodes
            critical_point_mapping: Mapping of concept critical points to image critical points

        Returns:
            List of ((end_c, path_c), (end_i, path_i)) pairs representing matched paths
        """
        # First use the critical point mapping to create matched pairs
        matched_pairs = []
        used_ends_c = set()
        used_ends_i = set()

        # Priority 1: Match paths where both endpoints are already mapped to each other
        for end_c, path_c in paths_c:
            if end_c in critical_point_mapping:
                mapped_end_i = critical_point_mapping[end_c]

                # Find the corresponding path in image_graph
                matching_path_i = None
                for end_i, path_i in paths_i:
                    if end_i == mapped_end_i:
                        matching_path_i = (end_i, path_i)
                        break

                if matching_path_i:
                    end_i, path_i = matching_path_i

                    # Calculate path similarity score to ensure they're structurally similar
                    path_similarity = self._calculate_path_similarity(
                        concept_graph, image_graph, path_c, path_i
                    )

                    conflict_c = sum(1 for n in path_c[1:-1] if n in matched_nodes_c)
                    conflict_i = sum(1 for n in path_i[1:-1] if n in matched_nodes_i)

                    # Add conflict penalty but with a lower weight for mapped critical points
                    conflict_penalty = (conflict_c + conflict_i) * 0.3
                    adjusted_similarity = path_similarity - conflict_penalty

                    # Use a lower threshold for critical point mapped paths
                    if adjusted_similarity > 0.2:  # Lower threshold for mapped paths
                        matched_pairs.append(((end_c, path_c), (end_i, path_i)))
                        used_ends_c.add(end_c)
                        used_ends_i.add(end_i)

                        self.logger.debug(
                            f"Matched path {end_c}-{end_i} from critical point mapping with similarity {adjusted_similarity:.2f}"
                        )

        # For remaining paths, use the similarity-based approach
        remaining_paths_c = [
            (end_c, path_c) for end_c, path_c in paths_c if end_c not in used_ends_c
        ]
        remaining_paths_i = [
            (end_i, path_i) for end_i, path_i in paths_i if end_i not in used_ends_i
        ]

        # Priority 2: Match the rest based on node compatibility and path similarity
        compatible_ends = []
        for end_c, path_c in remaining_paths_c:
            for end_i, path_i in remaining_paths_i:
                # Check if endpoints are compatible
                if self._check_node_type_compatibility(
                    concept_graph, image_graph, end_c, end_i
                ):
                    # Calculate path similarity score
                    path_similarity = self._calculate_path_similarity(
                        concept_graph, image_graph, path_c, path_i
                    )

                    # Check for conflicts with already matched nodes
                    conflict_c = sum(1 for n in path_c[1:-1] if n in matched_nodes_c)
                    conflict_i = sum(1 for n in path_i[1:-1] if n in matched_nodes_i)

                    # Penalize paths with conflicts
                    conflict_penalty = (conflict_c + conflict_i) * 0.5
                    adjusted_similarity = path_similarity - conflict_penalty

                    # Only consider paths with reasonable similarity
                    if (
                        adjusted_similarity > 0.3
                    ):  # Threshold for non-mapped path similarity
                        compatible_ends.append(
                            ((end_c, path_c), (end_i, path_i), adjusted_similarity)
                        )

        # Sort by similarity score, highest first
        compatible_ends.sort(key=lambda x: x[2], reverse=True)

        # Greedy algorithm for remaining paths
        for (end_c, path_c), (end_i, path_i), score in compatible_ends:
            # Skip if either endpoint is already used
            if end_c in used_ends_c or end_i in used_ends_i:
                continue

            self.logger.debug(
                f"Matched path {end_c}-{end_i} with similarity score {score:.2f}"
            )

            # Mark these endpoints as used
            used_ends_c.add(end_c)
            used_ends_i.add(end_i)

            # Add to matched pairs
            matched_pairs.append(((end_c, path_c), (end_i, path_i)))

        return matched_pairs

    def _calculate_path_similarity(
        self, graph1: nx.Graph, graph2: nx.Graph, path1: List[Any], path2: List[Any]
    ) -> float:
        """
        Calculates similarity between two paths based on:
        1. Relative length (closer is better)
        2. Node type compatibility

        Args:
            graph1: First graph
            graph2: Second graph
            path1: Path in first graph
            path2: Path in second graph

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Length similarity component (1.0 if equal length, decreasing as difference increases)
        len1, len2 = len(path1), len(path2)
        length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 1.0

        # Node compatibility component
        # Sample key positions in each path and check compatibility
        # Take start, end, and up to 3 intermediate points
        compatible_nodes = 0
        comparisons = 0

        # Always compare start and end
        positions = [0, -1]

        # Add middle point if paths are long enough
        if len1 > 2 and len2 > 2:
            positions.append(len1 // 2)

        # Add quarter and three-quarter points for longer paths
        if len1 > 4 and len2 > 4:
            positions.extend([len1 // 4, 3 * len1 // 4])

        for pos in positions:
            if pos >= len1 or (pos < 0 and abs(pos) > len1):
                continue

            idx1 = pos
            # Map position proportionally to path2
            if pos >= 0:
                idx2 = min(int(pos * len2 / len1), len2 - 1)
            else:
                idx2 = -min(abs(pos), len2)

            node1 = path1[idx1]
            node2 = path2[idx2]

            if self._check_node_type_compatibility(graph1, graph2, node1, node2):
                compatible_nodes += 1
            comparisons += 1

        node_compatibility = compatible_nodes / comparisons if comparisons > 0 else 0.0

        # Combine scores (weight length similarity less than node compatibility)
        similarity = 0.3 * length_ratio + 0.7 * node_compatibility

        return similarity

    def _find_paths_to_next_critical(
        self,
        graph: nx.Graph,
        start_node: Any,
        critical_points: Dict[str, List[Any]],
    ) -> List[Tuple[Any, List[Any]]]:
        """
        Finds all distinct simple paths from a start node to the *nearest* subsequent critical points.

        Args:
            graph: The graph to search within.
            start_node: The critical point node ID to start from.
            critical_points: Dictionary mapping critical point types to lists of node IDs.

        Returns:
            A list of tuples, where each tuple contains (next_critical_point_id, path_nodes_list).
        """
        self.logger.debug(f"Finding paths from critical node {start_node}")
        all_critical = set(
            node for points in critical_points.values() for node in points
        )
        paths_found = []
        visited_globally = {
            start_node
        }  # Keep track of nodes visited across all path searches from this start_node

        for neighbor in graph.neighbors(start_node):
            if neighbor == start_node:  # Avoid self-loops immediately
                continue

            queue = [(neighbor, [start_node, neighbor])]  # (current_node, path_list)
            visited_in_path = {
                start_node,
                neighbor,
            }  # Nodes visited in the current specific path search

            while queue:
                current, path = queue.pop(0)

                # Check if current node is a critical point (and not the start node)
                if current in all_critical:
                    self.logger.debug(f"Found path to critical point {current}: {path}")
                    paths_found.append((current, path))
                    # Mark nodes in this successful path as visited globally
                    # to prevent finding longer paths to the same critical point via these nodes
                    visited_globally.update(path)
                    continue  # Stop searching along this path once a critical point is found

                # Explore neighbors
                for next_node in graph.neighbors(current):
                    # Avoid cycles within the current path and globally visited nodes
                    if (
                        next_node not in visited_in_path
                        and next_node not in visited_globally
                    ):
                        visited_in_path.add(next_node)
                        new_path = path + [next_node]
                        queue.append((next_node, new_path))

        # Filter results: Ensure paths are simple (no node repeats within a path) - though the BFS approach helps
        # The logic above tries to find the shortest paths first implicitly.
        # We might need more robust filtering if multiple paths to the same critical point are found.
        # For now, we assume the BFS finds the relevant shortest paths.
        unique_paths = {}
        for end_node, path in paths_found:
            if end_node not in unique_paths or len(path) < len(
                unique_paths[end_node][1]
            ):
                unique_paths[end_node] = (end_node, path)

        self.logger.debug(f"Found {len(unique_paths)} unique paths from {start_node}")
        return list(unique_paths.values())

    def _check_node_type_compatibility(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> bool:
        """
        Check if two nodes have compatible types.
        Critical point type compatibility is now handled by the preprocessor prior to matching,
        so this method only needs to handle basic type compatibility checks.

        Args:
            graph1: First graph
            graph2: Second graph
            node1: Node in first graph
            node2: Node in second graph

        Returns:
            True if nodes have compatible types, False otherwise
        """
        node1_data = graph1.nodes[node1]
        node2_data = graph2.nodes[node2]

        node1_types = self.similarity_calculator._get_node_types(node1_data)
        node2_types = self.similarity_calculator._get_node_types(node2_data)

        # Check if they share any exact types first
        if set(node1_types) & set(node2_types):
            return True

        # Basic point vs vector compatibility check
        node1_is_point = any("Point" in t for t in node1_types)
        node1_is_vector = any("Vector" in t for t in node1_types)
        node2_is_point = any("Point" in t for t in node2_types)
        node2_is_vector = any("Vector" in t for t in node2_types)

        # Points should match with points, vectors with vectors
        if (node1_is_point and node2_is_vector) or (node1_is_vector and node2_is_point):
            return False

        # All types of points are compatible with each other after preprocessing
        if node1_is_point and node2_is_point:
            return True

        # Check vector type compatibility through reduction
        if node1_is_vector and node2_is_vector:
            # Get reduced vector types
            reduced_node1_vectors = [
                self._reduce_vector_type(t) for t in node1_types if "Vector" in t
            ]
            reduced_node2_vectors = [
                self._reduce_vector_type(t) for t in node2_types if "Vector" in t
            ]

            # Check if any reduced vector types match
            if set(reduced_node1_vectors) & set(reduced_node2_vectors):
                return True

        return False

    def _follow_path_to_next_critical(
        self,
        graph: nx.Graph,
        start_node: Any,
        visited: Set[Any],
        critical_points: Dict[str, List[Any]],
    ) -> Optional[Tuple[Any, List[Any]]]:
        """
        Follow a path in the graph until the next critical point is reached.

        This helps identify segments between critical points for comparison.

        Args:
            graph: The graph to analyze
            start_node: The starting node
            visited: Set of already visited nodes
            critical_points: Dictionary of critical points

        Returns:
            Tuple of (next_critical_point, path_nodes) or None if no path is found
        """
        self.logger.debug(f"Following path from {start_node} to next critical point")

        # All critical points in a flat list
        all_critical = set()
        for points in critical_points.values():
            all_critical.update(points)

        # BFS to find the path to the next critical point
        queue = [(start_node, [start_node], set())]  # (node, path, path_edge_set)
        path_visited = {start_node}

        while queue:
            current, path, path_edge_set = queue.pop(0)

            # Check if current node is a critical point (not the start node)
            if current != start_node and current in all_critical:
                self.logger.debug(
                    f"Found critical point {current} after traversing {len(path)} nodes"
                )
                return current, path

            # Explore neighbors
            for neighbor in graph.neighbors(current):
                # Create an edge identifier (always store edges with smaller node first)
                edge_id = tuple(sorted([current, neighbor]))

                # Skip if we've already traversed this edge or if neighbor is globally visited
                if edge_id in path_edge_set or neighbor in visited:
                    continue

                # Skip if we'd be revisiting a node in the current path (cycle detection)
                if neighbor in path:
                    continue

                if neighbor not in path_visited:
                    path_visited.add(neighbor)
                    new_path = path + [neighbor]
                    new_edge_set = path_edge_set.copy()
                    new_edge_set.add(edge_id)
                    queue.append((neighbor, new_path, new_edge_set))

        self.logger.debug(f"No path to critical point found from {start_node}")
        return None

    def _are_paths_compatible(
        self, graph1: nx.Graph, graph2: nx.Graph, path1: List[Any], path2: List[Any]
    ) -> bool:
        """
        Check if two paths are compatible for merging.
        This uses node type compatibility checks to ensure valid path matching.

        Part of the "Substructure Matching" step in the algorithm.

        Args:
            graph1: First graph
            graph2: Second graph
            path1: Path in first graph
            path2: Path in second graph

        Returns:
            True if paths are compatible, False otherwise
        """
        self.logger.debug(
            f"Checking compatibility of paths: length1={len(path1)}, length2={len(path2)}"
        )

        # Paths are compatible if the nodes at each position have compatible types
        # For the common prefix (minimum length of both paths)
        for i in range(min(len(path1), len(path2))):
            if not self._check_node_type_compatibility(
                graph1, graph2, path1[i], path2[i]
            ):
                self.logger.debug(f"Paths incompatible at position {i}")
                return False

        # If we got here, all compared nodes are compatible
        self.logger.debug("Paths are compatible")
        return True

    def _create_reduced_path_in_result(
        self,
        result_graph: nx.Graph,
        graph1: nx.Graph,
        graph2: nx.Graph,
        start1: Any,  # Critical point start in graph1
        end1: Any,  # Critical point end in graph1
        path1: List[Any],  # Full path nodes from start1 to end1
        start2: Any,  # Critical point start in graph2
        end2: Any,  # Critical point end in graph2
        path2: List[Any],  # Full path nodes from start2 to end2
    ) -> None:
        """
        Creates a path in the result graph by merging two paths, reducing the longer
        path to match the shorter one (template) based on node similarity.

        Implements the "Find Maximum Common Minor" and property merging for a
        single segment between two matched critical points.

        Args:
            result_graph: The result graph being built.
            graph1: First graph (concept).
            graph2: Second graph (image).
            start1: Start critical node ID in graph1.
            end1: End critical node ID in graph1.
            path1: Node list for the path between start1 and end1 (inclusive).
            start2: Start critical node ID in graph2.
            end2: End critical node ID in graph2.
            path2: Node list for the path between start2 and end2 (inclusive).
        """
        self.logger.debug(
            f"Creating reduced path in result between ({start1}, {start2}) and ({end1}, {end2})"
        )

        # Ensure start nodes are in the result graph (should have been added previously)
        if start1 not in result_graph:
            merged_start_props = self.prop_manager.process_node_properties(
                {}, graph1.nodes[start1], graph2.nodes[start2]
            )
            result_graph.add_node(start1, **merged_start_props)
            self.logger.debug(
                f"Added start node {start1} to result graph (was missing)"
            )

        # Determine template (shorter) and other (longer) paths
        # Exclude start/end critical points from length comparison and processing loop
        sub_path1 = path1[1:-1]
        sub_path2 = path2[1:-1]

        if len(sub_path1) <= len(sub_path2):
            template_path = sub_path1
            template_graph = graph1
            template_start_node = start1  # Use ID from graph1
            template_end_node = end1  # Use ID from graph1
            other_path = sub_path2
            other_graph = graph2
            self.logger.debug(
                f"Using path1 as template (sub-path length={len(template_path)})"
            )
        else:
            template_path = sub_path2
            template_graph = graph2
            template_start_node = start1  # Use ID from graph1
            template_end_node = end1  # Use ID from graph1
            other_path = sub_path1
            other_graph = graph1
            self.logger.debug(
                f"Using path2 as template (sub-path length={len(template_path)})"
            )

        # Calculate node similarity matrix between the *sub-paths*
        similarity_matrix = []
        if template_path and other_path:  # Only calculate if both sub-paths exist
            similarity_matrix = self.similarity_calculator.calculate_similarity_matrix(
                template_graph, other_graph, template_path, other_path
            )
            self.logger.debug(
                f"Calculated similarity matrix of size {len(template_path)}x{len(other_path)}"
            )
        else:
            self.logger.debug(
                "One or both sub-paths are empty, no similarity calculation needed."
            )

        # Add nodes from the template path to the result graph, merging properties
        prev_node_in_result = template_start_node

        for i, template_node_id in enumerate(template_path):
            # Find the best matching node from the other path
            best_match_idx = self._find_best_matching_node(
                similarity_matrix, i, template_path, other_path
            )

            if best_match_idx is not None and best_match_idx < len(other_path):
                other_node_id = other_path[best_match_idx]
                self.logger.debug(
                    f"Matching template node {template_node_id} (idx {i}) with other node {other_node_id} (idx {best_match_idx})"
                )
                # Merge properties from both corresponding nodes
                node_props = self.prop_manager.process_node_properties(
                    {},
                    template_graph.nodes[template_node_id],
                    other_graph.nodes[other_node_id],
                )
            else:
                # No good match found, or other_path is empty, use only template properties
                self.logger.debug(
                    f"No good match for template node {template_node_id} (idx {i}), using its properties only."
                )
                node_props = template_graph.nodes[
                    template_node_id
                ].copy()  # Make a copy

            # Use the node ID from the *first* graph (concept graph) if possible,
            # otherwise use the template node ID. This maintains consistency if graph1 was template.
            result_node_id = (
                template_node_id
                if template_graph == graph1
                else (
                    other_path[best_match_idx]
                    if best_match_idx is not None
                    else template_node_id
                )
            )
            # Correction: Always use the ID from the template path's graph for the result node ID
            # to represent the reduced structure based on the template.
            # However, for consistency, we should probably try to map back to graph1's IDs
            # if graph2 was the template. Let's stick to template ID for simplicity now.
            result_node_id = template_node_id  # Node ID from the template path

            # Add the node to the result graph if it doesn't exist
            if result_node_id not in result_graph:
                result_graph.add_node(result_node_id, **node_props)
                self.logger.debug(f"Added node {result_node_id} to result graph")
            else:
                # If node exists, update properties (this might happen with complex merges)
                # For now, we assume nodes are added once per path creation.
                # Re-adding might indicate issues elsewhere. Let's log a warning.
                self.logger.warning(
                    f"Node {result_node_id} already exists in result graph. Properties not updated."
                )

            # Add the edge from the previous node in the result path
            if prev_node_in_result != result_node_id:  # Avoid self-loops
                # Merge edge properties if needed (currently not implemented)
                result_graph.add_edge(prev_node_in_result, result_node_id)
                self.logger.debug(
                    f"Added edge ({prev_node_in_result}, {result_node_id}) to result graph"
                )
                prev_node_in_result = result_node_id
            else:
                self.logger.warning(
                    f"Skipping self-loop edge for node {result_node_id}"
                )

        # Ensure the end critical node is in the result graph and connected
        if template_end_node not in result_graph:
            # Merge properties of the end critical points
            merged_end_props = self.prop_manager.process_node_properties(
                {}, graph1.nodes[end1], graph2.nodes[end2]
            )
            result_graph.add_node(template_end_node, **merged_end_props)
            self.logger.debug(
                f"Added end critical node {template_end_node} to result graph"
            )

        # Add the final edge connecting the last node of the processed sub-path to the end critical node
        if prev_node_in_result != template_end_node:
            result_graph.add_edge(prev_node_in_result, template_end_node)
            self.logger.debug(
                f"Added final edge ({prev_node_in_result}, {template_end_node}) to result graph"
            )
        elif not template_path:  # Handle direct connection between critical points
            result_graph.add_edge(template_start_node, template_end_node)
            self.logger.debug(
                f"Added direct edge ({template_start_node}, {template_end_node}) between critical points"
            )

    def _find_best_matching_node(
        self,
        similarity_matrix: List[List[float]],
        current_idx: int,
        path1: List[Any],
        path2: List[Any],
    ) -> Optional[int]:
        """
        Find the best matching node in path2 for the node at current_idx in path1.

        This supports finding the maximum common minor by identifying corresponding
        nodes between two paths.

        Args:
            similarity_matrix: Node similarity matrix
            current_idx: Index of the current node in path1
            path1: First path
            path2: Second path

        Returns:
            Index of the best matching node in path2, or None if no good match
        """
        self.logger.debug(
            f"Finding best matching node for node at index {current_idx} in path1"
        )

        # We need to find a node in path2 that best matches the node at current_idx in path1
        # Get similarity scores for the current node
        scores = similarity_matrix[current_idx]

        # Find the index with highest similarity
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        best_score = scores[best_idx]

        self.logger.debug(
            f"Best match is node at index {best_idx} with score {best_score:.2f}"
        )

        # Only return a match if similarity is above threshold
        if best_score > 0.5:  # Threshold for considering a good match
            self.logger.debug(
                f"Match score {best_score:.2f} exceeds threshold, using property-based match"
            )
            return best_idx

        # Fallback to position-based matching if no good property-based match or paths are dissimilar
        # This ensures we always have a corresponding node for merging structure.
        self.logger.debug(
            f"Property match score {best_score:.2f} below threshold or no similarity matrix provided."
        )

        if not path1 or not path2:  # Cannot do position matching if a path is empty
            self.logger.debug("Cannot perform position matching with empty path(s).")
            return None

        # Calculate relative position and find corresponding position in other path
        relative_position = current_idx / (len(path1) - 1) if len(path1) > 1 else 0.5
        position_idx = round(
            relative_position * (len(path2) - 1)
        )  # Round to nearest index
        # Ensure index is within bounds
        position_idx = max(0, min(position_idx, len(path2) - 1))

        self.logger.debug(
            f"Falling back to position-based match: path1[{current_idx}] -> path2[{position_idx}]"
        )
        return position_idx
