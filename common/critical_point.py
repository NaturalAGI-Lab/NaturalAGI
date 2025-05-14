from enum import Enum
import numpy as np
from typing import Any


class CriticalPointType(Enum):
    INTERSECTION_POINT = "IntersectionPoint"
    CORNER_POINT = "CornerPoint"
    END_POINT = "EndPoint"
    START_POINT = "StartPoint"


class CriticalPoint:
    def __init__(self, graph_id: str, node_id: Any, label: str, norm_x: float, norm_y: float):
        self.graph_id = graph_id
        self.node_id = node_id
        self.label: str = label
        self.norm_x: float = norm_x
        self.norm_y: float = norm_y
        self.coordinates = np.array([norm_x, norm_y])
