import logging
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional, Set

from node_similarity_calculator import NodeSimilarityCalculator
from property_handlers.property_handler_manager import PropertyHandlerManager


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

        # Define the type reduction hierarchy
        self.type_reduction_map = {
            "IntersectionPoint": "CornerPoint",
            "CornerPoint": "Point",
            "VerticalVector": "Vector",
            "HorizontalVector": "Vector",
        }

    def find_max_common_minor(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> nx.Graph:
        """
        Find the maximum common minor between two graphs by identifying critical points
        and creating an intersection graph.

        This implements the key step in the concept formation algorithm where we find
        the common structural elements (graph minor) between the current concept
        and a new training sample.

        Args:
            concept_graph: The current concept graph (or temporary concept graph)
            image_graph: The new image graph (training sample) to integrate

        Returns:
            The updated concept graph with the intersection of both graphs
        """
        self.logger.info(
            f"Finding maximum common minor between graphs: concept ({len(concept_graph.nodes)} nodes) and image ({len(image_graph.nodes)} nodes)"
        )

        # 1. Identify critical points in both graphs
        concept_critical_points = self._identify_critical_points(concept_graph)
        image_critical_points = self._identify_critical_points(image_graph)

        self.logger.debug(
            f"Critical points in concept graph: {sum(len(points) for points in concept_critical_points.values())}"
        )
        self.logger.debug(
            f"Critical points in image graph: {sum(len(points) for points in image_critical_points.values())}"
        )

        # 2. Find the start points in both graphs - these are essential anchor points
        # per the algorithm documentation. StartPoints cannot be reduced.
        start_c = self._find_start_point(concept_graph, concept_critical_points)
        start_i = self._find_start_point(image_graph, image_critical_points)

        if not start_c or not start_i:
            self.logger.warning("Start point not found in one of the graphs")
            raise ValueError("Start point not found in one of the graphs")

        self.logger.info(f"Using start points: concept={start_c}, image={start_i}")

        # 3. Create a new graph for the intersection/result
        result_graph = nx.Graph()

        # 4. Start from the start points and build the intersection graph
        # This is where we trace paths between consecutive critical points
        # and identify the maximum common minors between them
        self._build_intersection_graph(
            result_graph,
            concept_graph,
            image_graph,
            start_c,
            start_i,
            concept_critical_points,
            image_critical_points,
            set(),
            set(),  # Visited nodes tracking
            set(),  # Track processed path pairs
        )

        self.logger.info(
            f"Completed common minor finding. Result graph has {len(result_graph.nodes)} nodes and {len(result_graph.edges)} edges"
        )
        return result_graph

    def _identify_critical_points(self, graph: nx.Graph) -> Dict[str, List[Any]]:
        """
        Identify critical points in a graph (intersection points, corner points, end points, start points).

        Critical points are structural elements that contain significant information:
        - Intersection Points: Where multiple vectors meet
        - Corner Points: Where the contour changes direction significantly
        - End Points: Terminal points of a structure
        - Start Points: Beginning point of a structure

        Args:
            graph: The graph to analyze

        Returns:
            Dictionary mapping point types to lists of node IDs
        """
        self.logger.debug(
            f"Identifying critical points in graph with {len(graph.nodes)} nodes"
        )
        critical_points = {
            "IntersectionPoint": [],
            "CornerPoint": [],
            "EndPoint": [],
            "StartPoint": [],
        }

        for node in graph.nodes:
            node_data = graph.nodes[node]
            # Check if node has labels attribute
            labels = node_data.get("labels", [])

            # Assign node to appropriate category
            for label in labels:
                if label in critical_points:
                    critical_points[label].append(node)

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

    def _reduce_point_type(self, point_type: str) -> str:
        """
        Reduce a point type to a more general one according to defined reduction rules.

        Type reduction hierarchy:
        - IntersectionPoint -> CornerPoint -> Point
        - StartPoint and EndPoint cannot be reduced

        Args:
            point_type: The original point type

        Returns:
            The reduced point type, or the original if no reduction is possible
        """
        return self.type_reduction_map.get(point_type, point_type)

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

    def _build_intersection_graph(
        self,
        result_graph: nx.Graph,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        current_c: Any,
        current_i: Any,
        concept_critical_points: Dict[str, List[Any]],
        image_critical_points: Dict[str, List[Any]],
        visited_c: Set[Any],
        visited_i: Set[Any],
        processed_paths: Set[Tuple[Any, Any]],
    ) -> None:
        """
        Recursively build the intersection graph starting from the current nodes.

        This method implements the core of the concept formation algorithm:
        1. Identify critical point sequences
        2. Match critical points across graphs
        3. Find maximum common minor for matched segments
        4. Update the result graph with the common structure

        Args:
            result_graph: The result graph being constructed
            concept_graph: The concept graph
            image_graph: The image graph
            current_c: Current node in concept graph
            current_i: Current node in image graph
            concept_critical_points: Critical points in concept graph
            image_critical_points: Critical points in image graph
            visited_c: Set of visited nodes in concept graph
            visited_i: Set of visited nodes in image graph
            processed_paths: Set of processed path pairs (as critical points pairs)
        """
        self.logger.debug(
            f"Building intersection graph from nodes: concept={current_c}, image={current_i}"
        )

        # Check if node types are compatible before proceeding
        if not self._check_node_type_compatibility(
            concept_graph, image_graph, current_c, current_i
        ):
            self.logger.debug(
                f"Nodes {current_c} and {current_i} are not compatible, skipping"
            )
            return

        # Mark current nodes as visited
        visited_c.add(current_c)
        visited_i.add(current_i)

        # Merge properties of the current nodes and add to result graph
        # This implements the statistical property updates part of the algorithm
        merged_props = self.prop_manager.process_node_properties(
            {}, concept_graph.nodes[current_c], image_graph.nodes[current_i]
        )

        # Add the node to the result graph
        if current_c not in result_graph:
            result_graph.add_node(current_c, **merged_props)
            self.logger.debug(f"Added node {current_c} to result graph")

        # Get neighbors of current nodes
        c_neighbors = list(concept_graph.neighbors(current_c))
        i_neighbors = list(image_graph.neighbors(current_i))

        self.logger.debug(
            f"Processing neighbors: concept={len(c_neighbors)}, image={len(i_neighbors)}"
        )

        # Explore all paths from current critical points to the next critical points
        for c_neighbor in c_neighbors:
            if c_neighbor in visited_c:
                continue

            is_c_critical = any(
                c_neighbor in points for points in concept_critical_points.values()
            )

            # If this is not a critical point, follow the path
            if not is_c_critical:
                path_c = self._follow_path_to_next_critical(
                    concept_graph, c_neighbor, visited_c, concept_critical_points
                )
                if not path_c:
                    continue
                next_critical_c, path_nodes_c = path_c
                self.logger.debug(
                    f"Found path in concept graph from {c_neighbor} to {next_critical_c}, length={len(path_nodes_c)}"
                )
            else:
                next_critical_c, path_nodes_c = c_neighbor, [c_neighbor]
                self.logger.debug(f"Neighbor {c_neighbor} is already a critical point")

            # Try to find a matching path in the image graph
            for i_neighbor in i_neighbors:
                if i_neighbor in visited_i:
                    continue

                # Check if neighbor types are compatible
                if not self._check_node_type_compatibility(
                    concept_graph, image_graph, c_neighbor, i_neighbor
                ):
                    continue

                is_i_critical = any(
                    i_neighbor in points for points in image_critical_points.values()
                )

                # If this is not a critical point, follow the path
                if not is_i_critical:
                    path_i = self._follow_path_to_next_critical(
                        image_graph, i_neighbor, visited_i, image_critical_points
                    )
                    if not path_i:
                        continue
                    next_critical_i, path_nodes_i = path_i
                    self.logger.debug(
                        f"Found path in image graph from {i_neighbor} to {next_critical_i}, length={len(path_nodes_i)}"
                    )
                else:
                    next_critical_i, path_nodes_i = i_neighbor, [i_neighbor]
                    self.logger.debug(
                        f"Neighbor {i_neighbor} is already a critical point"
                    )

                # Create a path pair identifier (ordered tuple of critical point pairs)
                path_pair_id = tuple(
                    sorted([(current_c, current_i), (next_critical_c, next_critical_i)])
                )

                # Skip if we've already processed this path pair
                if path_pair_id in processed_paths:
                    self.logger.debug(
                        f"Path pair {path_pair_id} already processed, skipping"
                    )
                    continue
                processed_paths.add(path_pair_id)

                # Check if the paths are compatible
                if self._are_paths_compatible(
                    concept_graph, image_graph, path_nodes_c, path_nodes_i
                ):
                    self.logger.debug(
                        f"Paths are compatible, creating path in result graph"
                    )
                    # Create the path in the result graph - this is where we implement
                    # the "Find Maximum Common Minor" step described in the algorithm
                    self._create_path_in_result(
                        result_graph,
                        concept_graph,
                        image_graph,
                        current_c,
                        next_critical_c,
                        path_nodes_c,
                        current_i,
                        next_critical_i,
                        path_nodes_i,
                    )

                    # Recursively continue from the next critical points
                    if (
                        next_critical_c not in visited_c
                        and next_critical_i not in visited_i
                    ):
                        self.logger.debug(
                            f"Recursively continuing to explore from {next_critical_c} and {next_critical_i}"
                        )
                        self._build_intersection_graph(
                            result_graph,
                            concept_graph,
                            image_graph,
                            next_critical_c,
                            next_critical_i,
                            concept_critical_points,
                            image_critical_points,
                            visited_c.copy(),
                            visited_i.copy(),
                            processed_paths,
                        )

    def _check_node_type_compatibility(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> bool:
        """
        Check if two nodes have compatible types using type reduction when necessary.

        Implements the type reduction logic from the algorithm:
        - IntersectionPoint can be reduced to CornerPoint
        - CornerPoint can be reduced to Point
        - StartPoint and EndPoint cannot be reduced

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

        # Check for StartPoint and EndPoint - these cannot be reduced
        node1_is_start = "StartPoint" in node1_types
        node1_is_end = "EndPoint" in node1_types
        node2_is_start = "StartPoint" in node2_types
        node2_is_end = "EndPoint" in node2_types

        # StartPoints must match StartPoints, EndPoints must match EndPoints
        if (node1_is_start and not node2_is_start) or (
            node1_is_end and not node2_is_end
        ):
            return False
        if (node2_is_start and not node1_is_start) or (
            node2_is_end and not node1_is_end
        ):
            return False

        # Check basic type compatibility (Point to Point, Vector to Vector)
        node1_is_point = any("Point" in t for t in node1_types)
        node1_is_vector = any("Vector" in t for t in node1_types)
        node2_is_point = any("Point" in t for t in node2_types)
        node2_is_vector = any("Vector" in t for t in node2_types)

        # If types don't match at basic level, nodes are incompatible
        if (node1_is_point and node2_is_vector) or (node1_is_vector and node2_is_point):
            self.logger.debug(
                f"Node type mismatch: {node1} ({node1_types}) and {node2} ({node2_types})"
            )
            return False

        # If we have critical points, check for transformation possibilities
        node1_is_intersection = "IntersectionPoint" in node1_types
        node1_is_corner = "CornerPoint" in node1_types
        node2_is_intersection = "IntersectionPoint" in node2_types
        node2_is_corner = "CornerPoint" in node2_types

        # Apply type reduction logic
        if node1_is_intersection and node2_is_corner:
            # IntersectionPoint can be reduced to CornerPoint
            self.logger.debug(
                f"Type reduction: IntersectionPoint to CornerPoint ({node1}, {node2})"
            )
            return True

        if node1_is_corner and node2_is_intersection:
            # IntersectionPoint can be reduced to CornerPoint
            self.logger.debug(
                f"Type reduction: IntersectionPoint to CornerPoint ({node2}, {node1})"
            )
            return True

        # Check if they share any types
        if set(node1_types) & set(node2_types):
            self.logger.debug(f"Nodes {node1} and {node2} share common types")
            return True

        # Try to apply type reduction
        reduced_node1_types = [self._reduce_point_type(t) for t in node1_types]
        reduced_node2_types = [self._reduce_point_type(t) for t in node2_types]

        # Check if the reduced types match
        if set(reduced_node1_types) & set(node2_types) or set(node1_types) & set(
            reduced_node2_types
        ):
            self.logger.debug(
                f"Nodes {node1} and {node2} are compatible after type reduction"
            )
            return True

        self.logger.debug(
            f"Nodes {node1} and {node2} are incompatible even after type reduction"
        )
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

    def _create_path_in_result(
        self,
        result_graph: nx.Graph,
        graph1: nx.Graph,
        graph2: nx.Graph,
        start1: Any,
        end1: Any,
        path1: List[Any],
        start2: Any,
        end2: Any,
        path2: List[Any],
    ) -> None:
        """
        Create a path in the result graph by merging two paths.

        This implements the "Find Maximum Common Minor" step of the algorithm:
        - Uses the shorter path as the template (applying graph minor operations)
        - Merges properties of corresponding nodes
        - Updates the result graph with the common structure

        Args:
            result_graph: The result graph
            graph1: First graph
            graph2: Second graph
            start1: Start node in first graph
            end1: End node in first graph
            path1: Path in first graph
            start2: Start node in second graph
            end2: End node in second graph
            path2: Path in second graph
        """
        self.logger.debug(f"Creating path in result graph from {start1} to {end1}")
        # Use the shorter path as the template - this implements the graph minor operation
        # where we simplify the more complex path to match the simpler one
        if len(path1) <= len(path2):
            template_path = path1
            template_graph = graph1
            other_path = path2
            other_graph = graph2
            self.logger.debug(f"Using path1 as template (length={len(path1)})")
        else:
            template_path = path2
            template_graph = graph2
            other_path = path1
            other_graph = graph1
            self.logger.debug(f"Using path2 as template (length={len(path2)})")

        # Calculate node similarity matrix between paths
        # This will help us find the best matching node for each template node
        similarity_matrix = self.similarity_calculator.calculate_similarity_matrix(
            template_graph, other_graph, template_path, other_path
        )
        self.logger.debug(
            f"Calculated similarity matrix of size {len(template_path)}x{len(other_path)}"
        )

        # Add all nodes in the template path to the result graph
        prev_node = start1  # Use IDs from the first graph for consistency

        for i, node in enumerate(template_path):
            # Skip the first node as it's already added
            if node == end1 or node == end2:
                # This is the end node, which may already exist in the result
                if end1 not in result_graph:
                    # Merge properties of end nodes
                    merged_props = self.prop_manager.process_node_properties(
                        {}, graph1.nodes[end1], graph2.nodes[end2]
                    )
                    result_graph.add_node(end1, **merged_props)
                    self.logger.debug(f"Added end node {end1} to result graph")

                # Add edge between previous node and end
                result_graph.add_edge(prev_node, end1)
                self.logger.debug(f"Added edge ({prev_node}, {end1}) to result graph")
                break

            # Find the best matching node from the other path
            best_match_idx = self._find_best_matching_node(
                similarity_matrix, i, template_path, other_path
            )

            if best_match_idx is not None:
                corresponding_node = other_path[best_match_idx]
                self.logger.debug(
                    f"Found matching node {corresponding_node} for template node {node}"
                )

                # Merge properties of the nodes - this implements the "update properties"
                # part of the algorithm, where stats from both samples are combined
                node_props = self.prop_manager.process_node_properties(
                    {},
                    template_graph.nodes[node],
                    other_graph.nodes[corresponding_node],
                )
            else:
                # No good match found, use template properties
                node_props = template_graph.nodes[node].copy()
                self.logger.debug(
                    f"No good match found for node {node}, using template properties"
                )

            # Use node ID from the template graph
            new_node = node

            # Add the node and edge
            if new_node not in result_graph:
                result_graph.add_node(new_node, **node_props)
                self.logger.debug(f"Added node {new_node} to result graph")

            result_graph.add_edge(prev_node, new_node)
            self.logger.debug(f"Added edge ({prev_node}, {new_node}) to result graph")
            prev_node = new_node

        # Ensure there's an edge to the end node if not already added
        if end1 in result_graph and prev_node != end1:
            result_graph.add_edge(prev_node, end1)
            self.logger.debug(f"Added final edge ({prev_node}, {end1}) to result graph")

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

        # Fallback to position-based matching if no good property-based match
        # Calculate relative position and find corresponding position in other path
        relative_position = current_idx / (len(path1) - 1) if len(path1) > 1 else 0.5
        position_idx = int(relative_position * (len(path2) - 1))

        self.logger.debug(
            f"No good property match, falling back to position-based match at index {position_idx}"
        )
        return position_idx
