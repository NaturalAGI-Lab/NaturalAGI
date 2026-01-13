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
                
                self.logger.debug(
                    f"Endpoint {endpoint_id}: direction=({direction_x:.4f}, {direction_y:.4f})"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to calculate direction for endpoint {endpoint_id}: {e}"
                )
                graph.nodes[endpoint_id]['direction_x'] = 0.0
                graph.nodes[endpoint_id]['direction_y'] = 0.0
    
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
    
    def _extract_coord(self, coord_value: Any) -> float:
        if coord_value is None:
            raise ValueError("Coordinate value is None")
        
        if isinstance(coord_value, dict) and "center" in coord_value:
            return float(coord_value["center"])
        
        if isinstance(coord_value, (int, float)):
            return float(coord_value)
        
        raise ValueError(f"Unexpected coordinate format: {coord_value}")
