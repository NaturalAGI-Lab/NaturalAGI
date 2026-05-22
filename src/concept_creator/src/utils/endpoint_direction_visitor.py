import logging
from typing import Any
import numpy as np
import networkx as nx
from common.graph_utils import GraphUtils


class EndpointDirectionVisitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def visit(self, graph: nx.Graph) -> None:
        endpoints = self._get_endpoints(graph)
        
        for endpoint_id in endpoints:
            try:
                direction_x, direction_y = self._calculate_direction(graph, endpoint_id)
                graph.nodes[endpoint_id]['direction_x'] = direction_x
                graph.nodes[endpoint_id]['direction_y'] = direction_y

                density = self._calculate_branch_corner_density(graph, endpoint_id)
                graph.nodes[endpoint_id]['branch_corner_density'] = density

                self.logger.debug(
                    f"Endpoint {endpoint_id}: direction=({direction_x:.4f}, {direction_y:.4f}), density={density:.4f}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to calculate direction for endpoint {endpoint_id}: {e}"
                )
                graph.nodes[endpoint_id]['direction_x'] = 0.0
                graph.nodes[endpoint_id]['direction_y'] = 0.0
                graph.nodes[endpoint_id]['branch_corner_density'] = 0.0
    
    def _get_endpoints(self, graph: nx.Graph) -> list:
        endpoints = []
        for node, data in graph.nodes(data=True):
            if GraphUtils.is_endpoint(data):
                endpoints.append(node)
        return endpoints
    
    def _calculate_direction(self, graph: nx.Graph, endpoint_id: Any) -> tuple[float, float]:
        endpoint_data = graph.nodes[endpoint_id]
        endpoint_x = self._extract_coord(endpoint_data.get('normalized_x'))
        endpoint_y = self._extract_coord(endpoint_data.get('normalized_y'))
        
        next_point_id = self._find_next_point(graph, endpoint_id)
        
        if next_point_id is None:
            raise ValueError(f"Could not find next point for endpoint {endpoint_id}")
        
        next_point_data = graph.nodes[next_point_id]
        next_point_x = self._extract_coord(next_point_data.get('normalized_x'))
        next_point_y = self._extract_coord(next_point_data.get('normalized_y'))
        
        dx = next_point_x - endpoint_x
        dy = next_point_y - endpoint_y
        
        magnitude = np.sqrt(dx**2 + dy**2)
        
        if magnitude < 1e-10:
            self.logger.warning(
                f"Zero-length direction vector for endpoint {endpoint_id}, using (0, 0)"
            )
            return 0.0, 0.0
        
        direction_x = dx / magnitude
        direction_y = dy / magnitude
        
        return direction_x, direction_y
    
    def _find_next_point(self, graph: nx.Graph, endpoint_id: Any) -> Any:
        immediate_neighbors = list(graph.neighbors(endpoint_id))
        
        if len(immediate_neighbors) != 1:
            raise ValueError(
                f"Endpoint {endpoint_id} has {len(immediate_neighbors)} neighbors, expected 1"
            )
        
        line_or_vector_id = immediate_neighbors[0]
        second_level_neighbors = list(graph.neighbors(line_or_vector_id))
        
        for neighbor_id in second_level_neighbors:
            if neighbor_id != endpoint_id:
                neighbor_data = graph.nodes[neighbor_id]
                labels = neighbor_data.get('labels', [])
                if 'Point' in labels:
                    return neighbor_id
        
        return None
    
    def _calculate_branch_corner_density(self, graph: nx.Graph, endpoint_id: Any) -> float:
        corner_count = 0
        point_hops = 0
        current = endpoint_id
        visited = {endpoint_id}

        while True:
            neighbors = [n for n in graph.neighbors(current) if n not in visited]
            if not neighbors:
                break

            for vector_node in neighbors:
                visited.add(vector_node)
                next_points = [n for n in graph.neighbors(vector_node) if n not in visited]

                if not next_points:
                    continue

                next_point = next_points[0]
                visited.add(next_point)
                point_hops += 1

                next_data = graph.nodes[next_point]

                if GraphUtils.is_corner_point(next_data):
                    corner_count += 1

                is_intersection = (
                    GraphUtils.is_intersection_point(next_data)
                    or graph.degree(next_point) > 2
                )
                is_terminal = (
                    GraphUtils.is_endpoint(next_data)
                    or "StartPoint" in next_data.get("labels", [])
                )

                if is_intersection or is_terminal:
                    if point_hops == 0:
                        return 0.0
                    return corner_count / point_hops

                current = next_point
                break

        if point_hops == 0:
            return 0.0
        return corner_count / point_hops

    def _extract_coord(self, coord_value: Any) -> float:
        if coord_value is None:
            raise ValueError("Coordinate value is None")
        
        if isinstance(coord_value, dict) and "center" in coord_value:
            return float(coord_value["center"])
        
        if isinstance(coord_value, (int, float)):
            return float(coord_value)
        
        raise ValueError(f"Unexpected coordinate format: {coord_value}")
