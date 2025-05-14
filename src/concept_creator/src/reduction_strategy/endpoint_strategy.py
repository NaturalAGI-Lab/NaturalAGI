import logging
from typing import Tuple, List, Any, Dict

import numpy as np
import networkx as nx
from common.critical_point import CriticalPointType
from common.graph_utils import GraphUtils
from src.node_similarity_calculator import NodeSimilarityCalculator

from .abstract_strategy import AbstractReductionStrategy

CONCEPT = "concept"
IMAGE = "image"

class EndpointReductionStrategy(AbstractReductionStrategy):
    def __init__(self, node_similarity_calculator: NodeSimilarityCalculator):
        super().__init__(node_similarity_calculator)
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = 0.25

    def reduce(
        self, concept_graph: nx.Graph, image_graph: nx.Graph
    ) -> Tuple[nx.Graph, nx.Graph]:
        concept_endpoints = self._get_endpoints(concept_graph)
        image_endpoints = self._get_endpoints(image_graph)

        if not concept_endpoints and not image_endpoints:
            self.logger.info("Concept and image have no endpoints. Returning original graphs.")
            return concept_graph, image_graph
        
        if not concept_endpoints and image_endpoints:
            self.logger.info("Concept has no endpoints. Reducing all endpoints in image.")
            image_graph = self._apply_reduction(image_graph, image_endpoints)
            return concept_graph, image_graph
        
        if concept_endpoints and not image_endpoints:
            self.logger.info("Image has no endpoints. Reducing all endpoints in concept.")
            concept_graph = self._apply_reduction(concept_graph, concept_endpoints)
            return concept_graph, image_graph        

        similarity_matrix = self.calculate_similarity_matrix(
            concept_graph,
            image_graph,
            concept_endpoints,
            image_endpoints,
        )

        concept_endpoints_below_threshold = self._find_endpoints_below_threshold(
            similarity_matrix, concept_endpoints, axis=1
        )
        image_endpoints_below_threshold = self._find_endpoints_below_threshold(
            similarity_matrix.T, image_endpoints, axis=1
        )

        if concept_endpoints_below_threshold:
            self.logger.info(
                f"Concept endpoints below threshold ({len(concept_endpoints_below_threshold)}): {concept_endpoints_below_threshold}"
            )
            concept_graph = self._apply_reduction(
                concept_graph, concept_endpoints_below_threshold
            )

        if image_endpoints_below_threshold:
            self.logger.info(
                f"Image endpoints below threshold ({len(image_endpoints_below_threshold)}): {image_endpoints_below_threshold}"
            )
            image_graph = self._apply_reduction(
                image_graph, image_endpoints_below_threshold
            )

        # Second pass: handle count mismatch
        concept_endpoints = self._get_endpoints(concept_graph)
        image_endpoints = self._get_endpoints(image_graph)

        len_concept_endpoints = len(concept_endpoints)
        len_image_endpoints = len(image_endpoints)

        if len_concept_endpoints == len_image_endpoints:
            self.logger.info(
                "Concept and image have the same number of endpoints. No reduction needed."
            )
            return concept_graph, image_graph

        # Determine which graph has more endpoints
        if len_concept_endpoints > len_image_endpoints:
            graph_large = concept_graph
            graph_small = image_graph
            points_large = concept_endpoints
            points_small = image_endpoints
            graph_to_reduce = CONCEPT
        else:
            graph_large = image_graph
            graph_small = concept_graph
            points_large = image_endpoints
            points_small = concept_endpoints
            graph_to_reduce = IMAGE


        similarity_matrix = self.calculate_similarity_matrix(
            graph_large, graph_small, points_large, points_small
        )

        excess_endpoints_to_remove = self._identify_excess_endpoints_to_remove(
            similarity_matrix,
            points_large,
            abs(len_concept_endpoints - len_image_endpoints)
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
            image_graph = self._apply_reduction(
                image_graph, excess_endpoints_to_remove
            )
        return concept_graph, image_graph

    def _get_endpoints(self, graph: nx.Graph) -> List[Any]:
        return [
            node
            for node, data in graph.nodes(data=True)
            if GraphUtils.is_endpoint(data) or self._node_is_semantically_endpoint(node, graph)
        ]
    
    def _node_is_semantically_endpoint(self, node: Any, graph: nx.Graph) -> bool:
        data = graph.nodes[node]
        labels = data.get("labels", [])
        
        # A node is semantically an endpoint if it has only one connection
        # and is not a start point
        is_endpoint = graph.degree(node) == 1 and CriticalPointType.START_POINT.value not in labels
        
        # If it's an endpoint but not labeled as one, add the label
        if is_endpoint and not any(pt.value in labels for pt in [CriticalPointType.END_POINT, CriticalPointType.START_POINT]):
            self.logger.info(f"Node {node} is an endpoint but not labeled as one. Adding label {CriticalPointType.END_POINT.value}.")
            data["labels"].clear()
            data["labels"].append(CriticalPointType.END_POINT.value)
            data["labels"].append("Point")
            
        return is_endpoint
            
    def _find_endpoints_below_threshold(
        self, similarity_matrix: np.ndarray, endpoints: List[Any], axis: int
    ) -> List[Any]:
        enpoints_below_threshold = []
        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        max_similarity = np.max(similarity_matrix, axis=axis)

        for i, endpoint_id in enumerate(endpoints):
            if max_similarity[i] < self.similarity_threshold:
                self.logger.info(f"Endpoint {endpoint_id} has similarity {max_similarity[i]} below threshold {self.similarity_threshold}. Adding to list of endpoints to remove.")
                enpoints_below_threshold.append(endpoint_id)
        return enpoints_below_threshold

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

            is_critical = GraphUtils.is_critical_point(node_data)
            is_intersection = graph.degree(current_node) > 2 # This node can not have intersection point label

            if is_critical or is_intersection:
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

    def _identify_excess_endpoints_to_remove(
        self,
        similarity_matrix: np.ndarray,
        endpoints_large: List[Any],
        difference: int,
    ) -> List[Any]:
        if difference <= 0:
            self.logger.error("Difference is less than or equal to 0. Raising error.")
            raise ValueError("Difference is less than or equal to 0.")

        if similarity_matrix.size == 0:
            self.logger.error("Similarity matrix is empty. Raising error.")
            raise ValueError("Similarity matrix is empty.")

        # Find the maximum similarity for each endpoint in the larger set (each row in the matrix)
        max_similarities_per_large_endpoint = np.max(similarity_matrix, axis=1)

        # Create a list of (index_in_large_list, max_similarity)
        indexed_similarities = list(enumerate(max_similarities_per_large_endpoint))

        # Sort by max_similarity in ascending order (lowest similarity first)
        indexed_similarities.sort(key=lambda x: x[1])

        # Get the indices of the 'difference' endpoints with the lowest max similarity
        indices_to_remove = [idx for idx, sim in indexed_similarities[:difference]]

        # Get the actual node IDs corresponding to these indices
        nodes_to_remove = [endpoints_large[i] for i in indices_to_remove]

        self.logger.debug(f"Indices identified for removal based on lowest max similarity: {indices_to_remove}")
        self.logger.debug(f"Nodes identified for removal: {nodes_to_remove}")

        return nodes_to_remove
            
            