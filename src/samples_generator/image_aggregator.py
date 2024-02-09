import math


def calculate_angle(a, b, c):
    # Calculate the angle opposite side c using the law of cosines
    angle = math.acos((a ** 2 + b ** 2 - c ** 2) / (2 * a * b))
    return math.degrees(angle)


def is_triangle_valid(vertices):
    # Calculate the lengths of the sides
    sides = [
        math.sqrt((vertices[1][0] - vertices[0][0]) ** 2 + (vertices[1][1] - vertices[0][1]) ** 2),
        math.sqrt((vertices[2][0] - vertices[1][0]) ** 2 + (vertices[2][1] - vertices[1][1]) ** 2),
        math.sqrt((vertices[0][0] - vertices[2][0]) ** 2 + (vertices[0][1] - vertices[2][1]) ** 2)
    ]

    # Calculate the angles
    angles = [
        calculate_angle(sides[1], sides[2], sides[0]),
        calculate_angle(sides[0], sides[2], sides[1]),
        calculate_angle(sides[0], sides[1], sides[2])
    ]

    # Check if any angle is greater than 120 degrees
    return all(angle <= 120 for angle in angles)


def on_segment(p, q, r):
    return (max(p[0], r[0]) >= q[0] >= min(p[0], r[0]) and
            max(p[1], r[1]) >= q[1] >= min(p[1], r[1]))


def orientation(p, q, r):
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if val == 0: return 0  # Collinear
    return 1 if val > 0 else 2  # Clockwise or counterclockwise


def do_intersect(p1, q1, p2, q2):
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4: return True
    if o1 == 0 and on_segment(p1, p2, q1): return True
    if o2 == 0 and on_segment(p1, q2, q1): return True
    if o3 == 0 and on_segment(p2, p1, q2): return True
    if o4 == 0 and on_segment(p2, q1, q2): return True

    return False


def extend_line(p1, p2, extension):
    # Calculate the direction vector of the line
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    # Normalize the direction vector
    length = (dx ** 2 + dy ** 2) ** 0.5
    dx /= length
    dy /= length

    # Extend the points in both directions
    p1_extended = (p1[0] - dx * extension, p1[1] - dy * extension)
    p2_extended = (p2[0] + dx * extension, p2[1] + dy * extension)

    return p1_extended, p2_extended


def generate_curved_line(start, end, curvature, steps):
    points = []
    for step in range(steps + 1):
        t = step / steps
        # Linear interpolation for control point
        mid_x = start[0] * (1 - t) + end[0] * t
        mid_y = start[1] * (1 - t) + end[1] * t

        # Apply curvature
        angle = math.atan2(end[1] - start[1], end[0] - start[0]) + math.pi / 2
        curve_x = mid_x + math.cos(angle) * curvature * math.sin(math.pi * t)
        curve_y = mid_y + math.sin(angle) * curvature * math.sin(math.pi * t)

        points.append((curve_x, curve_y))
    return points


def generate_curved_line_extended(start, end, curvature, extension, steps):
    # Calculate direction vector from start to end
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx ** 2 + dy ** 2)

    # Normalize direction vector
    dx /= length
    dy /= length

    # Extend start and end points
    extended_start = (start[0] - dx * extension, start[1] - dy * extension)
    extended_end = (end[0] + dx * extension, end[1] + dy * extension)

    points = []
    for step in range(steps + 1):
        t = step / steps
        # Linear interpolation for control point
        mid_x = extended_start[0] * (1 - t) + extended_end[0] * t
        mid_y = extended_start[1] * (1 - t) + extended_end[1] * t

        # Apply curvature
        angle = math.atan2(dy, dx) + math.pi / 2
        curve_x = mid_x + math.cos(angle) * curvature * math.sin(math.pi * t)
        curve_y = mid_y + math.sin(angle) * curvature * math.sin(math.pi * t)

        points.append((curve_x, curve_y))
    return points


def generate_zigzag_points(start, end, amplitude, frequency):
    points = []
    for i in range(frequency + 1):
        t = i / frequency
        mid_point = (start[0] * (1 - t) + end[0] * t, start[1] * (1 - t) + end[1] * t)

        # Calculate direction perpendicular to the line
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx ** 2 + dy ** 2)
        perp_dx = -dy / length
        perp_dy = dx / length

        # Alternate the side of the zigzag
        direction = 1 if i % 2 == 0 else -1
        zigzag_point = (mid_point[0] + direction * perp_dx * amplitude, mid_point[1] + direction * perp_dy * amplitude)

        points.append(zigzag_point)

    # Include the end point if frequency is odd
    if frequency % 2 == 0:
        points.append(end)

    return points


def generate_zigzag_points_extended(start, end, amplitude, frequency, extension):
    points = [start]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx**2 + dy**2)
    angle = math.atan2(dy, dx)

    # Length of each zigzag segment
    segment_length = length / frequency

    # Generate zigzag points
    for i in range(1, frequency + 1):
        direction = 1 if i % 2 == 1 else -1  # Alternate direction for each segment
        # Angle perpendicular to the main line for peaks/troughs
        perp_angle = angle + math.pi / 2 * direction
        # Calculate peak/trough point
        peak_x = points[-1][0] + math.cos(perp_angle) * amplitude + math.cos(angle) * segment_length
        peak_y = points[-1][1] + math.sin(perp_angle) * amplitude + math.sin(angle) * segment_length
        points.append((peak_x, peak_y))

    # Add extensions
    extension_start_angle = angle - math.pi
    extension_end_angle = angle
    start_extension = (start[0] + math.cos(extension_start_angle) * extension,
                       start[1] + math.sin(extension_start_angle) * extension)
    end_extension = (end[0] + math.cos(extension_end_angle) * extension,
                     end[1] + math.sin(extension_end_angle) * extension)

    # Insert start extension at the beginning and append end extension
    points = [start_extension] + points + [end_extension]

    return points
