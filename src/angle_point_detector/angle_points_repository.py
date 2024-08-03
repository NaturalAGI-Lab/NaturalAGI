import math
import uuid
from typing import List, Dict, Tuple, Optional

def line_intersection(line1: Dict[str, int], line2: Dict[str, int]) -> Optional[Tuple[int, int]]:
    x1, y1, x2, y2 = line1['x1'], line1['y1'], line1['x2'], line1['y2']
    x3, y3, x4, y4 = line2['x1'], line2['y1'], line2['x2'], line2['y2']

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denominator == 0:
        return None

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator

    delta = 5  # Allow intersection point to be up to 5 units outside the line bounds

    if (min(x1, x2) - delta <= px <= max(x1, x2) + delta and
        min(y1, y2) - delta <= py <= max(y1, y2) + delta and
        min(x3, x4) - delta <= px <= max(x3, x4) + delta and
        min(y3, y4) - delta <= py <= max(y3, y4) + delta):
        return int(px), int(py)
    else:
        return None

def calculate_angle(line1: Dict[str, int], line2: Dict[str, int], intersection: Tuple[int, int]) -> int:
    # Calculate side lengths
    a = math.sqrt((line1['x2'] - intersection[0])**2 + (line1['y2'] - intersection[1])**2)
    b = math.sqrt((line2['x2'] - intersection[0])**2 + (line2['y2'] - intersection[1])**2)
    c = math.sqrt((line1['x2'] - line2['x2'])**2 + (line1['y2'] - line2['y2'])**2)
    
    # Calculate angle using the law of cosines
    cos_angle = (a**2 + b**2 - c**2) / (2 * a * b)
    
    # Clamp the value to avoid domain errors due to floating point imprecision
    cos_angle = max(min(cos_angle, 1), -1)
    
    # Calculate angle in degrees
    angle = math.degrees(math.acos(cos_angle))
    
    return round_to_nearest(int(angle), 5)

def round_to_nearest(number: int, n: int) -> int:
    return round(number / n) * n

def calculate_angle_points(lines: List[Dict[str, int]]) -> List[Dict[str, any]]:
    angle_points = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            line1 = lines[i]
            line2 = lines[j]
            intersection = line_intersection(line1, line2)
            if intersection:
                angle = calculate_angle(line1, line2, intersection)
                angle_points.append({
                    'id': str(uuid.uuid4()),
                    'x': intersection[0],
                    'y': intersection[1],
                    'angle': angle,
                    'line1': line1['id'],
                    'line2': line2['id'],
                })
    return angle_points