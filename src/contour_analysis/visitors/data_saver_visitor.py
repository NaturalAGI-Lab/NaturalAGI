from visitors.visitor import Visitor
from model.point import Point
from model.vector import Vector

class DataSaverVisitor(Visitor):
    def __init__(self):
        self.data = []

    def visit_point(self, point: Point) -> None:
        self.data.append(point)

    def visit_line(self, line: Vector) -> None:
        self.data.append(line)