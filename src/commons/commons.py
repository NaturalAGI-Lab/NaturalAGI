from enum import Enum


class Commons:
    class HalfPlane(Enum):
        UPPER = "Upper"
        LOWER = "Lower"
        RIGHT = "Right"
        LEFT = "Left"

    class Structures(Enum):
        ANGLE_POINT = "AnglePoint"
        VECTOR = "Vector"
        LINE = "Line"
