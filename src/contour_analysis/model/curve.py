from dataclasses import dataclass
from typing import List
from enum import Enum

from .point import Point
from .vector import Vector

class CurveType(Enum):
    CONVEX = "convex"
    CONCAVE = "concave"


@dataclass
class Curve:
    id: str
    vectors: List[Vector]
    type: CurveType
    start_point: Point
    end_point: Point

