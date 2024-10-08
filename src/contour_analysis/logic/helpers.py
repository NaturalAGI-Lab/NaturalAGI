import logging
from enum import Enum

def calculate_half_plane_and_quadrant(dx, dy):
    horizontal_plane = Commons.HalfPlane.UPPER.value if dy > 0 else Commons.HalfPlane.LOWER.value
    vertical_plane = Commons.HalfPlane.RIGHT.value if dx > 0 else Commons.HalfPlane.LEFT.value

    if dx > 0 and dy > 0:
        quadrant = 1
    elif dx < 0 < dy:
        quadrant = 2
    elif dx < 0 and dy < 0:
        quadrant = 3
    elif dx > 0 > dy:
        quadrant = 4
    else:
        quadrant = -1  # For cases where dx or dy is 0

    logging.debug(f"Half-Planes: {horizontal_plane} and {vertical_plane}")
    logging.debug(f"Quadrant: {quadrant}")

    return horizontal_plane, vertical_plane, quadrant


class Commons:
    class HalfPlane(Enum):
        UPPER = "Upper"
        LOWER = "Lower"
        RIGHT = "Right"
        LEFT = "Left"