import math
from typing import List, Tuple, Type
import networkx as nx
import uuid
from service.analysis_result_persistence_service import AnalysisResultPersistenceService
from service.graph_analysis.analyzers.base_analyzer import BaseAnalyzer
from common.decorator import timed


class NetworkxGraphAnalysis:
    def __init__(
        self,
        graph: nx.Graph,
        analysis_result_persistence_service: AnalysisResultPersistenceService,
        merge_threshold: float = 10.0,
    ):
        self.graph = graph
        self.analyzers: List[BaseAnalyzer] = []
        self.analysis_result_persistence_service = analysis_result_persistence_service
        self.merge_threshold = merge_threshold

    def add_analyzer(self, analyzer_class: Type[BaseAnalyzer]):
        analyzer = analyzer_class(self.graph)
        self.analyzers.append(analyzer)

    @timed(label="merge_close_intersection_points")
    def merge_close_intersection_points(self, threshold_distance: float = None):
        """
        Merges intersection points that are close to each other and connected by a short vector.

        Args:
            threshold_distance (float, optional): Maximum distance between points to be considered for merging.
                If None, uses the instance's merge_threshold.
        """
        threshold_distance = (
            threshold_distance
            if threshold_distance is not None
            else self.merge_threshold
        )

        # Count intersection points before merging
        initial_intersection_nodes = [
            node for node in self.graph.nodes if self.graph.degree[node] > 2
        ]
        print(
            f"Initial number of intersection points: {len(initial_intersection_nodes)}"
        )

        modified = True
        merge_count = 0

        while modified:
            modified = False
            intersection_nodes = []

            # Find all nodes that are intersection points (degree > 2)
            for node in self.graph.nodes:
                if self.graph.degree[node] > 2:
                    intersection_nodes.append(node)

            # Check all pairs of intersection points
            for i in range(len(intersection_nodes)):
                if i >= len(
                    intersection_nodes
                ):  # Check if i is still valid after possible removals
                    break

                node1 = intersection_nodes[i]
                if (
                    node1 not in self.graph.nodes
                ):  # Skip if node was removed in a previous iteration
                    continue

                node1_data = self.graph.nodes[node1]

                for j in range(i + 1, len(intersection_nodes)):
                    if j >= len(intersection_nodes):  # Check if j is still valid
                        break

                    node2 = intersection_nodes[j]
                    if node2 not in self.graph.nodes:  # Skip if node was removed
                        continue

                    # Check if nodes are directly connected
                    if not self.graph.has_edge(node1, node2):
                        continue

                    node2_data = self.graph.nodes[node2]

                    # Calculate vector length directly from coordinates
                    vector_length = self.calculate_length(
                        (node1_data["x"], node1_data["y"]),
                        (node2_data["x"], node2_data["y"]),
                    )

                    # If the connecting vector is short enough, merge the points
                    if vector_length <= threshold_distance:
                        print(
                            f"Merging intersection points: {node1} and {node2} connected by vector of length {vector_length}"
                        )

                        # Create a new point at the average position
                        merged_x = (node1_data["x"] + node2_data["x"]) / 2
                        merged_y = (node1_data["y"] + node2_data["y"]) / 2
                        merged_normalized_x = (
                            node1_data["normalized_x"] + node2_data["normalized_x"]
                        ) / 2
                        merged_normalized_y = (
                            node1_data["normalized_y"] + node2_data["normalized_y"]
                        ) / 2

                        # Get all neighbors except the other point being merged
                        neighbors1 = list(self.graph.neighbors(node1))
                        neighbors2 = list(self.graph.neighbors(node2))

                        if node2 in neighbors1:
                            neighbors1.remove(node2)
                        if node1 in neighbors2:
                            neighbors2.remove(node1)

                        merged_node = str(uuid.uuid4())

                        print(f"Created merged node with ID: {merged_node}")

                        self.graph.add_node(
                            merged_node,
                            x=merged_x,
                            y=merged_y,
                            normalized_x=merged_normalized_x,
                            normalized_y=merged_normalized_y,
                        )

                        # Connect all neighbors to the new node
                        for neighbor in neighbors1 + neighbors2:
                            # Get edge attributes for the original connections
                            if self.graph.has_edge(node1, neighbor):
                                edge_data = self.graph.get_edge_data(node1, neighbor)
                                # Recalculate length for the new connection
                                neighbor_data = self.graph.nodes[neighbor]
                                length = self.calculate_length(
                                    (merged_x, merged_y),
                                    (neighbor_data["x"], neighbor_data["y"]),
                                )
                                # Create new edge with adapted properties
                                new_edge_data = edge_data.copy()
                                new_edge_data["length"] = length
                                if (
                                    new_edge_data.get("x1") == node1_data["x"]
                                    and new_edge_data.get("y1") == node1_data["y"]
                                ):
                                    new_edge_data["x1"] = merged_x
                                    new_edge_data["y1"] = merged_y
                                elif (
                                    new_edge_data.get("x2") == node1_data["x"]
                                    and new_edge_data.get("y2") == node1_data["y"]
                                ):
                                    new_edge_data["x2"] = merged_x
                                    new_edge_data["y2"] = merged_y
                                self.graph.add_edge(
                                    merged_node, neighbor, **new_edge_data
                                )

                            elif self.graph.has_edge(node2, neighbor):
                                edge_data = self.graph.get_edge_data(node2, neighbor)
                                # Recalculate length for the new connection
                                neighbor_data = self.graph.nodes[neighbor]
                                length = self.calculate_length(
                                    (merged_x, merged_y),
                                    (neighbor_data["x"], neighbor_data["y"]),
                                )
                                # Create new edge with adapted properties
                                new_edge_data = edge_data.copy()
                                new_edge_data["length"] = length
                                if (
                                    new_edge_data.get("x1") == node2_data["x"]
                                    and new_edge_data.get("y1") == node2_data["y"]
                                ):
                                    new_edge_data["x1"] = merged_x
                                    new_edge_data["y1"] = merged_y
                                elif (
                                    new_edge_data.get("x2") == node2_data["x"]
                                    and new_edge_data.get("y2") == node2_data["y"]
                                ):
                                    new_edge_data["x2"] = merged_x
                                    new_edge_data["y2"] = merged_y
                                self.graph.add_edge(
                                    merged_node, neighbor, **new_edge_data
                                )

                        # Remove original nodes
                        self.graph.remove_node(node1)
                        self.graph.remove_node(node2)

                        merge_count += 1
                        modified = True
                        break  # Break inner loop as node1 no longer exists

                if modified:
                    break  # Break outer loop to restart with the modified graph

        # Count intersection points after merging
        final_intersection_nodes = [
            node for node in self.graph.nodes if self.graph.degree[node] > 2
        ]
        print(f"Final number of intersection points: {len(final_intersection_nodes)}")
        print(f"Total number of merges performed: {merge_count}")

        if merge_count > 0:
            print(
                f"Merged {merge_count} pairs of intersection points using threshold distance: {threshold_distance}"
            )
            # Print some information about the merged nodes for debugging
            for node in self.graph.nodes:
                node_data = self.graph.nodes[node]
                if "merged_from" in node_data:
                    print(
                        f"Merged node {node}: id={node_data.get('id', 'N/A')}, "
                        f"position=({node_data.get('x', 'N/A')}, {node_data.get('y', 'N/A')}), "
                        f"degree={self.graph.degree[node]}, "
                        f"merged_from={node_data.get('merged_from', 'N/A')}, "
                        f"line_count={len(node_data.get('lines', []))}"
                    )
        else:
            print(
                f"No intersection points were merged (threshold distance: {threshold_distance})"
            )

    def analyze_graph(self, image_id: str, session_id: str):
        print(
            "Starting graph analysis with analyzers: ",
            [type(analyzer).__name__ for analyzer in self.analyzers],
        )

        # Graph exposition analysis
        for analyzer in self.analyzers:
            result = analyzer.analyze()
            self.analysis_result_persistence_service.save_analysis_result(
                analyzer, result, image_id, session_id
            )

    def calculate_length(
        self, coordinates1: Tuple[float, float], coordinates2: Tuple[float, float]
    ) -> float:
        dx = coordinates2[0] - coordinates1[0]
        dy = coordinates2[1] - coordinates1[1]
        return math.hypot(dx, dy)
