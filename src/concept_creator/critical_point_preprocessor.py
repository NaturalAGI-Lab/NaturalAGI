import logging
import networkx as nx
from typing import List, Tuple, Any, Dict, Set
from node_similarity_calculator import NodeSimilarityCalculator
from model.critical_point import CriticalPointType


class CriticalPointPreprocessor:
    """
    Preprocesses graphs to ensure they have compatible critical points before graph minor matching.
    This class handles reduction and removal of critical points to ensure compatibility.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.similarity_calculator = NodeSimilarityCalculator()

        # Define the type reduction hierarchy
        self.type_reduction_map = {
            CriticalPointType.INTERSECTION_POINT.value: CriticalPointType.CORNER_POINT.value,
            CriticalPointType.CORNER_POINT.value: "Point",
        }
        self.critical_point_types = {
            CriticalPointType.INTERSECTION_POINT.value,
            CriticalPointType.CORNER_POINT.value,
            CriticalPointType.END_POINT.value,
            CriticalPointType.START_POINT.value,
        }
        self.properties_to_compare = set(
            ["normalized_x", "normalized_y", "relative_distance"]
        )

    def preprocess_graphs(
        self, graph1: nx.Graph, graph2: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Preprocess two graphs to ensure they have compatible critical points.
        This method modifies the original graphs until their critical point structures become isomorphic.

        Args:
            graph1: First graph to preprocess
            graph2: Second graph to preprocess

        Returns:
            Tuple of (preprocessed_graph1, preprocessed_graph2) - the modified original graphs
        """
        # Make copies of the original graphs to avoid modifying the input graphs directly
        graph1_mod = graph1.copy()
        graph2_mod = graph2.copy()

        # Extract critical point graphs for initial isomorphism check
        crit_graph1, _ = self._extract_critical_points_graph(graph1_mod)
        crit_graph2, _ = self._extract_critical_points_graph(graph2_mod)

        is_isomorphic = nx.is_isomorphic(crit_graph1, crit_graph2)

        if not is_isomorphic:
            self.logger.info(
                "Critical point graphs are not isomorphic, applying reductions..."
            )
            self.logger.info(f"Initial critical graph 1: {crit_graph1.nodes}")
            self.logger.info(f"Initial critical graph 2: {crit_graph2.nodes}")

            # Apply graph reduction to make graphs isomorphic
            graph1_mod, graph2_mod = self._reduce_graphs_for_isomorphism(
                graph1_mod, graph2_mod
            )

            # Extract critical point graphs again to check if they're now isomorphic
            crit_graph1, _ = self._extract_critical_points_graph(graph1_mod)
            crit_graph2, _ = self._extract_critical_points_graph(graph2_mod)

            is_isomorphic_after_reduction = nx.is_isomorphic(crit_graph1, crit_graph2)
            self.logger.info(
                f"Critical point graphs isomorphic after reduction: {is_isomorphic_after_reduction}"
            )

            if not is_isomorphic_after_reduction:
                self.logger.info(
                    f"After reduction - Critical graph 1: {crit_graph1.nodes}"
                )
                self.logger.info(
                    f"After reduction - Critical graph 2: {crit_graph2.nodes}"
                )

        return graph1_mod, graph2_mod

    def _extract_critical_points_graph(
        self, graph: nx.Graph
    ) -> Tuple[nx.Graph, List[Any]]:
        """
        Extract a graph containing only critical points with preserved topology.

        Args:
            graph: Original graph

        Returns:
            Tuple of (New graph with only critical points and preserved topology, List of critical points)
        """
        # Create a new graph
        critical_graph = nx.Graph()

        # Identify critical points
        critical_points = []
        for node, data in graph.nodes(data=True):
            labels = data.get("labels", "")
            if any(label in self.critical_point_types for label in labels):
                critical_points.append(node)
                # Copy node and its attributes to the new graph
                critical_graph.add_node(node, **data)

        # Connect critical points if there's a path between them in the original graph
        for i, source in enumerate(critical_points):
            for target in critical_points[i + 1 :]:
                if source != target:
                    # Check if there's a path between these critical points in the original graph
                    # that doesn't go through other critical points
                    if self._has_path_excluding_others(
                        graph, source, target, critical_points
                    ):
                        # Add edge between these critical points in the new graph
                        critical_graph.add_edge(source, target)

        return critical_graph, critical_points

    def _reduce_graphs_for_isomorphism(
        self, graph1: nx.Graph, graph2: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Iteratively reduce graphs until their critical point structures become isomorphic.
        This method modifies the original graphs.

        Args:
            graph1: First graph
            graph2: Second graph

        Returns:
            Tuple of (reduced_graph1, reduced_graph2)
        """
        # Extract critical point graphs
        crit_graph1, _ = self._extract_critical_points_graph(graph1)
        crit_graph2, _ = self._extract_critical_points_graph(graph2)

        iteration = 0
        # Iterate until critical point graphs are isomorphic or no more reductions can be made
        while not nx.is_isomorphic(crit_graph1, crit_graph2):
            self.logger.info(f"Reduction iteration {iteration + 1}")
            reduction_made_this_iteration = False

            # STEP 1: First try type reduction based on the type reduction hierarchy
            type_reduction_applied = self._try_type_reduction(
                graph1, crit_graph1, graph2, crit_graph2
            )

            if type_reduction_applied:
                self.logger.info("Applied type reduction to one or both graphs")
                reduction_made_this_iteration = True
                # Check if graphs are isomorphic after type reduction
                if nx.is_isomorphic(crit_graph1, crit_graph2):
                    self.logger.info("Graphs became isomorphic after type reduction")
                    break

            # STEP 2: If type reduction wasn't enough, try node removal
            # Try to reduce different point types in order
            for point_type in [
                CriticalPointType.END_POINT.value,
                CriticalPointType.INTERSECTION_POINT.value,
                CriticalPointType.CORNER_POINT.value,
            ]:
                # Determine which nodes to remove from which graph for this point type
                nodes_to_remove_g1, nodes_to_remove_g2 = (
                    self._handle_point_type_mismatch(
                        crit_graph1, crit_graph2, point_type
                    )
                )

                # Apply reductions to graph1 if needed
                for node_id in nodes_to_remove_g1:
                    graph1, crit_graph1 = self._apply_reduction_to_graphs(
                        graph1, crit_graph1, node_id, point_type
                    )
                    reduction_made_this_iteration = True
                    self.logger.info(f"Removed {point_type} node {node_id} from graph1")

                # Apply reductions to graph2 if needed
                for node_id in nodes_to_remove_g2:
                    graph2, crit_graph2 = self._apply_reduction_to_graphs(
                        graph2, crit_graph2, node_id, point_type
                    )
                    reduction_made_this_iteration = True
                    self.logger.info(f"Removed {point_type} node {node_id} from graph2")

                # Check if graphs are isomorphic after this point type reduction
                if nx.is_isomorphic(crit_graph1, crit_graph2):
                    self.logger.info(
                        f"Graphs became isomorphic after {point_type} reduction"
                    )
                    break

            # If no reductions were made this iteration, we can't make the graphs isomorphic
            if not reduction_made_this_iteration:
                self.logger.warning("Cannot make graphs isomorphic with current rules")
                break

            iteration += 1
            # To prevent infinite loops, limit the number of iterations
            if iteration >= 10:  # arbitrary limit
                self.logger.warning("Reached maximum reduction iterations, stopping")
                break

        return graph1, graph2

    def _try_type_reduction(
        self,
        graph1: nx.Graph,
        crit_graph1: nx.Graph,
        graph2: nx.Graph,
        crit_graph2: nx.Graph,
    ) -> bool:
        """
        Try to apply type reduction to nodes based on the type_reduction_map hierarchy.
        This may convert an INTERSECTION_POINT to a CORNER_POINT, for example.

        Args:
            graph1: First original graph
            crit_graph1: First critical point graph
            graph2: Second original graph
            crit_graph2: Second critical point graph

        Returns:
            bool: True if any reductions were applied, False otherwise
        """
        reduction_applied = False

        # Get counts of each point type in both graphs
        counts1 = self._count_critical_points(crit_graph1)
        counts2 = self._count_critical_points(crit_graph2)

        # First, check for potential reductions in graph1
        reduction_applied |= self._apply_type_reduction_to_graph(
            graph1, crit_graph1, counts1, counts2
        )

        # Then, check for potential reductions in graph2
        reduction_applied |= self._apply_type_reduction_to_graph(
            graph2, crit_graph2, counts2, counts1
        )

        return reduction_applied

    def _apply_type_reduction_to_graph(
        self,
        graph: nx.Graph,
        crit_graph: nx.Graph,
        graph_counts: Dict[str, int],
        other_counts: Dict[str, int],
    ) -> bool:
        """
        Apply type reduction to a specific graph based on the type_reduction_map.

        Args:
            graph: The original graph to modify
            crit_graph: The critical point graph to modify
            graph_counts: Point type counts for this graph
            other_counts: Point type counts for the other graph

        Returns:
            bool: True if any reductions were applied, False otherwise
        """
        reduction_applied = False

        # Iterate through the type reduction map
        for higher_type, lower_type in self.type_reduction_map.items():
            # Check if this graph has more of the higher type than the other graph
            if graph_counts.get(higher_type, 0) > other_counts.get(higher_type, 0):
                diff = graph_counts.get(higher_type, 0) - other_counts.get(
                    higher_type, 0
                )
                self.logger.info(
                    f"Graph has {diff} more {higher_type} than the other graph"
                )

                # Find nodes of the higher type
                nodes_of_type = [
                    node
                    for node, data in crit_graph.nodes(data=True)
                    if higher_type in data.get("labels", [])
                ]

                # If we have nodes to reduce
                if nodes_of_type:
                    # Calculate similarity to find the best candidates for reduction
                    # For simplicity, we'll just use the first 'diff' nodes, but this could be
                    # enhanced with similarity calculation to choose the most suitable candidates
                    nodes_to_reduce = nodes_of_type[:diff]

                    for node_id in nodes_to_reduce:
                        # Reduce the type in both the original and critical graphs
                        self.logger.info(
                            f"Reducing node {node_id} from {higher_type} to {lower_type}"
                        )

                        # Update node in original graph
                        if node_id in graph.nodes:
                            labels = list(graph.nodes[node_id].get("labels", []))
                            if higher_type in labels:
                                labels.remove(higher_type)
                                if lower_type not in labels:
                                    labels.append(lower_type)
                                graph.nodes[node_id]["labels"] = labels

                        # Update node in critical graph
                        if node_id in crit_graph.nodes:
                            labels = list(crit_graph.nodes[node_id].get("labels", []))
                            if higher_type in labels:
                                labels.remove(higher_type)
                                if lower_type not in labels:
                                    labels.append(lower_type)
                                crit_graph.nodes[node_id]["labels"] = labels

                        reduction_applied = True

        return reduction_applied

    def _handle_point_type_mismatch(
        self,
        crit_graph1: nx.Graph,
        crit_graph2: nx.Graph,
        point_type: str,
    ) -> Tuple[List[Any], List[Any]]:
        """
        Handle mismatch in a specific point type between two critical point graphs.
        Determines which nodes need to be removed from which graph to make them compatible.

        Args:
            crit_graph1: First critical point graph
            crit_graph2: Second critical point graph
            point_type: Type of critical point to handle

        Returns:
            Tuple of (nodes_to_remove_from_g1, nodes_to_remove_from_g2) - one list will be empty
        """
        # Count nodes by type in each graph
        counts1 = self._count_critical_points(crit_graph1)
        counts2 = self._count_critical_points(crit_graph2)

        count1 = counts1.get(point_type, 0)
        count2 = counts2.get(point_type, 0)

        # If counts match, no action needed
        if count1 == count2:
            return [], []

        self.logger.info(
            f"Mismatch in {point_type} count: graph1={count1}, graph2={count2}"
        )

        # Get nodes of specified type from each graph
        nodes1 = [
            node
            for node, data in crit_graph1.nodes(data=True)
            if point_type in data.get("labels", [])
        ]

        nodes2 = [
            node
            for node, data in crit_graph2.nodes(data=True)
            if point_type in data.get("labels", [])
        ]

        if count1 > count2:
            # Graph1 has more points of this type, identify nodes to remove
            diff = count1 - count2
            nodes_to_remove = self._identify_nodes_to_remove(
                crit_graph1, nodes1, crit_graph2, nodes2, point_type, diff
            )
            return nodes_to_remove, []
        else:
            # Graph2 has more points of this type, identify nodes to remove
            diff = count2 - count1
            nodes_to_remove = self._identify_nodes_to_remove(
                crit_graph2, nodes2, crit_graph1, nodes1, point_type, diff
            )
            return [], nodes_to_remove

    def _apply_reduction_to_graphs(
        self,
        original_graph: nx.Graph,
        critical_graph: nx.Graph,
        node_id_crit: Any,
        critical_point_type: str,
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Apply reduction by removing nodes from both the original graph and its critical point graph.
        For END_POINTs, removes the path up to the next critical point.
        For other point types, removes just the critical point itself.

        Args:
            original_graph: The full original graph to modify
            critical_graph: The corresponding critical point graph
            node_id_crit: ID of the critical point to remove
            critical_point_type: Type of the critical point

        Returns:
            Tuple of (modified_original_graph, modified_critical_graph)
        """
        # For END_POINTs, we need to find and remove the entire path up to the next critical point
        if critical_point_type == CriticalPointType.END_POINT.value:
            # Find all nodes to remove including the path to the next critical point
            nodes_to_remove = self._find_endpoint_path_to_remove(
                original_graph, node_id_crit
            )
            self.logger.info(
                f"Removing endpoint {node_id_crit} and its path ({len(nodes_to_remove)} nodes)"
            )

            # Remove nodes from original graph
            for node in nodes_to_remove:
                if node in original_graph:
                    original_graph.remove_node(node)
        else:
            # For other critical points, just remove the single node
            self.logger.info(
                f"Removing single {critical_point_type} node {node_id_crit}"
            )
            if node_id_crit in original_graph:
                original_graph.remove_node(node_id_crit)

        # Remove the critical point from the critical graph
        if node_id_crit in critical_graph:
            critical_graph.remove_node(node_id_crit)

        return original_graph, critical_graph

    def _find_endpoint_path_to_remove(
        self, graph: nx.Graph, endpoint_id: Any
    ) -> List[Any]:
        """
        Find all nodes on the path from an endpoint to the next critical point.

        Args:
            graph: The original graph
            endpoint_id: ID of the endpoint node

        Returns:
            List of node IDs to remove (including the endpoint itself)
        """
        nodes_to_remove = [endpoint_id]

        # Start BFS from the endpoint
        visited = {endpoint_id}
        queue = list(graph.neighbors(endpoint_id))

        while queue:
            current = queue.pop(0)

            # Skip if already visited
            if current in visited:
                continue

            visited.add(current)

            # Check if this is a critical point
            node_data = graph.nodes[current]
            labels = node_data.get("labels", [])
            is_critical = any(label in self.critical_point_types for label in labels)

            if is_critical:
                # Found another critical point, stop the path here (don't include this node)
                continue

            # Add this non-critical node to the removal list
            nodes_to_remove.append(current)

            # Add neighbors to the queue
            for neighbor in graph.neighbors(current):
                if neighbor not in visited:
                    queue.append(neighbor)

        return nodes_to_remove

    def _identify_nodes_to_remove(
        self,
        graph_extra: nx.Graph,
        nodes_extra: List[Any],
        graph_fewer: nx.Graph,
        nodes_fewer: List[Any],
        point_type: str,
        difference: int,
    ) -> List[Any]:
        """
        Identify which nodes of a specific type should be removed from graph_extra.

        Args:
            graph_extra: Graph with more points of the specified type
            nodes_extra: Nodes of the specified type in graph_extra
            graph_fewer: Graph with fewer points of the specified type
            nodes_fewer: Nodes of the specified type in graph_fewer
            point_type: Type of critical point to consider
            difference: Number of points to remove

        Returns:
            List of node IDs to remove from graph_extra
        """
        self.logger.info(f"Found {len(nodes_extra)} {point_type} in graph_extra")
        self.logger.info(f"Found {len(nodes_fewer)} {point_type} in graph_fewer")

        # Calculate similarity between nodes
        similarity_pairs = []
        for node1 in nodes_extra:
            for node2 in nodes_fewer:
                similarity = self.similarity_calculator.calculate_node_similarity(
                    graph_extra, graph_fewer, node1, node2, self.properties_to_compare
                )
                similarity_pairs.append((node1, node2, similarity))

        # Sort by similarity (highest first)
        similarity_pairs.sort(key=lambda x: x[2], reverse=True)

        # Find best matches using greedy approach
        matched_extra_nodes = set()
        matched_fewer_nodes = set()
        matches = []

        for node1, node2, similarity in similarity_pairs:
            if node1 not in matched_extra_nodes and node2 not in matched_fewer_nodes:
                matched_extra_nodes.add(node1)
                matched_fewer_nodes.add(node2)
                matches.append((node1, node2, similarity))

                if len(matches) == len(nodes_fewer):
                    # We've matched all nodes from graph_fewer
                    break

        # Find nodes to remove (unmatched or lowest similarity)
        unmatched_nodes = [
            node for node in nodes_extra if node not in matched_extra_nodes
        ]

        nodes_to_remove = []
        # Add unmatched nodes first
        nodes_to_remove.extend(unmatched_nodes)

        # If we need to remove more, start from the lowest similarity matches
        if len(nodes_to_remove) < difference:
            # Sort matches by similarity (lowest first)
            matches.sort(key=lambda x: x[2])

            # Add nodes from lowest similarity matches
            for node1, _, _ in matches[: difference - len(nodes_to_remove)]:
                nodes_to_remove.append(node1)

        # Return only the required number of nodes
        return nodes_to_remove[:difference]

    def _count_critical_points(self, graph: nx.Graph) -> Dict[str, int]:
        """
        Count critical points by type in a graph.

        Args:
            graph: The graph containing nodes to count

        Returns:
            Dictionary mapping point type to count
        """
        counts = {}
        for _, data in graph.nodes(data=True):
            labels = data.get("labels", [])
            for label in labels:
                if label in self.critical_point_types:
                    counts[label] = counts.get(label, 0) + 1

        return counts

    def _has_path_excluding_others(
        self, graph: nx.Graph, source: Any, target: Any, critical_points: List[Any]
    ) -> bool:
        """
        Check if there's a path between source and target that doesn't go through other critical points.

        Args:
            graph: Original graph
            source: Source node
            target: Target node
            critical_points: List of all critical points

        Returns:
            True if there's a valid path, False otherwise
        """
        # Create a subgraph excluding other critical points
        excluded_nodes = [
            node for node in critical_points if node != source and node != target
        ]
        subgraph = graph.copy()
        subgraph.remove_nodes_from(excluded_nodes)

        try:
            nx.shortest_path(subgraph, source, target)
            return True
        except nx.NetworkXNoPath:
            return False
