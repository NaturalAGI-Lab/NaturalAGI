from typing import Dict, List, Any

from model.angle_point import AnglePoint, EndPoint, Point


# noinspection PyTypeChecker
class AnglePointConverter:
    @staticmethod
    def dict_to_points(point_dict: Dict[str, Any]) -> List[Point]:
        points: List[Point] = []
        for point in point_dict:
            if point["type"] == "angle_point":
                points.append(AnglePoint(**point))
            elif point["type"] == "endpoint":
                points.append(EndPoint(**point))
        return points