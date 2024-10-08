from typing import List, Any, Optional
import networkx as nx
import uuid
import math
from model.point import Point, CornerPoint, InflectionPoint, IntersectionPoint, EndPoint

class PointExtractor:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def extract_points(self) -> List[Point]:
        points: List[Point] = []
        points.extend(self._extract_corner_points())
        # points.extend(self._extract_inflection_points())
        points.extend(self._extract_intersection_points())
        points.extend(self._extract_end_points())
        return points

    def _extract_corner_points(self) -> List[CornerPoint]:
        corner_points = []
        for node, degree in self.graph.degree():
            if degree == 2:
                neighbors = list(self.graph.neighbors(node))
                angle = self._calculate_angle_between_lines(node, neighbors)
                if angle < 150:  # Threshold for corner detection
                    corner_points.append(CornerPoint(
                        id=str(uuid.uuid4()),
                        x=float(node[1]),
                        y=float(node[0]),
                        angle=angle,
                        line1=self.graph[node][neighbors[0]].get('id'),
                        line2=self.graph[node][neighbors[1]].get('id')
                    ))
        return corner_points

    def _extract_inflection_points(self) -> List[InflectionPoint]:
        # This is a simplified implementation and may need to be refined
        inflection_points = []
        for node in self.graph.nodes():
            if self.graph.degree(node) == 2:
                neighbors = list(self.graph.neighbors(node))
                curvature_before = self._calculate_curvature(neighbors[0], node, neighbors[1])
                curvature_after = self._calculate_curvature(node, neighbors[1], list(self.graph.neighbors(neighbors[1]))[0])
                if curvature_before * curvature_after < 0:
                    inflection_points.append(InflectionPoint(
                        id=str(uuid.uuid4()),
                        x=float(node[1]),
                        y=float(node[0]),
                        curvature_before=curvature_before,
                        curvature_after=curvature_after
                    ))
        return inflection_points

    def _extract_intersection_points(self) -> List[IntersectionPoint]:
        intersection_points = []
        edges = list(self.graph.edges())
        for i, (u1, v1) in enumerate(edges):
            for u2, v2 in edges[i+1:]:
                intersection = self._line_intersection((u1, v1), (u2, v2))
                if intersection:
                    intersection_points.append(IntersectionPoint(
                        id=str(uuid.uuid4()),
                        x=float(intersection[0]),
                        y=float(intersection[1]),
                        lines=[self.graph[u1][v1].get('id'), self.graph[u2][v2].get('id')]
                    ))
        return intersection_points

    def _extract_end_points(self) -> List[EndPoint]:
        end_points = []
        for node, degree in self.graph.degree():
            if degree == 1:
                neighbor = list(self.graph.neighbors(node))[0]
                end_points.append(EndPoint(
                    id=str(uuid.uuid4()),
                    x=float(node[1]),
                    y=float(node[0]),
                    line=self.graph[node][neighbor].get('id')
                ))
        return end_points

    def _calculate_angle_between_lines(self, node: Any, neighbors: List[Any]) -> float:
        vector1 = (neighbors[0][1] - node[1], neighbors[0][0] - node[0])
        vector2 = (neighbors[1][1] - node[1], neighbors[1][0] - node[0])
        
        dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
        magnitudes = [((v[0]**2 + v[1]**2)**0.5) for v in [vector1, vector2]]
        cos_angle = dot_product / (magnitudes[0] * magnitudes[1])
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))
        return angle

    def _calculate_distance(self, point1: Any, point2: Any) -> float:
        return ((point2[1] - point1[1])**2 + (point2[0] - point1[0])**2)**0.5

    def _calculate_curvature(self, p1: Any, p2: Any, p3: Any) -> float:
        # This is a simplified curvature calculation and may need to be refined
        dx1, dy1 = p2[1] - p1[1], p2[0] - p1[0]
        dx2, dy2 = p3[1] - p2[1], p3[0] - p2[0]
        return (dx2 * dy1 - dx1 * dy2) / ((dx1**2 + dy1**2)**1.5)

    def _line_intersection(self, line1: tuple, line2: tuple) -> Optional[tuple]:
        x1, y1 = line1[0][1], line1[0][0]
        x2, y2 = line1[1][1], line1[1][0]
        x3, y3 = line2[0][1], line2[0][0]
        x4, y4 = line2[1][1], line2[1][0]

        denom = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
        if denom == 0:  # lines are parallel
            return None

        ua = ((x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)) / denom
        if ua < 0 or ua > 1:  # out of range
            return None

        ub = ((x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)) / denom
        if ub < 0 or ub > 1:  # out of range
            return None

        x = x1 + ua * (x2-x1)
        y = y1 + ua * (y2-y1)
        return (x, y)
