from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
import math
import networkx as nx
from neo4j import ManagedTransaction

from visitors.visitor import Visitor
from model.point import Point
from model.vector import Vector


class RelativeSegment(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER_VERTICAL = "center_vertical"
    CENTER_HORIZONTAL = "center_horizontal"


@dataclass
class RelativePosition:
    distance_from_center: float
    segments: List[RelativeSegment]
    normalized_x: float  # -1 to 1
    normalized_y: float  # -1 to 1


class RelativePositionVisitor(Visitor):
    def __init__(self, graph: nx.Graph, image_width: int, image_height: int):
        super().__init__(graph)
        self.image_width = image_width
        self.image_height = image_height
        self.center_x = image_width / 2
        self.center_y = image_height / 2
        self.max_distance = math.sqrt(self.center_x**2 + self.center_y**2)
        self.segment_threshold = 0.2  # 25% threshold for center segments
        self.point_positions: Dict[str, RelativePosition] = {}
        self.vector_positions: Dict[str, RelativePosition] = {}

    def visit_point(self, point: Point) -> Dict[str, Any]:
        position = self._calculate_relative_position(point.x, point.y)
        self.point_positions[point.id] = position

        return {
            "point_id": point.id,
            "distance": position.distance_from_center,
            "segments": [seg.value for seg in position.segments],
            "normalized_x": position.normalized_x,
            "normalized_y": position.normalized_y,
        }

    def visit_line(self, line: Vector) -> Dict[str, Any]:
        # Calculate midpoint of the line
        mid_x = (line.x1 + line.x2) / 2
        mid_y = (line.y1 + line.y2) / 2

        position = self._calculate_relative_position(mid_x, mid_y)
        self.vector_positions[line.id] = position

        return {
            "line_id": line.id,
            "distance": position.distance_from_center,
            "segments": [seg.value for seg in position.segments],
            "normalized_x": position.normalized_x,
            "normalized_y": position.normalized_y,
        }

    def _calculate_relative_position(self, x: float, y: float) -> RelativePosition:
        # Calculate normalized coordinates (-1 to 1)
        normalized_x = (x - self.center_x) / self.center_x
        normalized_y = (y - self.center_y) / self.center_y

        # Calculate distance from center
        dx = x - self.center_x
        dy = y - self.center_y
        distance = math.sqrt(dx**2 + dy**2) / self.max_distance

        # Determine segments
        segments = []

        # Vertical segments
        if abs(normalized_y) < self.segment_threshold:
            segments.append(RelativeSegment.CENTER_HORIZONTAL)
        elif normalized_y < 0:
            segments.append(RelativeSegment.TOP)
        else:
            segments.append(RelativeSegment.BOTTOM)

        # Horizontal segments
        if abs(normalized_x) < self.segment_threshold:
            segments.append(RelativeSegment.CENTER_VERTICAL)
        elif normalized_x < 0:
            segments.append(RelativeSegment.LEFT)
        else:
            segments.append(RelativeSegment.RIGHT)

        return RelativePosition(
            distance_from_center=round(distance, 1),
            segments=segments,
            normalized_x=round(normalized_x, 1),
            normalized_y=round(normalized_y, 1),
        )

    def save_result(
        self,
        tx: ManagedTransaction,
        image_id: str,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        if "point_id" in result:
            self._save_point_position(tx, result)
        elif "line_id" in result:
            self._save_line_position(tx, result)

    def _save_point_position(
        self,
        tx: ManagedTransaction,
        result: Dict[str, Any],
    ) -> None:
        query = """
        MATCH (p:Point {id: $point_id})
        SET p.relative_distance = $distance,
            p.normalized_x = $normalized_x,
            p.normalized_y = $normalized_y,
            p.segments = $segments
        RETURN p
        """
        tx.run(
            query,
            point_id=result["point_id"],
            distance=result["distance"],
            normalized_x=result["normalized_x"],
            normalized_y=result["normalized_y"],
            segments=result["segments"],
        )

    def _save_line_position(
        self,
        tx: ManagedTransaction,
        result: Dict[str, Any],
    ) -> None:
        query = """
        MATCH (v:Vector {id: $line_id})
        SET v.relative_distance = $distance,
            v.normalized_x = $normalized_x,
            v.normalized_y = $normalized_y,
            v.segments = $segments
        """
        tx.run(
            query,
            line_id=result["line_id"],
            distance=result["distance"],
            normalized_x=result["normalized_x"],
            normalized_y=result["normalized_y"],
            segments=result["segments"],
        )

    def get_results(self) -> Dict[str, Dict[str, RelativePosition]]:
        return {"points": self.point_positions, "vectors": self.vector_positions}

    def reset(self) -> None:
        self.point_positions.clear()
        self.vector_positions.clear()
