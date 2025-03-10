import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Set, Any, Optional
from collections import defaultdict
import logging


class ConceptFormation:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_concept(self, training_graph_list: List[nx.Graph]) -> nx.Graph:
        """
        Create a concept graph by finding the intersection across all training samples.

        Args:
            training_graph_list: List of NetworkX graphs representing training samples

        Returns:
            A NetworkX graph representing the concept
        """
        if not training_graph_list:
            raise ValueError("No training graphs provided")

        # Start with the first sample as the initial concept
        concept_graph = training_graph_list[0].copy()

        # Iteratively refine by comparing with each training sample
        for i, sample_graph in enumerate(training_graph_list[1:], 1):
            self.logger.info(
                f"Processing training sample {i}/{len(training_graph_list)-1}"
            )

            # Find matching between critical points in both graphs
            point_matches = self._match_critical_points(concept_graph, sample_graph)

            # Update concept graph to keep only matched elements
            concept_graph = self._create_intersection_graph(
                concept_graph, sample_graph, point_matches
            )

            # Refine the concept graph
            concept_graph = self._refine_concept_graph(concept_graph)

            self.logger.info(
                f"After processing sample {i}, concept has {len(concept_graph.nodes())} nodes"
            )

        return concept_graph

    def _get_critical_points(self, graph: nx.Graph) -> Dict[str, Set]:
        """
        Extract critical points from a graph.

        Args:
            graph: NetworkX graph

        Returns:
            Dictionary mapping point type to set of node IDs
        """
        critical_points = {
            "intersection": set(),
            "corner": set(),
            "endpoint": set(),
            "start": set(),
        }

        for node, data in graph.nodes(data=True):
            # Check node labels or properties to identify critical points
            if "IntersectionPoint" in data.get("labels", []):
                critical_points["intersection"].add(node)

            if "CornerPoint" in data.get("labels", []):
                critical_points["corner"].add(node)

            if "EndPoint" in data.get("labels", []):
                critical_points["endpoint"].add(node)

            if "StartPoint" in data.get("labels", []):
                critical_points["start"].add(node)

        return critical_points

    def _calculate_point_similarity(
        self, point1_data: Dict, point2_data: Dict
    ) -> float:
        """
        Calculate similarity between two points based on their properties.

        Args:
            point1_data: Properties of first point
            point2_data: Properties of second point

        Returns:
            Similarity score between 0 and 1
        """
        # Weights for different property types
        weights = {"topological": 0.4, "geometric": 0.4, "segments": 0.2}

        similarity_scores = {"topological": 0.0, "geometric": 0.0, "segments": 0.0}

        # Topological similarity
        topo_features = [
            "intersection_points_count",
            "endpoints_count",
            "corner_points_count",
            "vectors_count",
            "cycle_count",
        ]

        topo_sim = 0.0
        topo_count = 0
        for feature in topo_features:
            if feature in point1_data and feature in point2_data:
                # Normalize difference between values to [0, 1]
                max_val = max(point1_data[feature], point2_data[feature])
                min_val = min(point1_data[feature], point2_data[feature])
                if max_val == 0:
                    sim = 1.0  # Both zero, perfect match
                else:
                    sim = min_val / max_val
                topo_sim += sim
                topo_count += 1

        if topo_count > 0:
            similarity_scores["topological"] = topo_sim / topo_count

        # Geometric similarity
        geo_sim = 0.0
        geo_count = 0

        # Coordinate similarity
        if "normalized_x" in point1_data and "normalized_x" in point2_data:
            x_diff = abs(point1_data["normalized_x"] - point2_data["normalized_x"])
            y_diff = abs(point1_data["normalized_y"] - point2_data["normalized_y"])
            # Convert to similarity (1 - normalized difference)
            coord_sim = (
                1.0 - (x_diff + y_diff) / 4.0
            )  # Max diff would be 2 for each dimension
            geo_sim += coord_sim
            geo_count += 1

        # Angle similarity
        if "angle" in point1_data and "angle" in point2_data:
            angle_diff = abs(point1_data["angle"] - point2_data["angle"])
            angle_diff = min(
                angle_diff, 360 - angle_diff
            )  # Handle circular nature of angles
            angle_sim = 1.0 - angle_diff / 180.0
            geo_sim += angle_sim
            geo_count += 1

        if geo_count > 0:
            similarity_scores["geometric"] = geo_sim / geo_count

        # Segment similarity
        if "segments" in point1_data and "segments" in point2_data:
            segments1 = set(point1_data["segments"])
            segments2 = set(point2_data["segments"])
            if not segments1 and not segments2:
                similarity_scores["segments"] = 1.0
            else:
                jaccard = len(segments1.intersection(segments2)) / len(
                    segments1.union(segments2)
                )
                similarity_scores["segments"] = jaccard

        # Weighted total similarity
        total_similarity = sum(weights[key] * similarity_scores[key] for key in weights)

        return total_similarity

    def _match_critical_points(
        self, graph1: nx.Graph, graph2: nx.Graph
    ) -> Dict[Any, Any]:
        """
        Find matching between critical points in two graphs.

        Args:
            graph1: First graph
            graph2: Second graph

        Returns:
            Dictionary mapping node IDs from graph1 to node IDs from graph2
        """
        # Get critical points from both graphs
        critical_points1 = self._get_critical_points(graph1)
        critical_points2 = self._get_critical_points(graph2)

        # Create similarity matrix for each critical point type
        matches = {}

        # For each type of critical point, find best matches
        for point_type in critical_points1:
            points1 = critical_points1[point_type]
            points2 = critical_points2[point_type]

            if not points1 or not points2:
                continue

            # Create similarity matrix
            similarity_matrix = np.zeros((len(points1), len(points2)))

            # Fill similarity matrix
            for i, p1 in enumerate(points1):
                for j, p2 in enumerate(points2):
                    p1_data = graph1.nodes[p1]
                    p2_data = graph2.nodes[p2]
                    similarity_matrix[i, j] = self._calculate_point_similarity(
                        p1_data, p2_data
                    )

            # Use Hungarian algorithm to find optimal matching
            try:
                from scipy.optimize import linear_sum_assignment

                row_indices, col_indices = linear_sum_assignment(
                    -similarity_matrix
                )  # Negative for maximization

                # Add matches that have sufficient similarity
                for i, j in zip(row_indices, col_indices):
                    if (
                        similarity_matrix[i, j] > 0.6
                    ):  # Threshold for acceptable similarity
                        p1 = list(points1)[i]
                        p2 = list(points2)[j]
                        matches[p1] = p2
            except ImportError:
                self.logger.warning(
                    "SciPy not available, using greedy matching instead"
                )
                # Fallback to greedy matching
                used_points2 = set()
                for p1 in points1:
                    best_match = None
                    best_similarity = 0.6  # Threshold
                    for p2 in points2:
                        if p2 in used_points2:
                            continue

                        p1_data = graph1.nodes[p1]
                        p2_data = graph2.nodes[p2]
                        similarity = self._calculate_point_similarity(p1_data, p2_data)

                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match = p2

                    if best_match:
                        matches[p1] = best_match
                        used_points2.add(best_match)

        return matches

    def _create_point_with_common_properties(
        self, point1_data: Dict, point2_data: Dict
    ) -> Dict:
        """
        Create a new point with properties common to both input points.

        Args:
            point1_data: Properties of first point
            point2_data: Properties of second point

        Returns:
            Dictionary of properties for the new point
        """
        new_point_data = {}

        # Copy labels
        labels1 = set(point1_data.get("labels", []))
        labels2 = set(point2_data.get("labels", []))
        new_point_data["labels"] = list(labels1.intersection(labels2))

        # Process common properties
        for prop in set(point1_data.keys()).intersection(set(point2_data.keys())):
            if prop == "labels":
                continue

            if point1_data[prop] == point2_data[prop]:
                # Exact match, keep the property
                new_point_data[prop] = point1_data[prop]
            elif isinstance(point1_data[prop], (int, float)) and isinstance(
                point2_data[prop], (int, float)
            ):
                # For numeric properties, take the average
                new_point_data[prop] = (point1_data[prop] + point2_data[prop]) / 2.0
            elif isinstance(point1_data[prop], list):
                # For lists (like segments), take the intersection
                if isinstance(point1_data[prop][0], (str, int, float)) and isinstance(
                    point2_data[prop][0], (str, int, float)
                ):
                    common = set(point1_data[prop]).intersection(set(point2_data[prop]))
                    if common:
                        new_point_data[prop] = list(common)

        return new_point_data

    def _create_vector_with_common_properties(
        self, vector1_data: Dict, vector2_data: Dict
    ) -> Dict:
        """
        Create a new vector with properties common to both input vectors.

        Args:
            vector1_data: Properties of first vector
            vector2_data: Properties of second vector

        Returns:
            Dictionary of properties for the new vector
        """
        # Similar to point properties but may have specific vector properties
        return self._create_point_with_common_properties(vector1_data, vector2_data)

    def _create_intersection_graph(
        self, graph1: nx.Graph, graph2: nx.Graph, point_matches: Dict
    ) -> nx.Graph:
        """
        Create an intersection graph containing only matched elements.

        Args:
            graph1: First graph
            graph2: Second graph
            point_matches: Dictionary mapping nodes from graph1 to nodes from graph2

        Returns:
            A new graph containing the intersection
        """
        intersection_graph = nx.Graph()

        # Add matched nodes to the intersection graph
        for node1, node2 in point_matches.items():
            node1_data = graph1.nodes[node1]
            node2_data = graph2.nodes[node2]

            # Create a new node with common properties
            new_node_data = self._create_point_with_common_properties(
                node1_data, node2_data
            )
            intersection_graph.add_node(node1, **new_node_data)

        # Add edges that exist in both graphs
        for node1, node2 in graph1.edges():
            if node1 in point_matches and node2 in point_matches:
                match1 = point_matches[node1]
                match2 = point_matches[node2]

                # Check if edge exists in graph2
                if graph2.has_edge(match1, match2):
                    # Get edge data from both graphs
                    edge1_data = graph1.get_edge_data(node1, node2)
                    edge2_data = graph2.get_edge_data(match1, match2)

                    # Create new edge with common properties
                    new_edge_data = self._create_vector_with_common_properties(
                        edge1_data, edge2_data
                    )
                    intersection_graph.add_edge(node1, node2, **new_edge_data)

        return intersection_graph

    def _refine_concept_graph(self, graph: nx.Graph) -> nx.Graph:
        """
        Refine the concept graph by removing isolated nodes and normalizing.

        Args:
            graph: Graph to refine

        Returns:
            Refined graph
        """
        # Remove isolated nodes
        isolated_nodes = [
            node for node, degree in dict(graph.degree()).items() if degree == 0
        ]
        graph.remove_nodes_from(isolated_nodes)

        # Ensure the graph is connected - keep only the largest component
        if len(graph) > 0 and not nx.is_connected(graph):
            largest_cc = max(nx.connected_components(graph), key=len)
            graph = graph.subgraph(largest_cc).copy()

        return graph
