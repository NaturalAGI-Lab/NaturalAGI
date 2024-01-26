from enum import Enum
import logging
import numpy as np

def find_next_vector(line_details, min_angle_point):
    next_line = None
    next_coords = None
    max_sum = 0

    for detail in line_details:
        line = detail["vector"]
        coords = detail["coordinates"]
        ap_x = min_angle_point["x"]
        x1, x2 = coords["x1"], coords["x2"]
        local_sum = ap_x + x1 + x2

        if local_sum > max_sum:
            max_sum = local_sum
            next_line = line
            next_coords = coords

    return next_line, next_coords


def calculate_half_plane_and_quadrant(dx, dy):
    vector = np.array([dx, dy])

    horizontal_plane = Commons.HalfPlane.UPPER.value if vector[1] > 0 else Commons.HalfPlane.LOWER.value
    vertical_plane = Commons.HalfPlane.RIGHT.value if vector[0] > 0 else Commons.HalfPlane.LEFT.value

    quadrant = np.digitize([vector[0], vector[1]], bins=[0, 0])
    quadrant_map = {1: 4, 2: 1, 3: 2, 4: 3}
    quadrant = quadrant_map.get(sum(quadrant), -1)

    logging.debug(f"Half-Planes: {horizontal_plane} and {vertical_plane}")
    logging.debug(f"Quadrant: {quadrant}")

    return horizontal_plane, vertical_plane, quadrant

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

