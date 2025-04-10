import networkx as nx
import collections
import logging
from typing import Dict, Set, Tuple, List, Any, Optional
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
        # This now returns the modified original graphs, not just critical point graphs
        G_c_processed, G_i_processed = (
            self.critical_point_preprocessor.preprocess_graphs(G_c, G_i)
        )

        self.logger.info(f"Processed concept graph nodes: {len(G_c_processed.nodes)}")
        self.logger.info(f"Processed image graph nodes: {len(G_i_processed.nodes)}")

        # Matrix of the subpaths between intersection points
        # Inside each subpath we have the traversal sequence of two graphs
        # Each inner list represents a continuous path between critical points
        sync_list: List[List[Tuple[Any, Any]]] = self._generate_sync_list(
            G_c_processed, G_i_processed
        )

        self.logger.info(
            "Sync list: \n" + "\n".join([str(subpath) for subpath in sync_list])
        )

        result_graph = nx.Graph()
        for subpath in sync_list:
            self.logger.info(f"Subpath: {subpath}")
            self._reduce_subpath(G_c_processed, G_i_processed, subpath, result_graph)
            self.logger.info(f"Result graph: {result_graph.nodes}")

        # Return the result graph which is the maximum common minor
        return result_graph

    def _reduce_subpath(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
        subpath: List[Tuple[Any, Any]],
        result_graph: nx.Graph,
    ) -> List[Tuple[Any, Any]]:
        """Reducing the subpath to the maximum common minor"""
        processed_paths_c = list()
        processed_paths_i = list()
        for i in range(len(subpath) - 1):
            start_c, end_c = subpath[i][0], subpath[i + 1][0]
            start_i, end_i = subpath[i][1], subpath[i + 1][1]

            # Get all simple paths between the critical points
            paths_c = list(nx.all_simple_paths(G_c, start_c, end_c))
            paths_i = list(nx.all_simple_paths(G_i, start_i, end_i))
            
            # Remove already processed paths to avoid reprocessing
            if processed_paths_c and processed_paths_i:
                # Filter out paths that have been processed before
                # Expand to regular loops for better debugging
                filtered_paths_c = []
                for path in paths_c:
                    if path not in processed_paths_c and path[::-1] not in processed_paths_c:
                        filtered_paths_c.append(path)
                    else:
                        self.logger.debug(f"Skipping already processed concept path: {path}")
                paths_c = filtered_paths_c
                
                filtered_paths_i = []
                for path in paths_i:
                    if path not in processed_paths_i and path[::-1] not in processed_paths_i:
                        filtered_paths_i.append(path)
                    else:
                        self.logger.debug(f"Skipping already processed image path: {path}")
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

    def _generate_sync_list(
        self,
        G_c: nx.Graph,
        G_i: nx.Graph,
    ) -> List[List[Tuple[Any, Any]]]:
        """Generating the sync list of the two graphs"""
        sync_list: List[List[Tuple[Any, Any]]] = []

        start_c = GraphUtils.get_first_point_by_type(G_c, CriticalPointType.START_POINT)
        start_i = GraphUtils.get_first_point_by_type(G_i, CriticalPointType.START_POINT)

        if start_c is None or start_i is None:
            raise ValueError("Could not find start points in one or both graphs.")

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
                    # Initialize the new path with the intersection point
                    sync_list.append([(current_c, current_i)])

                    # Get the matched image point
                    image_cp = matched_points[key]  # Renamed for clarity

                    # Add the matched neighbor pair to the new path list
                    sync_list[new_path_id].append((key, image_cp))

                    # Add the new path to the queue using the MATCHED PAIR
                    # Ensure the matched pair itself isn't immediately revisited on this new path
                    if (key, image_cp) not in visited:
                        visited[(key, image_cp)] = set()
                    visited[(key, image_cp)].add(new_path_id)

                    queue.append(
                        (
                            key,  # Matched concept neighbor
                            image_cp,  # Matched image neighbor
                            new_path_id,
                            current_c,  # Previous concept node (intersection)
                            current_i,  # Previous image node (intersection)
                        )
                    )
                # Mark the current path as completed since we branched
                completed_paths.add(path_id)
                continue  # Continue to next item in queue

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

            self.logger.info(
                f"Next critical points: {next_c_critical_point}, {next_i_critical_point}"
            )
            if not GraphUtils.is_same_critical_point_type(
                G_c.nodes[next_c_critical_point], G_i.nodes[next_i_critical_point]
            ):
                raise ValueError("Critical points are not the same type")

            sync_list[path_id].append((next_c_critical_point, next_i_critical_point))

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
            best_match_idx = self._find_best_matching_node(similarity_matrix, i)

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

        return best_idx
