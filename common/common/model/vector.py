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

    @classmethod
    def from_node_data(cls, node_data: dict) -> "Vector":
        return cls(
            id=node_data["id"],
            x1=node_data["x1"],
            y1=node_data["y1"],
            x2=node_data["x2"],
            y2=node_data["y2"],
            length=node_data["length"],
        )
