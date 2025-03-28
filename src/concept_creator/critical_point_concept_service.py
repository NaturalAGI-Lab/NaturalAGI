import logging
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional, Set
import uuid

from concept_creation_repository import ConceptCreationRepository
from property_handlers.property_handler_manager import PropertyHandlerManager
from node_similarity_calculator import NodeSimilarityCalculator


class CriticalPointConceptService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.repository = ConceptCreationRepository(
            neo4j_uri, neo4j_user, neo4j_password
        )
        self.prop_manager = PropertyHandlerManager()
        self.similarity_calculator = NodeSimilarityCalculator()
        self.logger = logging.getLogger(__name__)
        self.logger.info("CriticalPointConceptService initialized.")

    def create_concept_incrementally(
        self, session_id: str, concept_id: Optional[str] = None
    ) -> Tuple[str, nx.Graph]:
        """
        Create a concept incrementally by finding the intersection graph of all training samples.
        This follows the algorithm described in the concept formation documentation.

        Args:
            session_id: The session ID to create a concept for
            concept_id: Optional concept ID to use. If not provided, a new one will be generated.

        Returns:
            Tuple of (concept_id, concept_graph)
        """
        self.logger.info(
            f"Creating concept for session {session_id} using Critical Point approach."
        )

        if not concept_id:
            concept_id = str(uuid.uuid4())

        # Get all image IDs for the session
        image_ids = self.repository.get_image_ids_for_session(session_id)

        if not image_ids:
            raise ValueError(f"No images found for session {session_id}")

        # Start with the first image as the initial concept
        first_image_id = image_ids[0]
        concept_graph = self.repository.get_image_graph(first_image_id)

        # Initialize the concept with the first image
        self.logger.info(
            f"Initialized concept with graph from image {first_image_id}. Nodes: {len(concept_graph.nodes)}"
        )

        # Process each additional image
        for i, image_id in enumerate(image_ids[1:], 2):
            self.logger.info(f"Processing image {i}/{len(image_ids)}: {image_id}")
            image_graph = self.repository.get_image_graph(image_id)

            # Find the intersection graph between current concept and new image
            concept_graph = self._find_max_common_minor(concept_graph, image_graph)

            self.logger.info(
                f"Updated concept after image {image_id}. Nodes: {len(concept_graph.nodes)}"
            )

        # Save the final concept
        # self.repository.save_concept(concept_id, concept_graph)

        # for image_id in image_ids:
        #     self.repository.remove_image_data(image_id)

        return concept_id, concept_graph

    def _find_max_common_minor(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> nx.Graph:
        """
        Find the maximum common minor between two graphs by identifying critical points
        and creating an intersection graph.

        Args:
            concept_graph: The current concept graph
            image_graph: The new image graph to integrate

        Returns:
            The updated concept graph with the intersection of both graphs
        """
        # 1. Identify critical points in both graphs
        concept_critical_points = self._identify_critical_points(concept_graph)
        image_critical_points = self._identify_critical_points(image_graph)

        # 2. Find the start points in both graphs
        start_c = self._find_start_point(concept_graph, concept_critical_points)
        start_i = self._find_start_point(image_graph, image_critical_points)

        if not start_c or not start_i:
            self.logger.warning("Start point not found in one of the graphs")
            raise ValueError("Start point not found in one of the graphs")

        # 3. Create a new graph for the intersection/result
        result_graph = nx.Graph()

        # 4. Start from the start points and build the intersection graph
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
        )

        return result_graph

    def _identify_critical_points(self, graph: nx.Graph) -> Dict[str, List[Any]]:
        """
        Identify critical points in a graph (intersection points, corner points, end points, start points).

        Args:
            graph: The graph to analyze

        Returns:
            Dictionary mapping point types to lists of node IDs
        """
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

        return critical_points

    def _find_start_point(
        self, graph: nx.Graph, critical_points: Dict[str, List[Any]]
    ) -> Any:
        """
        Find the start point in a graph. If multiple start points exist, pick the first one.

        Args:
            graph: The graph to analyze
            critical_points: Dictionary of critical points by type

        Returns:
            Node ID of the start point, or None if not found
        """
        start_points = critical_points.get("StartPoint", [])
        if start_points:
            return start_points[0]

        return None

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
    ) -> None:
        """
        Recursively build the intersection graph starting from the current nodes.

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
        """
        # Check if node types are compatible before proceeding
        if not self._check_node_type_compatibility(
            concept_graph, image_graph, current_c, current_i
        ):
            return

        # Mark current nodes as visited
        visited_c.add(current_c)
        visited_i.add(current_i)

        # Merge properties of the current nodes and add to result graph
        merged_props = self.prop_manager.process_node_properties(
            {}, concept_graph.nodes[current_c], image_graph.nodes[current_i]
        )

        # Add the node to the result graph
        if current_c not in result_graph:
            result_graph.add_node(current_c, **merged_props)

        # Get neighbors of current nodes
        c_neighbors = list(concept_graph.neighbors(current_c))
        i_neighbors = list(image_graph.neighbors(current_i))

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
            else:
                next_critical_c, path_nodes_c = c_neighbor, [c_neighbor]

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
                else:
                    next_critical_i, path_nodes_i = i_neighbor, [i_neighbor]

                # Check if the paths are compatible
                if self._are_paths_compatible(
                    concept_graph, image_graph, path_nodes_c, path_nodes_i
                ):
                    # Create the path in the result graph
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
                        self._build_intersection_graph(
                            result_graph,
                            concept_graph,
                            image_graph,
                            next_critical_c,
                            next_critical_i,
                            concept_critical_points,
                            image_critical_points,
                            visited_c,
                            visited_i,
                        )

    def _check_node_type_compatibility(
        self, graph1: nx.Graph, graph2: nx.Graph, node1: Any, node2: Any
    ) -> bool:
        """
        Check if two nodes have compatible types (Point to Point, Vector to Vector).
        Special handling for critical points: IntersectionPoint can be transformed to CornerPoint.

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

        # Check basic type compatibility (Point to Point, Vector to Vector)
        node1_is_point = any("Point" in t for t in node1_types)
        node1_is_vector = any("Vector" in t for t in node1_types)
        node2_is_point = any("Point" in t for t in node2_types)
        node2_is_vector = any("Vector" in t for t in node2_types)

        # If types don't match at basic level, nodes are incompatible
        if (node1_is_point and node2_is_vector) or (node1_is_vector and node2_is_point):
            return False

        # If we have critical points, check for transformation possibilities
        node1_is_intersection = "IntersectionPoint" in node1_types
        node1_is_corner = "CornerPoint" in node1_types
        node2_is_intersection = "IntersectionPoint" in node2_types
        node2_is_corner = "CornerPoint" in node2_types

        # Special case: IntersectionPoint can be transformed to CornerPoint
        # This allows matching these critical point types
        if (node1_is_intersection and node2_is_corner) or (
            node1_is_corner and node2_is_intersection
        ):
            return True

        # Check if they share any types
        if set(node1_types) & set(node2_types):
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

        Args:
            graph: The graph to analyze
            start_node: The starting node
            visited: Set of already visited nodes
            critical_points: Dictionary of critical points

        Returns:
            Tuple of (next_critical_point, path_nodes) or None if no path is found
        """
        # All critical points in a flat list
        all_critical = set()
        for points in critical_points.values():
            all_critical.update(points)

        # BFS to find the path to the next critical point
        queue = [(start_node, [start_node])]
        path_visited = {start_node}

        while queue:
            current, path = queue.pop(0)

            # Check if current node is a critical point (not the start node)
            if current != start_node and current in all_critical:
                return current, path

            # Explore neighbors
            for neighbor in graph.neighbors(current):
                if neighbor not in path_visited and neighbor not in visited:
                    path_visited.add(neighbor)
                    new_path = path + [neighbor]
                    queue.append((neighbor, new_path))

        return None

    def _are_paths_compatible(
        self, graph1: nx.Graph, graph2: nx.Graph, path1: List[Any], path2: List[Any]
    ) -> bool:
        """
        Check if two paths are compatible for merging.
        This uses node type compatibility checks to ensure valid path matching.

        Args:
            graph1: First graph
            graph2: Second graph
            path1: Path in first graph
            path2: Path in second graph

        Returns:
            True if paths are compatible, False otherwise
        """
        # Paths are compatible if the nodes at each position have compatible types
        # For the common prefix (minimum length of both paths)
        for i in range(min(len(path1), len(path2))):
            if not self._check_node_type_compatibility(
                graph1, graph2, path1[i], path2[i]
            ):
                return False

        # If we got here, all compared nodes are compatible
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
        # Use the shorter path as the template
        if len(path1) <= len(path2):
            template_path = path1
            template_graph = graph1
            other_path = path2
            other_graph = graph2
        else:
            template_path = path2
            template_graph = graph2
            other_path = path1
            other_graph = graph1

        # Calculate node similarity matrix between paths
        # This will help us find the best matching node for each template node
        similarity_matrix = self.similarity_calculator.calculate_similarity_matrix(
            template_graph, other_graph, template_path, other_path
        )

        # Add all nodes in the template path to the result graph
        prev_node = start1  # Use IDs from the first graph for consistency

        for i, node in enumerate(template_path):
            # Skip the first node as it's already added
            if node == end1:
                # This is the end node, which may already exist in the result
                if end1 not in result_graph:
                    # Merge properties of end nodes
                    merged_props = self.prop_manager.process_node_properties(
                        {}, graph1.nodes[end1], graph2.nodes[end2]
                    )
                    result_graph.add_node(end1, **merged_props)

                # Add edge between previous node and end
                result_graph.add_edge(prev_node, end1)
                break

            # Find the best matching node from the other path
            best_match_idx = self._find_best_matching_node(
                similarity_matrix, i, template_path, other_path
            )

            if best_match_idx is not None:
                corresponding_node = other_path[best_match_idx]

                # Merge properties of the nodes
                node_props = self.prop_manager.process_node_properties(
                    {},
                    template_graph.nodes[node],
                    other_graph.nodes[corresponding_node],
                )
            else:
                # No good match found, use template properties
                node_props = template_graph.nodes[node].copy()

            # Use node ID from the template graph
            new_node = node

            # Add the node and edge
            if new_node not in result_graph:
                result_graph.add_node(new_node, **node_props)

            result_graph.add_edge(prev_node, new_node)
            prev_node = new_node

        # Ensure there's an edge to the end node if not already added
        if end1 in result_graph and prev_node != end1:
            result_graph.add_edge(prev_node, end1)

    def _find_best_matching_node(
        self,
        similarity_matrix: List[List[float]],
        current_idx: int,
        path1: List[Any],
        path2: List[Any],
    ) -> Optional[int]:
        """
        Find the best matching node in path2 for the node at current_idx in path1.

        Args:
            similarity_matrix: Node similarity matrix
            current_idx: Index of the current node in path1
            path1: First path
            path2: Second path

        Returns:
            Index of the best matching node in path2, or None if no good match
        """
        # We need to find a node in path2 that best matches the node at current_idx in path1
        # Get similarity scores for the current node
        scores = similarity_matrix[current_idx]

        # Find the index with highest similarity
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        best_score = scores[best_idx]

        # Only return a match if similarity is above threshold
        if best_score > 0.5:  # Threshold for considering a good match
            return best_idx

        # Fallback to position-based matching if no good property-based match
        # Calculate relative position and find corresponding position in other path
        relative_position = current_idx / (len(path1) - 1) if len(path1) > 1 else 0.5
        position_idx = int(relative_position * (len(path2) - 1))

        return position_idx
