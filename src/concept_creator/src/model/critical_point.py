from enum import Enum


class CriticalPointType(Enum):
    INTERSECTION_POINT = "IntersectionPoint"
    CORNER_POINT = "CornerPoint"
    END_POINT = "EndPoint"
    START_POINT = "StartPoint"
