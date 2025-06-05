from dataclasses import dataclass


@dataclass
class Point:
    id: str
    x: float
    y: float

    @classmethod
    def from_node_data(cls, node_data: dict) -> "Point":
        return cls(
            x=node_data["x"],
            y=node_data["y"],
            id=node_data["id"],
        )

    def __hash__(self):
        return hash(self.id)


@dataclass
class CornerPoint(Point):
    angle: float


@dataclass
class IntersectionPoint(Point):
    pass


@dataclass
class EndPoint(Point):
    pass


@dataclass
class StartPoint(Point):
    pass
