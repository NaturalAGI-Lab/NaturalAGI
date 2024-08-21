import argparse
import logging
import os
from typing import Dict, List, Union
import uuid

import cv2
import numpy as np

from hough_bundler import HoughBundler

logging.basicConfig(level=logging.INFO)


def _get_line_length(line: list) -> float:
    """Get the length of a line"""
    return np.sqrt((line[2] - line[0]) ** 2 + (line[3] - line[1]) ** 2)


def detect_lines(image: np.ndarray) -> list:
    # Convert the image to grayscale if it's not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    height, width = gray.shape[:2]
    
    # Calculate relative parameters
    min_line_length = int(0.1 * min(height, width)) 
    max_line_gap = int(0.1 * min(height, width)) 
    threshold = int(0.25 * min(height, width)) 

    lines = cv2.HoughLinesP(gray, 1, np.pi / 180, threshold=threshold, 
                            minLineLength=min_line_length, maxLineGap=max_line_gap)

    # Check if lines is None
    if lines is None:
        print("No lines found")
        return []

    # Initialize HoughBundler with relative parameters
    min_distance = int(0.1 * min(height, width)) 
    bundler = HoughBundler(min_distance=min_distance, min_angle=15)

    # Process lines
    processed_lines = bundler.process_lines(lines)
    processed_lines = [{'id': str(uuid.uuid4()), 'x1': int(line[0][0]), 'y1': int(line[0][1]), 'x2': int(line[0][2]),
                        'y2': int(line[0][3]), 'length': int(_get_line_length(line[0]))} for line in processed_lines]

    logging.debug(f"Pre-processed lines found: {len(lines)}")
    logging.debug(f"Post-processed lines: {len(processed_lines)}")
    return processed_lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect lines in an image")
    parser.add_argument("--folder_path", type=str, default="", help="Path to the folder containing images")
    parser.add_argument("--num_lines", type=int, default=3, help="Number of lines to detect")
    parser.add_argument("--min_distance_factor", type=float, default=0.02, 
                        help="Minimum distance factor for HoughBundler (relative to image size)")
    parser.add_argument("--min_angle", type=float, default=15, 
                        help="Minimum angle for HoughBundler")

    args = parser.parse_args()

    folder_path = args.folder_path
    num_lines = args.num_lines
    image_files = [f for f in os.listdir(folder_path) if f.endswith('.bmp')]


    valid_images_count = 0

    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        image = cv2.imread(image_path)
        
        # Calculate min_distance based on image size
        height, width = image.shape[:2]
        min_distance = int(args.min_distance_factor * min(height, width))
        
        # Initialize HoughBundler with relative min_distance
        bundler = HoughBundler(min_distance=min_distance, min_angle=args.min_angle)
        
        lines = detect_lines(image)
        if len(lines) == num_lines:
            valid_images_count += 1
            logging.debug(f"Valid image: {image_path}")
        else:
            logging.debug(f"Removing image: {image_path}")
            os.remove(image_path)
        logging.debug(f"Image path: {image_path}")
        logging.debug(f"Number of lines: {len(lines)}")

    logging.debug(f"Valid images count: {valid_images_count}")
    exit(valid_images_count)