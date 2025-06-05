from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List
import math
import networkx as nx
from neo4j import ManagedTransaction

from .visitor import Visitor
from ...model.point import Point
from ...model.vector import Vector


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
    def __init__(self, graph: nx.Graph):
        super().__init__(graph)

        # Find the bounding box and calculate center
        self._calculate_bounding_box_center()

        self.segment_threshold = 0.05  # 20% threshold for center segments
        self.point_positions: Dict[str, RelativePosition] = {}
        self.vector_positions: Dict[str, RelativePosition] = {}

    def _calculate_bounding_box_center(self) -> None:
        """Calculate the center based on the bounding box of all points in the graph."""
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        # Find min and max coordinates to determine the bounding box
        for node_id, node_data in self.graph.nodes(data=True):
            if "Point" not in node_data["labels"]:
                continue

            x = node_data["x"]
            y = node_data["y"]
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

        # Calculate center of the bounding box
        self.center_x = (min_x + max_x) / 2
        self.center_y = (min_y + max_y) / 2

        # Calculate half-width and half-height of the bounding box
        half_width = (max_x - min_x) / 2
        half_height = (max_y - min_y) / 2

        # Maximum distance is from center to the corner of the bounding box
        self.max_distance = math.sqrt(half_width**2 + half_height**2)

    def visit_point(self, point: Point) -> Dict[str, Any]:
        position = self._calculate_relative_position(point.x, point.y)
        self.point_positions[point.id] = position
        node = self.graph.nodes[point.id]
        node["relative_distance"] = position.distance_from_center
        node["normalized_x"] = position.normalized_x
        node["normalized_y"] = position.normalized_y
        node["segments"] = [seg.value for seg in position.segments]

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
        node = self.graph.nodes[line.id]
        node["relative_distance"] = position.distance_from_center
        node["normalized_x"] = position.normalized_x
        node["normalized_y"] = position.normalized_y
        node["segments"] = [seg.value for seg in position.segments]

        return {
            "line_id": line.id,
            "distance": position.distance_from_center,
            "segments": [seg.value for seg in position.segments],
            "normalized_x": position.normalized_x,
            "normalized_y": position.normalized_y,
        }

    def _calculate_relative_position(self, x: float, y: float) -> RelativePosition:
        # Calculate normalized coordinates (-1 to 1) relative to bounding box center
        normalized_x = (x - self.center_x) / (
            self.max_distance if self.max_distance > 0 else 1
        )
        normalized_y = (y - self.center_y) / (
            self.max_distance if self.max_distance > 0 else 1
        )

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
            distance_from_center=round(distance, 2),
            segments=segments,
            normalized_x=round(normalized_x, 2),
            normalized_y=round(normalized_y, 2),
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
