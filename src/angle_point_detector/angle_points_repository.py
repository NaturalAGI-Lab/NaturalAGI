import math
import uuid


def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1['x1'], line1['y1'], line1['x2'], line1['y2']
    x3, y3, x4, y4 = line2['x1'], line2['y1'], line2['x2'], line2['y2']

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denominator == 0:
        return None

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator

    # Check if the intersection point is within the boundaries of both lines
    if min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2) and \
            min(x3, x4) <= px <= max(x3, x4) and min(y3, y4) <= py <= max(y3, y4):
        return [int(px), int(py)]
    else:
        return None


def calculate_angle(line1, line2):
    dx1 = line1['x2'] - line1['x1']
    dy1 = line1['y2'] - line1['y1']
    dx2 = line2['x2'] - line2['x1']
    dy2 = line2['y2'] - line2['y1']

    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(dy2, dx2)
    angle = abs(angle1 - angle2)

    if angle > math.pi:
        angle = 2 * math.pi - angle

    # Ensuring the angle is always the interior angle
    if angle > math.pi / 2:
        angle = math.pi - angle

    angle = int(math.degrees(angle))  # Convert to degrees

    return angle


def calculate_angle_points(lines):
    angle_points = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            line1 = lines[i]
            line2 = lines[j]
            intersection = line_intersection(line1, line2)
            if intersection:
                angle = calculate_angle(lines[i], lines[j])
                angle_points.append({
                    'id': str(uuid.uuid4()),  # Add UUID for angle point
                    'x': intersection[0],
                    'y': intersection[1],
                    'angle': angle,
                    'line1': line1['id'],  # Use UUID of line1
                    'line2': line2['id'],  # Use UUID of line2
                })
    return angle_points
