from typing import Dict
from visitors.visitor import Visitor
from model.point import Point
from model.vector import Vector

class QuadrantVisitor(Visitor):
    def __init__(self):
        self.quadrants: Dict[str, int] = {}

    def visit_point(self, point: Point) -> None:
        # Implementation for point-related operations
        pass

    def visit_line(self, line: Vector) -> None:
        dx = line.x2 - line.x1
        dy = line.y2 - line.y1
        quadrant = self.determine_quadrant(dx, dy)
        self.quadrants[line.id] = quadrant

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