import logging
import numpy as np
import networkx as nx
from typing import Any, List, Tuple

from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils
from node_similarity_calculator import NodeSimilarityCalculator
from .abstract_strategy import AbstractReductionStrategy


class IntersectionPointReductionStrategy(AbstractReductionStrategy):
    """
    This is basically the same as the intersection reduction strategy in the concept creator,
    but with the difference that we apply it to the image graph.
    """

    def __init__(
        self,
        node_similarity_calculator: NodeSimilarityCalculator,
        similarity_threshold: float = 0.5,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        super().__init__(node_similarity_calculator)
        self.logger = logger
        self.similarity_threshold = similarity_threshold

    def reduce(
        self,
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
    ) -> Tuple[nx.Graph, nx.Graph]:
        image_graph = self._apply_degree_reduction(image_graph)

        concept_intersection_points = self._get_intersection_points(concept_graph)
        image_intersection_points = self._get_intersection_points(image_graph)

        if not concept_intersection_points and not image_intersection_points:
            self.logger.info("Concept or image has no intersection points.")
            return image_graph, concept_graph

        if not concept_intersection_points and image_intersection_points:
            self.logger.info(
                "Concept has no intersection points. Removing intersection points from image."
            )
            image_graph = self._apply_reduction(image_graph, image_intersection_points)
            return image_graph, concept_graph

        if concept_intersection_points and not image_intersection_points:
            raise ValueError("Concept has intersection points but image does not.")

        len_concept_intersection_points = len(concept_intersection_points)
        len_image_intersection_points = len(image_intersection_points)

        if len_concept_intersection_points == len_image_intersection_points:
            self.logger.info(
                "Concept and image have the same number of intersection points. No reduction needed."
            )
            return image_graph, concept_graph

        if len_concept_intersection_points > len_image_intersection_points:
            raise ValueError(
                f"Concept has more intersection points than image. {len_concept_intersection_points} > {len_image_intersection_points}"
            )
        else:
            graph_large = image_graph
            graph_small = concept_graph
            points_large = image_intersection_points
            points_small = concept_intersection_points

        similarity_matrix = self.calculate_similarity_matrix(
            graph_large, graph_small, points_large, points_small
        )

        excess_intersection_points_to_remove = (
            self._identify_excess_intersection_points_to_remove(
                similarity_matrix,
                points_large,
                abs(len_concept_intersection_points - len_image_intersection_points),
            )
        )

        if excess_intersection_points_to_remove:
            self.logger.info(
                f"Excess intersection points to remove ({len(excess_intersection_points_to_remove)}): {excess_intersection_points_to_remove}"
            )

        image_graph = self._apply_reduction(
            image_graph, excess_intersection_points_to_remove
        )

        return image_graph, concept_graph

    def _apply_degree_reduction(self, graph: nx.Graph) -> nx.Graph:
        for node, data in graph.nodes(data=True):
            if GraphUtils.is_intersection_point(data):
                node_degree = graph.degree(node)
                if not node_degree > 2:
                    self.logger.info(
                        f"Removing IntersectionPoint label from {node} with degree {node_degree}"
                    )
                    labels = graph.nodes[node]["labels"]
                    labels.remove(CriticalPointType.INTERSECTION_POINT.value)
                    if node_degree == 1:
                        self.logger.info(
                            f"Adding EndPoint label to {node} with degree {node_degree}"
                        )
                        labels.append(CriticalPointType.END_POINT.value)
                    else:
                        self.logger.info(
                            f"Adding CornerPoint label to {node} with degree {node_degree}"
                        )
                        labels.append(CriticalPointType.CORNER_POINT.value)
                    graph.nodes[node]["labels"] = labels
        return graph

    def _get_intersection_points(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_intersection_point(data)
        ]

    def _find_intersection_points_below_threshold(
        self, similarity_matrix: np.ndarray, intersection_points: List[Any], axis: int
    ) -> List[Any]:
        intersection_points_below_threshold = []
        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        max_similarity = np.max(similarity_matrix, axis=axis)

        for i, intersection_point in enumerate(intersection_points):
            if max_similarity[i] < self.similarity_threshold:
                self.logger.info(
                    f"Intersection point {intersection_point} has similarity {max_similarity[i]} below threshold {self.similarity_threshold}. Adding to list of intersection points to remove."
                )
                intersection_points_below_threshold.append(intersection_point)
        return intersection_points_below_threshold

    def _apply_reduction(
        self, graph: nx.Graph, intersection_points: List[Any]
    ) -> nx.Graph:
        relink_edges: set[tuple[Any, Any]] = set()
        all_nodes_to_remove = set()
        for intersection_id in intersection_points:
            # capture neighbors BEFORE any modifications
            neighbors = list(graph.neighbors(intersection_id))

            # path_nodes to delete and the critical/intersection node to keep
            path_nodes, target_node = self._find_path_to_nearest_critical(
                graph, intersection_id
            )
            all_nodes_to_remove.update(path_nodes)

            # schedule relinking of original neighbors to the new critical node
            for nbr in neighbors:
                if nbr != target_node and nbr not in path_nodes:
                    relink_edges.add((nbr, target_node))

        if all_nodes_to_remove:
            self.logger.info(f"Removing {len(all_nodes_to_remove)} nodes from graph.")
            graph.remove_nodes_from(all_nodes_to_remove)
            self.logger.info(f"Graph after reduction has {len(graph.nodes)} nodes.")

        # relink preserved neighbors to the target critical/intersection node
        for u, v in relink_edges:
            if u in graph and v in graph and not graph.has_edge(u, v):
                graph.add_edge(u, v)

        return graph

    def _identify_excess_intersection_points_to_remove(
        self,
        similarity_matrix: np.ndarray,
        points_large: List[Any],
        difference: int,
    ) -> List[Any]:
        if difference <= 0:
            self.logger.error("Difference is less than or equal to 0. Raising error.")
            raise ValueError("Difference is less than or equal to 0.")

        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        max_similarities_per_large_point = np.max(similarity_matrix, axis=1)

        indexed_similarities = list(enumerate(max_similarities_per_large_point))

        indexed_similarities.sort(key=lambda x: x[1])

        indices_to_remove = [idx for idx, sim in indexed_similarities[:difference]]

        nodes_to_remove = [points_large[i] for i in indices_to_remove]

        self.logger.debug(
            f"Indices identified for removal based on lowest max similarity: {indices_to_remove}"
        )
        self.logger.debug(f"Nodes identified for removal: {nodes_to_remove}")

        return nodes_to_remove

    def _find_path_to_nearest_critical(
        self, graph: nx.Graph, start_node: Any
    ) -> Tuple[List[Any], Any]:
        """
        BFS from `start_node` (an excessive intersection) and return a path to the
        *nearest* **intersection point**, falling back to the nearest other critical
        point if no intersection exists at that distance.

        Returns
        -------
        Tuple[List[Any], Any]
            nodes_to_remove : list
                Every node from `start_node` up to *but not including* the chosen
                `target_node`.
            target_node : Any
                The intersection / critical node that will remain in the graph and
                to which old neighbours will be re‑linked.
        """
        from collections import deque

        visited: set[Any] = {start_node}
        queue = deque([(start_node, [start_node])])

        # We iterate level‑by‑level so we can prefer intersections at the same depth
        while queue:
            current_node, path = queue.popleft()
            depth_now = len(path)

            if current_node != start_node:
                node_data = graph.nodes[current_node]
                is_intersection = (
                    GraphUtils.is_intersection_point(node_data)
                    or graph.degree(current_node) > 2
                )
                is_critical = GraphUtils.is_critical_point(node_data)

                if is_intersection:
                    # Found nearest intersection – choose immediately.
                    target_node = current_node
                    path_nodes = path[:-1]  # exclude target itself
                    if start_node not in path_nodes:
                        path_nodes.append(start_node)
                    return path_nodes, target_node

                # Only choose a non‑intersection critical if *no* intersection exists
                # at the same BFS depth.  Defer the decision until siblings checked.
                if is_critical:
                    # Check if an unvisited intersection is queued at the same depth.
                    intersection_at_same_depth = any(
                        (len(p) == depth_now)
                        and (
                            GraphUtils.is_intersection_point(graph.nodes[n])
                            or graph.degree(n) > 2
                        )
                        for n, p in queue
                    )
                    if not intersection_at_same_depth:
                        target_node = current_node
                        path_nodes = path[:-1]
                        if start_node not in path_nodes:
                            path_nodes.append(start_node)
                        return path_nodes, target_node

            # Enqueue neighbours
            for neighbour in graph.neighbors(current_node):
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append((neighbour, path + [neighbour]))

        # Fallback – should never happen
        return [start_node], start_node
