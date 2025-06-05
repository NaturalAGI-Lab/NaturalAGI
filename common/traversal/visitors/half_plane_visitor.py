from typing import Any, Dict

from neo4j import ManagedTransaction
from ...model.half_plane import HalfPlane
from .visitor import Visitor
from ...model.point import Point
from ...model.vector import Vector


class HalfPlaneVisitor(Visitor):
    def __init__(self, graph):
        super().__init__(graph)
        self.half_planes: Dict[str, HalfPlane] = {}

    def visit_point(self, _: Point) -> None:
        # This visitor does not handle points
        return None

    def visit_line(self, line: Vector) -> Dict[str, Any]:
        dx = line.x2 - line.x1
        dy = line.y2 - line.y1
        half_plane = self.determine_half_plane(dx, dy)
        self.half_planes[line.id] = half_plane
        self.graph.nodes[line.id]["half_plane"] = half_plane.value

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        query = """
        MATCH (v:Vector {id: $id})
        MERGE (hp:HalfPlane:Feature {value: $half_plane, session_id: $session_id})
        ON CREATE SET hp.samples = [$image_id], v.half_plane = $half_plane
        ON MATCH SET hp.samples = CASE
            WHEN NOT $image_id IN hp.samples THEN hp.samples + $image_id
            ELSE hp.samples
        END, v.half_plane = $half_plane
        MERGE (v)-[:IS_IN_HALF_PLANE]->(hp)
        """
        tx.run(
            query,
            id=result["line_id"],
            half_plane=result["half_plane"],
            session_id=session_id,
            image_id=image_id,
        )

    def get_results(self) -> Dict[str, str]:
        return {k: v.value for k, v in self.half_planes.items()}

    def reset(self) -> None:
        self.half_planes.clear()

    @staticmethod
    def determine_half_plane(dx: float, dy: float) -> HalfPlane:
        if dx == 0 and dy == 0:
            return HalfPlane.ORIGIN
        elif abs(dy) > abs(dx):
            return HalfPlane.UPPER if dy > 0 else HalfPlane.LOWER
        else:
            return HalfPlane.RIGHT if dx > 0 else HalfPlane.LEFT
