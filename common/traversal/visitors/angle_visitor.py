from typing import Any, Dict, List, Tuple
import math

from neo4j import ManagedTransaction
from .visitor import Visitor
from ...model.point import Point
from ...model.vector import Vector
import networkx as nx


class AngleVisitor(Visitor):
    def __init__(self, graph: nx.Graph):
        super().__init__(graph)
        self.point_angles: Dict[str, set[float]] = {}
        self.line_angles: Dict[str, float] = {}

    def visit_point(self, point: Point) -> Dict[str, Any]:
        connected_lines = self._get_connected_lines(point)
        if len(connected_lines) >= 2:
            angles = []
            for i in range(len(connected_lines)):
                for j in range(i + 1, len(connected_lines)):
                    angles = self._calculate_angle_between_lines(
                        connected_lines[i], connected_lines[j]
                    )
                    angles.extend(angles)
            self.point_angles[point.id] = angles
            self.graph.nodes[point.id]["angles"] = angles
            return {"angles": angles, "point_id": point.id}
        return None

    def visit_line(self, line: Vector) -> Dict[str, Any]:
        angle_with_ox = self._calculate_angle_with_ox(line)
        self.line_angles[line.id] = angle_with_ox
        self.graph.nodes[line.id]["angle_with_ox"] = angle_with_ox
        return {"angle_with_ox": angle_with_ox, "line_id": line.id}

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        if result is None:
            return

        if "angles" in result:
            self._save_point_angles(tx, image_id, session_id, result)
        elif "angle_with_ox" in result:
            self._save_line_angle(tx, image_id, session_id, result)

    def _save_point_angles(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        query = """
            MATCH (p:Point {id: $point_id})
            UNWIND $angles as angle
            MERGE (a:PointAngle:Feature {value: angle, session_id: $session_id})
            ON CREATE SET a.samples = [$image_id], p.angle = angle
            ON MATCH SET a.samples = CASE
                WHEN NOT $image_id IN a.samples THEN a.samples + $image_id
                ELSE a.samples
            END, p.angle = angle
            MERGE (p)-[:HAS_ANGLE]->(a)
        """
        tx.run(
            query,
            point_id=result["point_id"],
            angles=result["angles"],
            session_id=session_id,
            image_id=image_id,
        )

    def _save_line_angle(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        query = """
        MATCH (l:Vector {id: $line_id})
        MERGE (a:LineAngle:Feature {line_id: $line_id, session_id: $session_id})
        ON CREATE SET a.angle_with_ox = $angle_with_ox, a.samples = [$image_id], l.angle_with_ox = $angle_with_ox
        ON MATCH SET a.angle_with_ox = $angle_with_ox, 
                     a.samples = CASE
                         WHEN NOT $image_id IN a.samples THEN a.samples + $image_id
                         ELSE a.samples
                     END, l.angle_with_ox = $angle_with_ox
        MERGE (l)-[:HAS_ANGLE]->(a)
        """
        tx.run(
            query,
            line_id=result["line_id"],
            angle_with_ox=result["angle_with_ox"],
            session_id=session_id,
            image_id=image_id,
        )

    def get_results(self) -> Dict[str, Any]:
        return {"point_angles": self.point_angles, "line_angles": self.line_angles}

    def reset(self) -> None:
        self.point_angles.clear()
        self.line_angles.clear()

    def _get_connected_lines(self, point: Point) -> List[Vector]:
        connected_lines = []
        node = [
            node
            for node, data in self.graph.nodes(data=True)
            if data["uuid"] == point.id
        ][0]
        for neighbor in self.graph.neighbors(node):
            edge_data = self.graph.get_edge_data(node, neighbor)
            connected_lines.append(
                Vector(
                    id=edge_data["uuid"],
                    x1=edge_data["x1"],
                    y1=edge_data["y1"],
                    x2=edge_data["x2"],
                    y2=edge_data["y2"],
                    length=edge_data["length"],
                )
            )
        return connected_lines

    def _calculate_angle_between_lines(
        self, line1: Vector, line2: Vector
    ) -> Tuple[float, float]:
        # Find the common point (intersection point)
        if (line1.x1, line1.y1) == (line2.x1, line2.y1):
            vector1 = (line1.x2 - line1.x1, line1.y2 - line1.y1)
            vector2 = (line2.x2 - line2.x1, line2.y2 - line2.y1)
        elif (line1.x1, line1.y1) == (line2.x2, line2.y2):
            vector1 = (line1.x2 - line1.x1, line1.y2 - line1.y1)
            vector2 = (line2.x1 - line2.x2, line2.y1 - line2.y2)
        elif (line1.x2, line1.y2) == (line2.x1, line2.y1):
            vector1 = (line1.x1 - line1.x2, line1.y1 - line1.y2)
            vector2 = (line2.x2 - line2.x1, line2.y2 - line2.y1)
        elif (line1.x2, line1.y2) == (line2.x2, line2.y2):
            vector1 = (line1.x1 - line1.x2, line1.y1 - line1.y2)
            vector2 = (line2.x1 - line2.x2, line2.y1 - line2.y2)
        else:
            raise ValueError("Lines do not intersect")

        dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
        magnitude1 = math.sqrt(vector1[0] ** 2 + vector1[1] ** 2)
        magnitude2 = math.sqrt(vector2[0] ** 2 + vector2[1] ** 2)

        cos_angle = dot_product / (magnitude1 * magnitude2)
        angle1 = math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))
        angle2 = 360 - angle1

        angle1 = round(angle1 / 10) * 10
        angle2 = round(angle2 / 10) * 10
        return [angle1, angle2]

    def _calculate_angle_with_ox(self, line: Vector) -> float:
        vector = (line.x2 - line.x1, line.y2 - line.y1)
        dot_product = vector[0] * 1 + vector[1] * 0
        magnitude = math.sqrt(vector[0] ** 2 + vector[1] ** 2)
        cos_angle = dot_product / magnitude
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))
        return round(angle / 10) * 10
