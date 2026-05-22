from typing import Any, Dict

import networkx as nx
from neo4j import ManagedTransaction
from .visitor import Visitor
from ...model.point import Point
from ...model.vector import Vector


class QuadrantVisitor(Visitor):
    def __init__(self, graph: nx.Graph):
        super().__init__(graph)
        self.quadrants: Dict[str, int] = {}

    def visit_point(self, point: Point) -> None:
        x = point.normalized_x
        y = point.normalized_y
        quadrant = self.determine_quadrant(x, y)
        self.graph.nodes[point.id]["quadrant"] = quadrant

    def determine_vector_type(self, dx: float, dy: float) -> str:
        """Determine vector type based on relative dimensions.

        Args:
            dx (float): Change in x coordinate
            dy (float): Change in y coordinate

        Returns:
            str: Vector type label ("HorizontalVector", "VerticalVector", or "DiagonalVector")
        """
        # Swap x and y
        abs_dx = abs(dx)
        abs_dy = abs(dy)

        if abs_dx == abs_dy:
            return "DiagonalVector"
        elif abs_dx > abs_dy:
            return "HorizontalVector"
        else:
            return "VerticalVector"

    def visit_line(self, line: Vector, start_point: Point) -> Dict[str, Any]:
        start_coords = (start_point.x, start_point.y)
        end_coords = (
            (line.x2, line.y2)
            if line.x1 == start_point.x and line.y1 == start_point.y
            else (line.x1, line.y1)
        )
        dx = end_coords[0] - start_coords[0]
        dy = end_coords[1] - start_coords[1]
        quadrant = self.determine_quadrant(dx, dy)
        vector_type = self.determine_vector_type(dx, dy)

        self.quadrants[line.id] = quadrant
        self.graph.nodes[line.id]["quadrant"] = quadrant
        self.graph.nodes[line.id]["vector_type"] = vector_type
        self.graph.nodes[line.id]["labels"].append(vector_type)
        self.graph.nodes[line.id]["dx"] = dx
        self.graph.nodes[line.id]["dy"] = dy
        self._compute_vector_midpoint(line.id)
        return {
            "quadrant": quadrant,
            "line_id": line.id,
            "vector_type": vector_type,
            "dx": dx,
            "dy": dy,
        }

    def _compute_vector_midpoint(self, line_id: str) -> None:
        point_neighbors = [
            n for n in self.graph.neighbors(line_id)
            if "Point" in self.graph.nodes[n].get("labels", [])
        ]
        if len(point_neighbors) != 2:
            return
        d1 = self.graph.nodes[point_neighbors[0]]
        d2 = self.graph.nodes[point_neighbors[1]]
        nx1, ny1 = d1.get("normalized_x"), d1.get("normalized_y")
        nx2, ny2 = d2.get("normalized_x"), d2.get("normalized_y")
        if all(v is not None for v in (nx1, ny1, nx2, ny2)):
            self.graph.nodes[line_id]["normalized_x"] = round((nx1 + nx2) / 2.0, 1)
            self.graph.nodes[line_id]["normalized_y"] = round((ny1 + ny2) / 2.0, 1)

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        query = f"""
        MATCH (v:Vector {{id: $id}})
        SET v:{result['vector_type']}, v.quadrant = $quadrant
        """
        tx.run(query, id=result["line_id"], quadrant=result["quadrant"])

    @staticmethod
    def determine_quadrant(dx: float, dy: float) -> int:
        if dx > 0 and dy > 0:
            return 1
        elif dx < 0 < dy:
            return 2
        elif dx < 0 and dy < 0:
            return 3
        elif dx > 0 > dy:
            return 4
        else:
            return -1  # Axis-aligned
