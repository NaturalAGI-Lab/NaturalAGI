from dataclasses import dataclass
from .enums import HorizontalDirection, VerticalDirection


@dataclass
class Vector:
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    length: float
    horizontal_direction: HorizontalDirection = HorizontalDirection.NONE
    vertical_direction: VerticalDirection = VerticalDirection.NONE
