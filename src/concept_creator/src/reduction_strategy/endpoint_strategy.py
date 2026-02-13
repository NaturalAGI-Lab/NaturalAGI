import logging
from typing import Tuple, List, Any

import networkx as nx
from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils
from src.utils.distance_matrix_calculator import DistanceMatrixCalculator
from src.utils.endpoint_direction_visitor import EndpointDirectionVisitor
from src.node_similarity_calculator import NodeSimilarityCalculator

from .abstract_strategy import AbstractReductionStrategy

CONCEPT = "concept"
IMAGE = "image"

properties_to_compare = set(
    ["normalized_x", "normalized_y", "direction_x", "direction_y"]
)


class EndpointReductionStrategy(AbstractReductionStrategy):
    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        super().__init__(node_similarity_calculator)
        self.logger = logging.getLogger(__name__)
        self.distance_threshold = 0.31
        self.distance_matrix_calculator = DistanceMatrixCalculator()
        self.endpoint_direction_visitor = EndpointDirectionVisitor()

    def reduce(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        concept_graph = self._apply_degree_reduction(concept_graph)
        image_graph = self._apply_degree_reduction(image_graph)

        concept_endpoints = self._get_endpoints(concept_graph)
        image_endpoints = self._get_endpoints(image_graph)

        if not concept_endpoints and not image_endpoints:
            self.logger.info(
                "Concept and image have no endpoints. Returning original graphs."
            )
            return concept_graph, image_graph

        if not concept_endpoints and image_endpoints:
            self.logger.info(
                "Concept has no endpoints. Reducing all endpoints in image."
            )
            image_graph = self._apply_reduction(image_graph, image_endpoints)
            return concept_graph, image_graph

        if concept_endpoints and not image_endpoints:
            self.logger.info(
                "Image has no endpoints. Reducing all endpoints in concept."
            )
            concept_graph = self._apply_reduction(concept_graph, concept_endpoints)
            return concept_graph, image_graph

        self.endpoint_direction_visitor.visit(concept_graph)
        self.endpoint_direction_visitor.visit(image_graph)

        distance_matrix = self.distance_matrix_calculator.calculate_distance_matrix(
            concept_graph,
            image_graph,
            concept_endpoints,
            image_endpoints,
            properties_to_compare,
        )

        concept_endpoints_above_threshold = (
            self.distance_matrix_calculator.find_points_above_distance_threshold(
                distance_matrix, concept_endpoints, self.distance_threshold, axis=1
            )
        )
        image_endpoints_above_threshold = (
            self.distance_matrix_calculator.find_points_above_distance_threshold(
                distance_matrix.T, image_endpoints, self.distance_threshold, axis=1
            )
        )

        if concept_endpoints_above_threshold:
            self.logger.info(
                f"Concept endpoints below threshold ({len(concept_endpoints_above_threshold)}): {concept_endpoints_above_threshold}"
            )
            concept_graph = self._apply_reduction(
                concept_graph, concept_endpoints_above_threshold
            )

        if image_endpoints_above_threshold:
            self.logger.info(
                f"Image endpoints below threshold ({len(image_endpoints_above_threshold)}): {image_endpoints_above_threshold}"
            )
            image_graph = self._apply_reduction(
                image_graph, image_endpoints_above_threshold
            )

        # Second pass: handle count mismatch
        concept_endpoints = self._get_endpoints(concept_graph)
        image_endpoints = self._get_endpoints(image_graph)

        len_concept_endpoints = len(concept_endpoints)
        len_image_endpoints = len(image_endpoints)

        if len_concept_endpoints == 0 and len_image_endpoints > 0:
            self.logger.info(
                "Concept has no endpoints after first pass. Reducing all remaining endpoints in image."
            )
            image_graph = self._apply_reduction(image_graph, image_endpoints)
            return concept_graph, image_graph

        if len_image_endpoints == 0 and len_concept_endpoints > 0:
            self.logger.info(
                "Image has no endpoints after first pass. Reducing all remaining endpoints in concept."
            )
            concept_graph = self._apply_reduction(concept_graph, concept_endpoints)
            return concept_graph, image_graph

        if len_concept_endpoints == len_image_endpoints:
            self.logger.info(
                "Concept and image have the same number of endpoints. No reduction needed."
            )
            return concept_graph, image_graph

        if len_concept_endpoints > len_image_endpoints:
            points_large = concept_endpoints
            graph_to_reduce = CONCEPT
        else:
            points_large = image_endpoints
            graph_to_reduce = IMAGE

        self.endpoint_direction_visitor.visit(concept_graph)
        self.endpoint_direction_visitor.visit(image_graph)

        distance_matrix = self.distance_matrix_calculator.calculate_distance_matrix(
            concept_graph,
            image_graph,
            concept_endpoints,
            image_endpoints,
            properties_to_compare,
        )

        axis = 0 if len_concept_endpoints < len_image_endpoints else 1

        excess_endpoints_to_remove = (
            self.distance_matrix_calculator.find_points_for_difference(
                distance_matrix,
                points_large,
                abs(len_concept_endpoints - len_image_endpoints),
                axis=axis,
            )
        )

        if excess_endpoints_to_remove:
            self.logger.info(
                f"Excess endpoints to remove ({len(excess_endpoints_to_remove)}): {excess_endpoints_to_remove}"
            )

        if graph_to_reduce == CONCEPT:
            concept_graph = self._apply_reduction(
                concept_graph, excess_endpoints_to_remove
            )
        else:
            image_graph = self._apply_reduction(image_graph, excess_endpoints_to_remove)
        return concept_graph, image_graph

    def _apply_degree_reduction(self, graph: nx.Graph) -> nx.Graph:
        for node, data in graph.nodes(data=True):
            if GraphUtils.is_endpoint(data) and not graph.degree(node) == 1:
                self.logger.info(
                    f"Node {node} is an endpoint but has degree {graph.degree(node)}. Removing endpoint label and adding corner point label."
                )
                graph.nodes[node]["labels"].remove(CriticalPointType.END_POINT.value)
                graph.nodes[node]["labels"].append(CriticalPointType.CORNER_POINT.value)
        return graph

    def _get_endpoints(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_endpoint(data)
            or self._node_is_semantically_endpoint(node, graph)
        ]

    def _node_is_semantically_endpoint(self, node: Any, graph: nx.Graph) -> bool:
        data = graph.nodes[node]
        labels = data.get("labels", [])

        # A node is semantically an endpoint if it has only one connection
        # and is not a start point
        is_endpoint = (
            graph.degree(node) == 1
            and CriticalPointType.START_POINT.value not in labels
        )

        # If it's an endpoint but not labeled as one, add the label
        if is_endpoint and not any(
            pt.value in labels
            for pt in [CriticalPointType.END_POINT, CriticalPointType.START_POINT]
        ):
            self.logger.info(
                f"Node {node} is an endpoint but not labeled as one. Adding label {CriticalPointType.END_POINT.value}."
            )
            data["labels"].clear()
            data["labels"].append(CriticalPointType.END_POINT.value)
            data["labels"].append("Point")

        return is_endpoint

    def _apply_reduction(self, graph: nx.Graph, endpoints: List[Any]) -> nx.Graph:
        relink_edges: set[tuple[Any, Any]] = set()
        all_nodes_to_remove = set()
        for endpoint_id in endpoints:
            if endpoint_id in graph:
                path_nodes = self._find_endpoint_path_to_remove(graph, endpoint_id)
                all_nodes_to_remove.update(path_nodes)

        if all_nodes_to_remove:
            self.logger.info(f"Removing {len(all_nodes_to_remove)} nodes from graph.")
            graph.remove_nodes_from(all_nodes_to_remove)
            self.logger.info(
                f"Graph after reduction: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
            )
        # relink preserved neighbors to the target critical/intersection node
        for u, v in relink_edges:
            if u in graph and v in graph and not graph.has_edge(u, v):
                graph.add_edge(u, v)

        return graph

    def _find_endpoint_path_to_remove(
        self, graph: nx.Graph, endpoint_id: Any
    ) -> List[Any]:
        nodes_on_path = [endpoint_id]
        queue = list(graph.neighbors(endpoint_id))
        visited = {endpoint_id}

        path_found = False

        while queue:
            current_node = queue.pop(0)

            if current_node in visited:
                continue
            visited.add(current_node)

            node_data = graph.nodes[current_node]

            is_intersection = (
                GraphUtils.is_intersection_point(node_data)
                or graph.degree(current_node) > 2
            )

            if is_intersection:
                path_found = True
                break
            else:
                nodes_on_path.append(current_node)
                for neighbor in graph.neighbors(current_node):
                    if neighbor not in visited:
                        queue.append(neighbor)

        if not path_found:
            self.logger.error(
                f"No path found for endpoint {endpoint_id}. Returning empty list."
            )
            raise ValueError(f"No path found for endpoint {endpoint_id}.")

        return nodes_on_path
