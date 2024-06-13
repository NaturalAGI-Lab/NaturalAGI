from typing import Dict, List, Any

from model.angle_point import AnglePoint


# noinspection PyTypeChecker
class AnglePointConverter:
    @staticmethod
    def dict_to_angle_point(angle_point_dict: Dict[str, Any]) -> AnglePoint:
        angle_points: List[AnglePoint] = []
        for angle_point in angle_point_dict:
            angle_points.append(
                AnglePoint(
                    id=angle_point["id"],
                    x=angle_point["x"],
                    y=angle_point["y"],
                    angle=angle_point["angle"],
                    line1=angle_point["line1"],
                    line2=angle_point["line2"]
                )
            )
        return angle_points
