import json
import base64
import math

import cv2
import numpy as np


def handler(context, event):
    context.logger.info('Running line detection')

    # Decode the base64 image
    base64_image = event.body
    image_data = base64.b64decode(base64_image)
    image_np = np.frombuffer(image_data, dtype=np.uint8)
    image = cv2.imdecode(image_np, flags=1)

    # Perform line detection
    result_image = detect_lines(image)

    # Convert back to base64
    _, img_encoded = cv2.imencode('.jpg', result_image)
    img_base64 = base64.b64encode(img_encoded.tostring()).decode('utf-8')

    return context.Response(body=json.dumps({'image': img_base64}),
                            headers={},
                            content_type='application/json',
                            status_code=200)

def slope_intercept(x1, y1, x2, y2):
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return slope, intercept

def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def detect_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Use canny edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Apply HoughLinesP method to
    # to directly obtain line end points
    lines_list = []
    lines = cv2.HoughLinesP(
        edges,  # Input edge image
        1,  # Distance resolution in pixels
        np.pi / 180,  # Angle resolution in radians
        threshold=100,  # Min number of votes for valid line
        minLineLength=5,  # Min allowed l0ength of line
        maxLineGap=10  # Max allowed gap between line for joining them
    )

    print(f'Lines detected: {len(lines)}')

    # Iterate over points
    for points in lines:
        # Extracted points nested in the list
        x1, y1, x2, y2 = points[0]
        # Draw the lines joing the points
        # On the original image
        cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    return image