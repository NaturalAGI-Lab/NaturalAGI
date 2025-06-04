from dataclasses import dataclass
from typing import List


@dataclass
class Point:
    x: float
    y: float
    id: str
    nx_id: str

    def __hash__(self):
        return hash(self.id)


@dataclass
class CornerPoint(Point):
    angle: float
    line1: str
    line2: str


@dataclass
class IntersectionPoint(Point):
    lines: List[str]


@dataclass
class EndPoint(Point):
    line: str


@dataclass
class StartPoint(Point):
    line: str
