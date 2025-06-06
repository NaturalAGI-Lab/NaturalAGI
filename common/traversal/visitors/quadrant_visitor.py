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
        return {
            "quadrant": quadrant,
            "line_id": line.id,
            "vector_type": vector_type,
            "dx": dx,
            "dy": dy,
        }

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        # First query to set the vector type label
        set_type_query = f"""
        MATCH (v:Vector {{id: $id}})
        SET v:{result['vector_type']}
        """

        # Second query to handle quadrant relationship
        quadrant_query = """
        MATCH (v:Vector {id: $id})
        MERGE (q:Quadrant:Feature {value: $quadrant, session_id: $session_id})
        ON CREATE SET q.samples = [$image_id], v.quadrant = $quadrant
        ON MATCH SET q.samples = CASE
            WHEN NOT $image_id IN q.samples THEN q.samples + $image_id
            ELSE q.samples
        END, v.quadrant = $quadrant
        MERGE (v)-[:IS_IN_QUADRANT]->(q)
        """

        # Execute both queries
        tx.run(set_type_query, id=result["line_id"])
        tx.run(
            quadrant_query,
            id=result["line_id"],
            quadrant=result["quadrant"],
            session_id=session_id,
            image_id=image_id,
        )

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
