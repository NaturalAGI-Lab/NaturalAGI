from skimage.transform import probabilistic_hough_line
from skimage.feature import canny
from matplotlib import cm
from math import atan2, degrees, floor
import numpy as np
import os
import cv2

from hough_builder import HoughBundler


class LineDetector:
    def detect_lines(self, image):
        # Convert the image to grayscale if it's not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # edges = canny(image, sigma=1.0, low_threshold=10, high_threshold=20)
        # lines = probabilistic_hough_line(gray, threshold=10, line_length=2, line_gap=5)
        lines = cv2.HoughLinesP(gray, 1, np.pi / 180, 50, None, 50, 10)
        
        # Initialize HoughBundler
        bundler = HoughBundler(min_distance=10, min_angle=5)
        
        # Process lines
        processed_lines = bundler.process_lines(lines)

        print(f"Pre-processed lines found: {len(lines)}")
        print(f"Post-processed lines: {len(processed_lines)}")
        return processed_lines


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
