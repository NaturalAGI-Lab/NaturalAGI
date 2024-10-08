import math
import uuid
from typing import List, Dict, Tuple, Optional, Any

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

def calculate_angle(line1: Dict[str, int], line2: Dict[str, int], intersection: Tuple[int, int]) -> float:
    # Calculate direction vectors
    dx1 = line1['x2'] - line1['x1'] 
    dy1 = line1['y2'] - line1['y1']
    dx2 = line2['x2'] - line2['x1']
    dy2 = line2['y2'] - line2['y1']
    
    # Calculate dot product and magnitudes
    dot = dx1*dx2 + dy1*dy2
    mag1 = math.sqrt(dx1**2 + dy1**2) 
    mag2 = math.sqrt(dx2**2 + dy2**2)
    
    # Check for zero-length lines
    if mag1 == 0 or mag2 == 0:
        raise ValueError("Cannot calculate angle for zero-length line")
        
    # Calculate cosine of angle and clip to valid range
    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1, min(cos_angle, 1))
    
    # Calculate angle in radians
    angle_rad = math.acos(cos_angle)
    
    # Convert to degrees
    angle_deg = math.degrees(angle_rad)
    
    # Ensure angle is between 0 and 180
    if angle_deg > 180:
        angle_deg = 360 - angle_deg
        
    return round(angle_deg, 5)

def round_to_nearest(number: int, n: int) -> int:
    return round(number / n) * n

def calculate_points(lines: List[Dict[str, int]]) -> List[Dict[str, Any]]:
    points = []
    intersection_points = set()
    
    for i, line in enumerate(lines):
        # Calculate angle points (intersections)
        for j in range(i + 1, len(lines)):
            line1 = lines[i]
            line2 = lines[j]
            intersection = line_intersection(line1, line2)
            if intersection:
                angle = calculate_angle(line1, line2, intersection)
                points.append({
                    'id': str(uuid.uuid4()),
                    'x': intersection[0],
                    'y': intersection[1],
                    'angle': round_to_nearest(angle, 5),
                    'type': 'angle_point',
                    'line1': line1['id'],
                    'line2': line2['id'],
                })
                intersection_points.add(intersection)
    
    # Add endpoints that are not intersection points
    for line in lines:
        start_point = (line['x1'], line['y1'])
        end_point = (line['x2'], line['y2'])
        
        if start_point not in intersection_points:
            points.append({
                'id': str(uuid.uuid4()),
                'x': start_point[0],
                'y': start_point[1],
                'type': 'endpoint',
                'line': line['id']
            })
        
        if end_point not in intersection_points:
            points.append({
                'id': str(uuid.uuid4()),
                'x': end_point[0],
                'y': end_point[1],
                'type': 'endpoint',
                'line': line['id']
            })
    
    return points