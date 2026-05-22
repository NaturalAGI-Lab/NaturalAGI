from enum import Enum, auto


class ContourType(Enum):
    CLOSED = "Closed"
    OPEN = "Open"


class ContourDevelopment(Enum):
    MONOTONIC = "Monotonic"
    NON_MONOTONIC = "Non-monotonic"
    UNKNOWN = "Unknown"


class HorizontalDirection(Enum):
    LEFT = auto()
    RIGHT = auto()
    NONE = auto()


class VerticalDirection(Enum):
    TOP = auto()
    BOTTOM = auto()
    NONE = auto()
