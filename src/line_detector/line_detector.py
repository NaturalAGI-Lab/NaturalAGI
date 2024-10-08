import argparse
import logging
import os
import uuid
from skimage.morphology import skeletonize

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

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Perform skeletonization
    skeleton = skeletonize(binary / 255)  # Normalize to [0, 1] range
    skeleton = (skeleton * 255).astype(np.uint8)  # Convert back to [0, 255] range

    # Use HoughLinesP on the skeleton image
    height, width = skeleton.shape[:2]
    
    # Calculate relative parameters
    min_line_length = int(0.1 * min(height, width)) 
    max_line_gap = int(0.1 * min(height, width)) 
    threshold = 1

    lines = cv2.HoughLinesP(skeleton, 1, np.pi / 180, threshold=threshold, 
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

    logging.info(f"Pre-processed lines found: {len(lines)}")
    logging.info(f"Post-processed lines: {len(processed_lines)}")
    return processed_lines


def skeletonize_image(image: np.ndarray) -> np.ndarray:
    # Convert the image to grayscale if it's not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Threshold the image to create a binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Perform skeletonization
    skeleton = skeletonize(binary / 255)  # Normalize to [0, 1] range
    skeleton = (skeleton * 255).astype(np.uint8)  # Convert back to [0, 255] range

    return skeleton


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect lines in an image")
    parser.add_argument("--folder_path", type=str, default="", help="Path to the folder containing images")
    parser.add_argument("--num_lines", type=int, default=3, help="Number of lines to detect")
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