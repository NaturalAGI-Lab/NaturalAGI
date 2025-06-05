from typing import Dict, List, Any, Optional
import networkx as nx
import math
from common.model import (
    Point,
    CornerPoint,
    IntersectionPoint,
    EndPoint,
)


class PointExtractor:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def extract_points(self) -> List[Point]:
        points: List[Point] = []
        points.extend(self._extract_corner_points())
        points.extend(self._extract_intersection_points())
        points.extend(self._extract_end_points())
        return points

    def _extract_corner_points(self) -> List[CornerPoint]:
        # Step 1: Calculate angles for all degree-2 nodes
        MIN_CORNER_ANGLE = 160  # Maximum angle to be considered a corner (more than this is too straight)
        corner_points = []

        for node, node_data in self.graph.nodes(data=True):
            if self.graph.degree(node) == 2:
                neighbors = list(self.graph.neighbors(node))
                angle = self._calculate_angle_between_lines(
                    node_data, [self.graph.nodes[n] for n in neighbors]
                )

                # Step 2: Check if the angle is below the threshold
                if angle < MIN_CORNER_ANGLE:
                    corner_points.append(
                        CornerPoint(
                            id=node,
                            x=float(node_data["x"]),
                            y=float(node_data["y"]),
                            angle=angle,
                        )
                    )

        return corner_points

    def _extract_intersection_points(self) -> List[IntersectionPoint]:
        intersection_points = []
        nodes_with_degree_gt_2 = [
            node for node in self.graph.nodes() if self.graph.degree(node) > 2
        ]

        for node in nodes_with_degree_gt_2:
            node_data = self.graph.nodes[node]
            intersection_point = IntersectionPoint(
                id=node,
                x=float(node_data["x"]),
                y=float(node_data["y"]),
            )
            intersection_points.append(intersection_point)

        return intersection_points

    def _extract_end_points(self) -> List[EndPoint]:
        end_points = []
        for node, node_data in self.graph.nodes(data=True):
            if self.graph.degree(node) == 1:
                end_points.append(
                    EndPoint(
                        id=node,
                        x=float(node_data["x"]),
                        y=float(node_data["y"]),
                    )
                )
        return end_points

    def _calculate_angle_between_lines(
        self, node: Dict[str, Any], neighbors: List[Dict[str, Any]]
    ) -> float:
        vector1 = (neighbors[0]["x"] - node["x"], neighbors[0]["y"] - node["y"])
        vector2 = (neighbors[1]["x"] - node["x"], neighbors[1]["y"] - node["y"])

        dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
        magnitudes = [math.sqrt(v[0] ** 2 + v[1] ** 2) for v in [vector1, vector2]]
        cos_angle = dot_product / (magnitudes[0] * magnitudes[1])
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))
        return angle

    def _calculate_distance(self, point1: Any, point2: Any) -> float:
        return ((point2[1] - point1[1]) ** 2 + (point2[0] - point1[0]) ** 2) ** 0.5

    def _calculate_curvature(self, p1: Any, p2: Any, p3: Any) -> float:
        # This is a simplified curvature calculation and may need to be refined
        dx1, dy1 = p2[1] - p1[1], p2[0] - p1[0]
        dx2, dy2 = p3[1] - p2[1], p3[0] - p2[0]
        return (dx2 * dy1 - dx1 * dy2) / ((dx1**2 + dy1**2) ** 1.5)

    def _line_intersection(self, line1: tuple, line2: tuple) -> Optional[tuple]:
        def get_coordinates(point):
            if isinstance(point, (tuple, list)) and len(point) == 2:
                return point[0], point[1]
            elif isinstance(point, dict) and "x" in point and "y" in point:
                return point["x"], point["y"]
            else:
                raise ValueError(f"Unexpected point format: {point}")

        x1, y1 = get_coordinates(line1[0])
        x2, y2 = get_coordinates(line1[1])
        x3, y3 = get_coordinates(line2[0])
        x4, y4 = get_coordinates(line2[1])

        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:  # lines are parallel
            return None

        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        if ua < 0 or ua > 1:  # out of range
            return None

        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        if ub < 0 or ub > 1:  # out of range
            return None

        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)
