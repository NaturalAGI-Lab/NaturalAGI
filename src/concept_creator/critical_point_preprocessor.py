import logging
import networkx as nx
from typing import Dict, List, Tuple, Any, Set
from node_similarity_calculator import NodeSimilarityCalculator


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
            "IntersectionPoint": "CornerPoint",
            "CornerPoint": "Point",
            "EndPoint": "Point",  # Added to enable reduction when needed
        }

    def preprocess_graphs(
        self, graph1: nx.Graph, graph2: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Preprocess two graphs to ensure they have compatible critical points.

        Args:
            graph1: First graph to preprocess
            graph2: Second graph to preprocess

        Returns:
            Tuple of (preprocessed_graph1, preprocessed_graph2)
        """
        self.logger.info(f"Preprocessing graphs for critical point compatibility")

        # Create copies to avoid modifying original graphs
        preprocessed_graph1 = graph1.copy()
        preprocessed_graph2 = graph2.copy()

        # Extract critical points from both graphs
        critical_points1 = self._identify_critical_points(preprocessed_graph1)
        critical_points2 = self._identify_critical_points(preprocessed_graph2)

        # Count critical points by type
        cp_count1 = {
            cp_type: len(points) for cp_type, points in critical_points1.items()
        }
        cp_count2 = {
            cp_type: len(points) for cp_type, points in critical_points2.items()
        }

        self.logger.info(f"Graph1 critical points: {cp_count1}")
        self.logger.info(f"Graph2 critical points: {cp_count2}")

        # 1. Validate start points - each graph MUST have exactly one start point
        if cp_count1["StartPoint"] != 1 or cp_count2["StartPoint"] != 1:
            raise ValueError(
                f"Each graph must have exactly one StartPoint. Graph1: {cp_count1['StartPoint']}, Graph2: {cp_count2['StartPoint']}"
            )

        # 2. Process endpoints - reduce excess endpoints from the graph with more
        preprocessed_graph1, preprocessed_graph2 = self._align_endpoints(
            preprocessed_graph1, preprocessed_graph2, critical_points1, critical_points2
        )

        # Re-identify critical points after endpoint alignment
        critical_points1 = self._identify_critical_points(preprocessed_graph1)
        critical_points2 = self._identify_critical_points(preprocessed_graph2)

        # 3. Process IntersectionPoints and CornerPoints
        preprocessed_graph1, preprocessed_graph2 = (
            self._align_intersection_and_corner_points(
                preprocessed_graph1,
                preprocessed_graph2,
                critical_points1,
                critical_points2,
            )
        )

        # Final verification
        final_cp1 = self._identify_critical_points(preprocessed_graph1)
        final_cp2 = self._identify_critical_points(preprocessed_graph2)

        final_count1 = {cp_type: len(points) for cp_type, points in final_cp1.items()}
        final_count2 = {cp_type: len(points) for cp_type, points in final_cp2.items()}

        self.logger.info(
            f"After preprocessing - Graph1: {final_count1}, Graph2: {final_count2}"
        )

        # Verify that the critical point counts match between graphs
        for cp_type in ["StartPoint", "EndPoint", "IntersectionPoint", "CornerPoint"]:
            if final_count1[cp_type] != final_count2[cp_type]:
                self.logger.warning(
                    f"Critical point mismatch after preprocessing: {cp_type} - Graph1: {final_count1[cp_type]}, Graph2: {final_count2[cp_type]}"
                )

        return preprocessed_graph1, preprocessed_graph2

    def _align_endpoints(
        self,
        graph1: nx.Graph,
        graph2: nx.Graph,
        critical_points1: Dict[str, List[Any]],
        critical_points2: Dict[str, List[Any]],
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Align endpoints between graphs by removing excess endpoints from the graph with more.
        Uses similarity matching to determine which endpoints to remove.

        Args:
            graph1: First graph
            graph2: Second graph
            critical_points1: Critical points in graph1
            critical_points2: Critical points in graph2

        Returns:
            Tuple of (aligned_graph1, aligned_graph2)
        """
        endpoints1 = critical_points1["EndPoint"]
        endpoints2 = critical_points2["EndPoint"]

        # If the endpoint counts are already equal, no action needed
        if len(endpoints1) == len(endpoints2):
            self.logger.info("Endpoint counts already match. No alignment needed.")
            return graph1, graph2

        # Determine which graph has excess endpoints
        if len(endpoints1) > len(endpoints2):
            graph_to_reduce = graph1.copy()
            other_graph = graph2.copy()
            endpoints_to_reduce = endpoints1
            other_endpoints = endpoints2
            target_count = len(endpoints2)
            excess_count = len(endpoints1) - len(endpoints2)
            self.logger.info(
                f"Graph1 has excess endpoints: {len(endpoints1)} > {len(endpoints2)}"
            )
        else:
            graph_to_reduce = graph2.copy()
            other_graph = graph1.copy()
            endpoints_to_reduce = endpoints2
            other_endpoints = endpoints1
            target_count = len(endpoints1)
            excess_count = len(endpoints2) - len(endpoints1)
            self.logger.info(
                f"Graph2 has excess endpoints: {len(endpoints2)} > {len(endpoints1)}"
            )

        # Calculate which endpoints to remove based on similarity to endpoints in the other graph
        endpoints_to_remove = self._select_endpoints_to_remove(
            graph_to_reduce,
            other_graph,
            endpoints_to_reduce,
            other_endpoints,
            excess_count,
        )

        self.logger.info(f"Will remove {len(endpoints_to_remove)} endpoints")

        # Remove the selected endpoints - convert them to regular Points
        for endpoint in endpoints_to_remove:
            node_data = graph_to_reduce.nodes[endpoint]
            if "labels" in node_data and isinstance(node_data["labels"], list):
                # Remove the EndPoint label
                node_data["labels"] = [
                    label for label in node_data["labels"] if label != "EndPoint"
                ]
                self.logger.info(f"Reduced endpoint {endpoint} to Point")

        # Return the graphs in the original order
        if len(endpoints1) > len(endpoints2):
            return graph_to_reduce, other_graph
        else:
            return other_graph, graph_to_reduce

    def _select_endpoints_to_remove(
        self,
        graph_with_excess: nx.Graph,
        other_graph: nx.Graph,
        excess_endpoints: List[Any],
        other_endpoints: List[Any],
        count_to_remove: int,
    ) -> List[Any]:
        """
        Select which endpoints to remove based on their similarity to endpoints in the other graph.
        Endpoints with the lowest similarity scores will be removed.

        Args:
            graph_with_excess: The graph with excess endpoints
            other_graph: The graph with fewer endpoints
            excess_endpoints: List of endpoints in the graph with excess
            other_endpoints: List of endpoints in the other graph
            count_to_remove: Number of endpoints to remove

        Returns:
            List of endpoints to remove
        """
        if count_to_remove <= 0:
            return []

        # Calculate similarity scores between all pairs of endpoints
        endpoint_scores = []

        for excess_ep in excess_endpoints:
            # Find the best matching endpoint in the other graph
            best_similarity = -1
            for other_ep in other_endpoints:
                similarity = self.similarity_calculator.calculate_node_similarity(
                    graph_with_excess, other_graph, excess_ep, other_ep
                )
                if similarity > best_similarity:
                    best_similarity = similarity

            # Store the endpoint and its best similarity score
            endpoint_scores.append((excess_ep, best_similarity))

        # Sort by similarity score (ascending - we want to remove the least similar ones)
        endpoint_scores.sort(key=lambda x: x[1])

        # Return the endpoints with the lowest similarity scores
        to_remove = [ep for ep, _ in endpoint_scores[:count_to_remove]]

        # Log the similarity scores for removed endpoints
        for ep, score in endpoint_scores[:count_to_remove]:
            self.logger.info(
                f"Selected endpoint {ep} for removal with similarity score {score:.4f}"
            )

        return to_remove

    def _align_intersection_and_corner_points(
        self,
        graph1: nx.Graph,
        graph2: nx.Graph,
        critical_points1: Dict[str, List[Any]],
        critical_points2: Dict[str, List[Any]],
    ) -> Tuple[nx.Graph, nx.Graph]:
        """
        Align IntersectionPoints and CornerPoints between graphs.
        Uses similarity matching to determine which points to reduce.

        Rules:
        1. IntersectionPoints can be reduced to CornerPoints
        2. Both can be reduced to regular Points
        3. Ensure the counts of each type match between graphs

        Args:
            graph1: First graph
            graph2: Second graph
            critical_points1: Critical points in graph1
            critical_points2: Critical points in graph2

        Returns:
            Tuple of (aligned_graph1, aligned_graph2)
        """
        # Make copies to work with
        aligned_graph1 = graph1.copy()
        aligned_graph2 = graph2.copy()

        # Count points of each type
        intersection_count1 = len(critical_points1["IntersectionPoint"])
        intersection_count2 = len(critical_points2["IntersectionPoint"])
        corner_count1 = len(critical_points1["CornerPoint"])
        corner_count2 = len(critical_points2["CornerPoint"])

        self.logger.info(
            f"IntersectionPoints - Graph1: {intersection_count1}, Graph2: {intersection_count2}"
        )
        self.logger.info(
            f"CornerPoints - Graph1: {corner_count1}, Graph2: {corner_count2}"
        )

        # Case 1: Reduce IntersectionPoints to CornerPoints if needed
        if intersection_count1 > intersection_count2:
            # Select IntersectionPoints to reduce in graph1 based on similarity scores
            to_reduce = intersection_count1 - intersection_count2
            points_to_reduce = self._select_critical_points_to_transform(
                aligned_graph1,
                aligned_graph2,
                critical_points1["IntersectionPoint"],
                critical_points2["IntersectionPoint"],
                to_reduce,
            )

            self.logger.info(
                f"Reducing {len(points_to_reduce)} IntersectionPoints to CornerPoints in Graph1"
            )
            for point in points_to_reduce:
                self._transform_critical_point(
                    aligned_graph1, point, "IntersectionPoint", "CornerPoint"
                )

        elif intersection_count2 > intersection_count1:
            # Select IntersectionPoints to reduce in graph2 based on similarity scores
            to_reduce = intersection_count2 - intersection_count1
            points_to_reduce = self._select_critical_points_to_transform(
                aligned_graph2,
                aligned_graph1,
                critical_points2["IntersectionPoint"],
                critical_points1["IntersectionPoint"],
                to_reduce,
            )

            self.logger.info(
                f"Reducing {len(points_to_reduce)} IntersectionPoints to CornerPoints in Graph2"
            )
            for point in points_to_reduce:
                self._transform_critical_point(
                    aligned_graph2, point, "IntersectionPoint", "CornerPoint"
                )

        # Re-identify critical points after first transformation
        updated_cp1 = self._identify_critical_points(aligned_graph1)
        updated_cp2 = self._identify_critical_points(aligned_graph2)

        # Update counts
        intersection_count1 = len(updated_cp1["IntersectionPoint"])
        intersection_count2 = len(updated_cp2["IntersectionPoint"])
        corner_count1 = len(updated_cp1["CornerPoint"])
        corner_count2 = len(updated_cp2["CornerPoint"])

        self.logger.info(
            f"After first alignment - IntersectionPoints: Graph1={intersection_count1}, Graph2={intersection_count2}"
        )
        self.logger.info(
            f"After first alignment - CornerPoints: Graph1={corner_count1}, Graph2={corner_count2}"
        )

        # Case 2: If CornerPoints still don't match, reduce excess to regular Points
        if corner_count1 > corner_count2:
            # Select CornerPoints to reduce in graph1 based on similarity scores
            to_reduce = corner_count1 - corner_count2
            points_to_reduce = self._select_critical_points_to_transform(
                aligned_graph1,
                aligned_graph2,
                updated_cp1["CornerPoint"],
                updated_cp2["CornerPoint"],
                to_reduce,
            )

            self.logger.info(
                f"Reducing {len(points_to_reduce)} CornerPoints to Points in Graph1"
            )
            for point in points_to_reduce:
                self._transform_critical_point(
                    aligned_graph1, point, "CornerPoint", "Point"
                )

        elif corner_count2 > corner_count1:
            # Select CornerPoints to reduce in graph2 based on similarity scores
            to_reduce = corner_count2 - corner_count1
            points_to_reduce = self._select_critical_points_to_transform(
                aligned_graph2,
                aligned_graph1,
                updated_cp2["CornerPoint"],
                updated_cp1["CornerPoint"],
                to_reduce,
            )

            self.logger.info(
                f"Reducing {len(points_to_reduce)} CornerPoints to Points in Graph2"
            )
            for point in points_to_reduce:
                self._transform_critical_point(
                    aligned_graph2, point, "CornerPoint", "Point"
                )

        return aligned_graph1, aligned_graph2

    def _select_critical_points_to_transform(
        self,
        graph_with_excess: nx.Graph,
        other_graph: nx.Graph,
        excess_points: List[Any],
        other_points: List[Any],
        count_to_transform: int,
    ) -> List[Any]:
        """
        Select which critical points to transform based on their similarity to points in the other graph.
        Points with the lowest similarity scores will be transformed.

        Args:
            graph_with_excess: The graph with excess critical points
            other_graph: The graph with fewer critical points
            excess_points: List of critical points in the graph with excess
            other_points: List of critical points in the other graph
            count_to_transform: Number of points to transform

        Returns:
            List of points to transform
        """
        if count_to_transform <= 0 or not excess_points:
            return []

        # If there are no points in the other graph, we can't calculate similarities
        # So just take the first N points
        if not other_points:
            return excess_points[:count_to_transform]

        # Calculate similarity scores between all pairs of points
        point_scores = []

        for excess_pt in excess_points:
            # Find the best matching point in the other graph
            best_similarity = -1
            for other_pt in other_points:
                similarity = self.similarity_calculator.calculate_node_similarity(
                    graph_with_excess, other_graph, excess_pt, other_pt
                )
                if similarity > best_similarity:
                    best_similarity = similarity

            # Store the point and its best similarity score
            point_scores.append((excess_pt, best_similarity))

        # Sort by similarity score (ascending - we want to transform the least similar ones)
        point_scores.sort(key=lambda x: x[1])

        # Return the points with the lowest similarity scores
        points_to_transform = [pt for pt, _ in point_scores[:count_to_transform]]

        # Log the similarity scores for transformed points
        for pt, score in point_scores[:count_to_transform]:
            self.logger.info(
                f"Selected point {pt} for transformation with similarity score {score:.4f}"
            )

        return points_to_transform

    def _transform_critical_point(
        self,
        graph: nx.Graph,
        point: Any,
        from_type: str,
        to_type: str,
    ) -> None:
        """
        Transform a critical point from one type to another.

        Args:
            graph: Graph to modify
            point: Critical point to transform
            from_type: Original type to transform from
            to_type: Target type to transform to
        """
        node_data = graph.nodes[point]

        if "labels" in node_data:
            if isinstance(node_data["labels"], list):
                # Remove the from_type label
                node_data["labels"] = [
                    label for label in node_data["labels"] if label != from_type
                ]

                # Add the to_type label if not already present
                if to_type not in node_data["labels"]:
                    node_data["labels"].append(to_type)
                    self.logger.info(
                        f"Transformed critical point {point} from {from_type} to {to_type}"
                    )

    def _transform_critical_point_type(
        self,
        graph: nx.Graph,
        candidate_points: List[Any],
        from_type: str,
        to_type: str,
        count: int,
    ) -> None:
        """
        Transform multiple critical points from one type to another.

        Args:
            graph: Graph to modify
            candidate_points: List of points to potentially transform
            from_type: Original type to transform from
            to_type: Target type to transform to
            count: Number of points to transform
        """
        if not candidate_points or count <= 0:
            return

        # Limit to the requested count
        points_to_transform = candidate_points[:count]

        for point in points_to_transform:
            self._transform_critical_point(graph, point, from_type, to_type)

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
