from enum import Enum


class HalfPlane(Enum):
    UPPER = "upper"
    LOWER = "lower"
    RIGHT = "right"
    LEFT = "left"
    ORIGIN = "origin"