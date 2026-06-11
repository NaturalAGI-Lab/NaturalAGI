import networkx as nx
import logging
import os
from typing import Tuple, List, Any, Optional
from src.property_handlers import PropertyProcessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.logic.synced_traversal_generator import SyncedTraversalGenerator
from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils


class SyncedGraphMinorFinder:
    def __init__(
        self,
        prop_manager: PropertyProcessor,
        similarity_calculator: NodeSimilarityCalculator,
        critical_point_preprocessor: CriticalPointPreprocessor,
        logger=None,
    ):
        self.prop_manager = prop_manager
        self.similarity_calculator = similarity_calculator
        self.logger = logger or logging.getLogger(__name__)
        self.critical_point_preprocessor = critical_point_preprocessor
        self.synced_traversal_generator = SyncedTraversalGenerator(
            critical_point_types={
                CriticalPointType.START_POINT,
                CriticalPointType.END_POINT,
                CriticalPointType.INTERSECTION_POINT,
                CriticalPointType.CORNER_POINT,
            }
        )
        self.min_match_similarity = float(
            os.getenv("CONCEPT_MIN_MATCH_SIMILARITY", "0.3")
        )
        self._segment_counter = 0

    def find_max_common_minor(self, G_c: nx.Graph, G_i: nx.Graph) -> nx.Graph:
        """Finding the maximum common minor of two graphs by traversing through critical points first, generating the skeleton graph

        Args:
            G_c (nx.Graph): concept graph
            G_i (nx.Graph): image graph

        Returns:
            nx.Graph: maximum common minor of the two graphs
        """
        # Preprocess the graphs to align critical points
        # This now returns the modified original graphs, not just critical point graphs
        G_c_processed, G_i_processed = (
            self.critical_point_preprocessor.preprocess_graphs(G_c, G_i)
        )

        self.logger.info(f"Processed concept graph nodes: {len(G_c_processed.nodes)}")
        self.logger.info(f"Processed image graph nodes: {len(G_i_processed.nodes)}")

        start_c = GraphUtils.get_first_point_by_type(
            G_c_processed, CriticalPointType.START_POINT
        )
        start_i = GraphUtils.get_first_point_by_type(
            G_i_processed, CriticalPointType.START_POINT
        )
        if start_c is not None and start_i is not None:
            start_distance = self.synced_traversal_generator._pair_distance(
                G_c_processed.nodes[start_c], G_i_processed.nodes[start_i]
            )
            if start_distance > self.synced_traversal_generator.max_pair_distance:
                raise ValueError(
                    f"Start-pair spatial mismatch {start_distance:.2f} exceeds "
                    f"threshold {self.synced_traversal_generator.max_pair_distance}"
                )

        self._segment_counter = 0

        # Matrix of the subpaths between intersection points
        # Inside each subpath we have the traversal sequence of two graphs
        # Each inner list represents a continuous path between critical points
        sync_list: List[List[Tuple[Any, Any]]] = (
            self.synced_traversal_generator.generate_synced_traversal(
                G_c_processed, G_i_processed
            )
        )

        self.logger.info(
            "Sync list: \n" + "\n".join([str(subpath) for subpath in sync_list])
        )

        result_graph = nx.Graph()
        for subpath in sync_list:
            self.logger.info(f"Subpath: {subpath}")
            self._reduce_subpath(G_c_processed, G_i_processed, subpath, result_graph)
            self.logger.info("Result graph:")
            for node in result_graph.nodes:
                self.logger.info(f"Node {node}: {result_graph.nodes[node]['labels']}")

        # Return the result graph which is the maximum common minor
        return result_graph

    def _reduce_subpath(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        subpath: List[Tuple[Any, Any]],
        result_graph: nx.Graph,
    ) -> None:
        """Reducing the subpath to the maximum common minor"""
        processed_paths_c = list()
        processed_paths_i = list()
        for i in range(len(subpath) - 1):
            start_c, end_c = subpath[i][0], subpath[i + 1][0]
            start_i, end_i = subpath[i][1], subpath[i + 1][1]

            # Get all simple paths between the critical points
            paths_c = list(nx.all_simple_paths(G_c, start_c, end_c))
            paths_i = list(nx.all_simple_paths(G_i, start_i, end_i))

            # Remove paths that contain critical points in the middle
            paths_c = [
                path
                for path in paths_c
                if not any(
                    GraphUtils.is_critical_point(G_c.nodes[node]) for node in path[1:-1]
                )
            ]
            paths_i = [
                path
                for path in paths_i
                if not any(
                    GraphUtils.is_critical_point(G_i.nodes[node]) for node in path[1:-1]
                )
            ]

            # Remove already processed paths to avoid reprocessing
            if processed_paths_c and processed_paths_i:
                # Filter out paths that have been processed before
                # Expand to regular loops for better debugging
                filtered_paths_c = []
                for path in paths_c:
                    if (
                        path not in processed_paths_c
                        and path[::-1] not in processed_paths_c
                    ):
                        filtered_paths_c.append(path)
                    else:
                        self.logger.debug(
                            f"Skipping already processed concept path: {path}"
                        )
                paths_c = filtered_paths_c

                filtered_paths_i = []
                for path in paths_i:
                    if (
                        path not in processed_paths_i
                        and path[::-1] not in processed_paths_i
                    ):
                        filtered_paths_i.append(path)
                    else:
                        self.logger.debug(
                            f"Skipping already processed image path: {path}"
                        )
                paths_i = filtered_paths_i
                self.logger.debug(
                    f"After filtering processed paths: {len(paths_c)} concept paths, {len(paths_i)} image paths remain"
                )

            if not paths_c or not paths_i:
                self.logger.warning(
                    f"No path found between critical points: ({start_c},{end_c}) or ({start_i},{end_i})"
                )
                continue

            # Find the best matching paths using similarity calculation
            best_path_c, best_path_i = self._find_best_matching_paths(
                G_c, G_i, paths_c, paths_i
            )

            self.logger.info(
                f"Selected best matching paths: {best_path_c} and {best_path_i}"
            )

            # Add to processed paths to avoid reprocessing
            processed_paths_c.append(best_path_c)
            processed_paths_i.append(best_path_i)

            # Create the reduced path in the result graph
            self._create_reduced_path_in_result(
                result_graph,
                G_c,
                G_i,
                start_c,
                end_c,
                best_path_c,
                start_i,
                end_i,
                best_path_i,
            )

    def _find_best_matching_paths(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        paths_c: List[List[Any]],
        paths_i: List[List[Any]],
    ) -> Tuple[List[Any], List[Any]]:
        """
        Find the best matching paths between two sets of paths using node similarity.

        Args:
            G_c: Concept graph
            G_i: Image graph
            paths_c: List of paths in concept graph
            paths_i: List of paths in image graph

        Returns:
            Tuple of (best_path_c, best_path_i)
        """
        best_score = -1
        best_pair = (paths_c[0], paths_i[0])  # Default to first paths

        self.logger.info(
            f"Finding best matching paths from {len(paths_c)} concept paths and {len(paths_i)} image paths"
        )
        self.logger.info(
            f"Concept paths: " + "\n".join([str(path) for path in paths_c])
        )
        self.logger.info(f"Image paths: " + "\n".join([str(path) for path in paths_i]))

        # Compare each path pair and find the one with highest similarity
        for path_c in paths_c:
            for path_i in paths_i:
                # Calculate similarity matrix between the paths
                similarity_matrix = (
                    self.similarity_calculator.calculate_similarity_matrix(
                        G_c, G_i, path_c, path_i
                    )
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

    def _calculate_path_similarity_score(
        self, similarity_matrix: List[List[float]]
    ) -> float:
        """
        Calculate a similarity score between two paths based on their node similarity matrix.
        Uses average of maximum similarities for each node in the first path.

        Args:
            similarity_matrix: Matrix of node similarity scores

        Returns:
            Overall path similarity score
        """
        if not similarity_matrix:
            return 0.0

        # For each node in the first path, find its best match in the second path
        max_similarities = [max(row) if row else 0.0 for row in similarity_matrix]

        # Average the maximum similarities
        if max_similarities:
            return sum(max_similarities) / len(max_similarities)
        return 0.0

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
            merged_start_props = self.prop_manager.process_properties(
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

        segment_index = self._segment_counter
        self._segment_counter += 1

        alignment = self._align_paths(similarity_matrix) if similarity_matrix else []

        for i, template_node_id in enumerate(template_path):
            best_match_idx = alignment[i] if i < len(alignment) else None
            if (
                best_match_idx is not None
                and similarity_matrix[i][best_match_idx] < self.min_match_similarity
            ):
                best_match_idx = None

            if best_match_idx is not None and best_match_idx < len(other_path):
                other_node_id = other_path[best_match_idx]
                self.logger.debug(
                    f"Matching template node {template_node_id} (idx {i}) with other node {other_node_id} (idx {best_match_idx})"
                )
                # Merge properties from both corresponding nodes
                node_props = self.prop_manager.process_properties(
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

            # Interior nodes get collision-proof IDs; critical points keep
            # graph1 IDs as shared anchors across segments.
            result_node_id = f"seg{segment_index}_pos{i}"
            node_props["origin_template_id"] = template_node_id

            assert result_node_id not in result_graph, (
                f"Interior node {result_node_id} already exists in result graph"
            )
            result_graph.add_node(result_node_id, **node_props)
            self.logger.debug(f"Added node {result_node_id} to result graph")

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
            merged_end_props = self.prop_manager.process_properties(
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

    def _align_paths(self, sim: List[List[float]]) -> List[Optional[int]]:
        """Monotone (order-preserving) one-to-one alignment of two ordered paths.

        Needleman–Wunsch-style DP over the similarity matrix; gap = unmatched node.
        """
        n = len(sim)
        m = len(sim[0]) if sim else 0
        if n == 0 or m == 0:
            return [None] * n

        dp = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                dp[i][j] = max(
                    dp[i - 1][j],
                    dp[i][j - 1],
                    dp[i - 1][j - 1] + sim[i - 1][j - 1],
                )

        match: List[Optional[int]] = [None] * n
        i, j = n, m
        while i > 0 and j > 0:
            if dp[i][j] == dp[i - 1][j - 1] + sim[i - 1][j - 1]:
                match[i - 1] = j - 1
                i -= 1
                j -= 1
            elif dp[i][j] == dp[i - 1][j]:
                i -= 1
            else:
                j -= 1
        return match
