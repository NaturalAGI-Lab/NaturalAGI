from pydantic import BaseModel
from enum import Enum, auto


class HorizontalDirection(Enum):
    LEFT = auto()
    RIGHT = auto()
    NONE = auto()


class VerticalDirection(Enum):
    TOP = auto()
    BOTTOM = auto()
    NONE = auto()


class Vector(BaseModel):
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    length: float
    horizontal_direction: HorizontalDirection = HorizontalDirection.NONE
    vertical_direction: VerticalDirection = VerticalDirection.NONE
