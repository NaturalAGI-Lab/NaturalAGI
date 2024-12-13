from dataclasses import dataclass
from typing import List


@dataclass
class Point:
    x: float
    y: float
    id: str
    nx_id: str  # id used in networkx

    def __hash__(self):
        return hash(self.uuid)


@dataclass
class CornerPoint(Point):
    """
    A corner point represents a sharp change in direction of a contour.
    It's characterized by a significant angle between two adjacent line segments.
    """

    angle: float
    line1: str
    line2: str


@dataclass
class InflectionPoint(Point):
    """
    #TODO not used for now. Implement support for it later

    An inflection point is where the curvature of a contour changes sign,
    i.e., where it transitions from being concave to convex or vice versa.
    """

    curvature_before: float
    curvature_after: float


@dataclass
class IntersectionPoint(Point):
    """
    An intersection point is where two or more line segments of the contour
    cross each other. This could indicate complex structures or overlapping parts.
    """

    lines: List[str]  # IDs of the intersecting lines


@dataclass
class EndPoint(Point):
    """
    An end point is the termination of a line segment that is not connected
    to any other point in the contour. It could indicate the start or end
    of an open contour.
    """

    line: str
