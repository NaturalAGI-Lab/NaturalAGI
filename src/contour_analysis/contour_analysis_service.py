from contour_analysis_repository import ContourAnalysisRepository
import uuid
from typing import Dict, Any, List
import networkx as nx
from model.vector_details import VectorDetails
from logic.point_extractor import PointExtractor

class ContourAnalysisService:
    def __init__(self, repository: ContourAnalysisRepository):
        self.repository = repository

    def analyze_contour(self, graph: nx.Graph, session_id: str) -> Dict[str, Any]:
        transformed_data = self._transform_input(graph, session_id)
        return self.repository.analyze_contour(transformed_data)

    def _transform_input(self, graph: nx.Graph, session_id: str) -> Dict[str, Any]:
        point_extractor = PointExtractor(graph)
        points = point_extractor.extract_points()
        lines = self._extract_lines(graph)

        return {
            "image_id": str(uuid.uuid4()),
            "points": points,
            "lines": lines,
            "parameters": {
                "session_id": session_id
            }
        }

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
