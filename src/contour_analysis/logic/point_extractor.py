from typing import Dict, List, Any, Optional
import networkx as nx
import uuid
import math
from model.point import (
    Point,
    CornerPoint,
    IntersectionPoint,
    EndPoint,
    StartPoint,
)


class PointExtractor:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def extract_points(self) -> List[Point]:
        points: List[Point] = []
        points.extend(self._extract_corner_points())
        # points.extend(self._extract_inflection_points())
        points.extend(self._extract_intersection_points())
        points.extend(self._extract_end_points())
        start_point = self._extract_start_point()
        if start_point:
            points.append(start_point)
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
                            id=node_data["uuid"],
                            x=float(node_data["x"]),
                            y=float(node_data["y"]),
                            angle=angle,
                            line1=self.graph[node][neighbors[0]].get("uuid"),
                            line2=self.graph[node][neighbors[1]].get("uuid"),
                            nx_id=node,
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
            lines = []
            for neighbor in self.graph.neighbors(node):
                edge_data = self.graph.get_edge_data(node, neighbor)
                lines.append(edge_data["uuid"])

            if len(lines) >= 2:
                intersection_point = IntersectionPoint(
                    id=node_data["uuid"],
                    x=float(node_data["x"]),
                    y=float(node_data["y"]),
                    lines=lines,
                    nx_id=node,
                )
                intersection_points.append(intersection_point)

        return intersection_points

    def _extract_end_points(self) -> List[EndPoint]:
        end_points = []
        for node, node_data in self.graph.nodes(data=True):
            if self.graph.degree(node) == 1:
                neighbor = list(self.graph.neighbors(node))[0]
                end_points.append(
                    EndPoint(
                        id=node_data.get("uuid", str(uuid.uuid4())),
                        x=float(node_data["x"]),
                        y=float(node_data["y"]),
                        line=self.graph[node][neighbor].get("uuid"),
                        nx_id=node,
                    )
                )
        return end_points

    def _extract_start_point(self) -> Optional[StartPoint]:
        if not self.graph.nodes:
            return None

        # Priority 1: Look for endpoints (nodes with degree 1)
        end_point_nodes = [
            node for node in self.graph.nodes() if self.graph.degree(node) == 1
        ]

        # If there are endpoints, select the top-leftmost endpoint
        if end_point_nodes:
            # Find the top-leftmost endpoint
            top_leftmost_node = min(
                end_point_nodes,
                key=lambda n: (
                    float(self.graph.nodes[n]["y"]) + float(self.graph.nodes[n]["x"]),
                ),
            )
        else:
            # Priority 2: If no endpoints, find the top-leftmost point out of any points
            top_leftmost_node = min(
                self.graph.nodes(),
                key=lambda n: (
                    float(self.graph.nodes[n]["y"]) + float(self.graph.nodes[n]["x"]),
                ),
            )

        node_data = self.graph.nodes[top_leftmost_node]

        # Get the line connected to this point
        line = None
        if self.graph.degree(top_leftmost_node) > 0:
            neighbor = list(self.graph.neighbors(top_leftmost_node))[0]
            line = self.graph[top_leftmost_node][neighbor].get("uuid")

        return StartPoint(
            id=node_data.get("uuid", str(uuid.uuid4())),
            x=float(node_data["x"]),
            y=float(node_data["y"]),
            line=line,
            nx_id=top_leftmost_node,
        )

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
