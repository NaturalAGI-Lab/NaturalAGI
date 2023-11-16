from skimage.transform import probabilistic_hough_line
from skimage.feature import canny
from matplotlib import cm
from math import atan2, degrees, floor
import numpy as np
import os
import cv2


class LineDetector:
    def detect_lines(self, image):
        # Convert the image to grayscale if it's not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        edges = canny(image, sigma=1.0, low_threshold=10, high_threshold=20)
        lines = probabilistic_hough_line(gray, threshold=10, line_length=2, line_gap=5)

        # Calculate angles for each line and store them
        angles = [self.calculate_angle(line) for line in lines]

        # Cluster lines by angle
        clusters = {}
        for idx, angle in enumerate(angles):
            found_cluster = False
            for cluster_angle in clusters.keys():
                if self.are_similar(angle, cluster_angle):
                    clusters[cluster_angle].append(lines[idx])
                    found_cluster = True
                    break
            if not found_cluster:
                clusters[angle] = [lines[idx]]

        # Assuming clusters is a dictionary with angles as keys and lists of lines as values
        unioned_lines = []

        for angle, lines_n in clusters.items():
            # Extract endpoints for all lines in the cluster
            x_coords = []
            y_coords = []
            for line in lines_n:
                p0, p1 = line
                x_coords.extend([p0[0], p1[0]])
                y_coords.extend([p0[1], p1[1]])

            # Perform linear regression on the endpoints
            A = np.vstack([x_coords, np.ones(len(x_coords))]).T
            m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]

            # Determine the new endpoints for the unioned line
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = m * x_min + c, m * x_max + c

            # Add the new line to the list of unioned lines
            unioned_lines.append(
                [[floor(x_min), floor(y_min), floor(x_max), floor(y_max)]]
            )

        print(f"Lines found: {len(unioned_lines)}")
        intersections = self.all_intersections(unioned_lines)
        print(intersections)
        print(f"Intersection points found: {len(intersections)}")
        return unioned_lines

    def calculate_slope_intercept(self, x1, y1, x2, y2):
        if x2 == x1:
            return None, None  # This indicates a vertical line
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        return slope, intercept

    def find_intersection(self, slope1, intercept1, slope2, intercept2):
        if slope1 is None or slope2 is None:
            return None  # One or both lines are vertical
        if slope1 == slope2:
            return None  # Parallel lines
        x = (intercept2 - intercept1) / (slope1 - slope2)
        y = slope1 * x + intercept1
        return x, y

    def all_intersections(self, lines):
        intersections = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                line1 = lines[i][0]
                line2 = lines[j][0]

                slope1, intercept1 = self.calculate_slope_intercept(
                    line1[0], line1[1], line1[2], line1[3]
                )
                slope2, intercept2 = self.calculate_slope_intercept(
                    line2[0], line2[1], line2[2], line2[3]
                )

                if slope1 is not None and slope2 is not None:
                    intersection = self.find_intersection(
                        slope1, intercept1, slope2, intercept2
                    )
                    if intersection:
                        intersections.append(intersection)
                # Add handling for vertical lines if needed

        return intersections

    # A function to calculate the angle of a line
    def calculate_angle(self, line):
        p0, p1 = line
        return degrees(atan2(p1[1] - p0[1], p1[0] - p0[0]))

    # A function to check if two angles are similar
    def are_similar(self, angle1, angle2, threshold=5):
        return abs(angle1 - angle2) < threshold

    def merge_lines(self, lines_e):
        # Find the most extreme points in the grouped lines
        x_coords = [x for line in lines_e for x in (line[0][0], line[1][0])]
        y_coords = [y for line in lines_e for y in (line[0][1], line[1][1])]

        # Create a new line from the minimum and maximum points
        return (max(x_coords), max(y_coords)), (min(x_coords), min(y_coords))

        # Find the most extreme points in the grouped lines
        x_coords = [x for line in lines_e for x in (line[0][0], line[1][0])]
        y_coords = [y for line in lines_e for y in (line[0][1], line[1][1])]

        # Create a new line from the minimum and maximum points
        return (max(x_coords), max(y_coords)), (min(x_coords), min(y_coords))


if __name__ == "__main__":
    output_folder = "output"
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    img = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.line(img, (0, 0), (300, 300), (63, 124, 172), 2)
    cv2.line(img, (200, 100), (100, 400), (213, 225, 163), 2)
    cv2.line(img, (100, 300), (500, 100), (189, 196, 167), 2)
    cv2.imwrite(f"{output_folder}/img.png", img)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    detector = LineDetector()
    lines = detector.detect_lines(img)

    # Draw detected lines in the image
    blank_img = np.zeros_like(img)

    for dline in lines:
        p0, p1 = dline
        x0 = int(round(p0[0]))
        y0 = int(round(p1[0]))
        x1 = int(round(p0[1]))
        y1 = int(round(p1[1]))
        print(f"Drawing line: x0: {x0}, y0: {y0}, x1: {x1}, y1: {y1}")
        cv2.line(blank_img, (x0, y0), (x1, y1), 255, 1)

    cv2.imwrite(f"{output_folder}/image_with_detected_lines.jpg", blank_img)
