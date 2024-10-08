from contour_analysis_repository import ContourAnalysisRepository
import uuid
from typing import Dict, Any, List
import networkx as nx
from model.vector_details import VectorDetails
from model.angle_point import AnglePoint
import math

class ContourAnalysisService:
    def __init__(self, repository: ContourAnalysisRepository):
        self.repository = repository

    def analyze_contour(self, graph: nx.Graph, session_id: str) -> Dict[str, Any]:
        transformed_data = self._transform_input(graph, session_id)
        return self.repository.analyze_contour(transformed_data)

    def _transform_input(self, graph: nx.Graph, session_id: str) -> Dict[str, Any]:
        angle_points = self._extract_angle_points(graph)
        lines = self._extract_lines(graph)

        return {
            "image_id": str(uuid.uuid4()),
            "angle_points": angle_points,
            "lines": lines,
            "parameters": {
                "session_id": session_id
            }
        }

    def _extract_angle_points(self, graph: nx.Graph) -> List[AnglePoint]:
        angle_points = []
        for node, degree in graph.degree():
            if degree == 2:
                neighbors = list(graph.neighbors(node))
                angle = self._calculate_angle_between_lines(graph, node, neighbors)
                angle_points.append(AnglePoint(
                    id=str(uuid.uuid4()),
                    x=node[1],  # Use node[1] for x-coordinate
                    y=node[0],  # Use node[0] for y-coordinate
                    angle=angle,
                    line1=graph[node][neighbors[0]]['id'],
                    line2=graph[node][neighbors[1]]['id']
                ))
        return angle_points

    def _extract_lines(self, graph: nx.Graph) -> List[VectorDetails]:
        return [
            VectorDetails(
                id=data['id'],
                x1=u[1],  # Use u[1] for x1-coordinate
                y1=u[0],  # Use u[0] for y1-coordinate
                x2=v[1],  # Use v[1] for x2-coordinate
                y2=v[0],  # Use v[0] for y2-coordinate
                length=self._calculate_length(u, v)
            )
            for u, v, data in graph.edges(data=True)
        ]

    def _calculate_length(self, u: Any, v: Any) -> float:
        return ((v[1] - u[1])**2 + (v[0] - u[0])**2)**0.5

    def _calculate_angle_between_lines(self, graph: nx.Graph, node: Any, neighbors: List[Any]) -> float:
        vector1 = (neighbors[0][1] - node[1], neighbors[0][0] - node[0])
        vector2 = (neighbors[1][1] - node[1], neighbors[1][0] - node[0])
        
        dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
        magnitudes = [((v[0]**2 + v[1]**2)**0.5) for v in [vector1, vector2]]
        cos_angle = dot_product / (magnitudes[0] * magnitudes[1])
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))
        return angle
