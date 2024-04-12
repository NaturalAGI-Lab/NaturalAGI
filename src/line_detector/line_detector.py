import numpy as np
import os
import cv2
import argparse

from hough_builder import HoughBundler


class LineDetector:
    def detect_lines(self, image):
        # Convert the image to grayscale if it's not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        lines = cv2.HoughLinesP(gray, 1, np.pi / 180, threshold=15, lines=None, minLineLength=5, maxLineGap=1)
        
        # Check if lines is None
        if lines is None:
            print("No lines found")
            return []
        
        # Initialize HoughBundler
        bundler = HoughBundler(min_distance=10, min_angle=10)
        
        # Process lines
        processed_lines = bundler.process_lines(lines)

        print(f"Pre-processed lines found: {len(lines)}")
        print(f"Post-processed lines: {len(processed_lines)}")
        return processed_lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect lines in an image")
    parser.add_argument('--folder_path', type=str, default="", help="Path to the folder containing images")
    
    args = parser.parse_args()
    
    detector = LineDetector()
    
    folder_path = args.folder_path
    image_files = os.listdir(folder_path)
    
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        image = cv2.imread(image_path)
        lines = detector.detect_lines(image)
        # Remove the files with lines not equal to 3
        if len(lines) != 3:
            print('Removing image: ', image_path)
            os.remove(image_path)
        print('Image path: ', image_path)
        print('Number of lines: ', len(lines))
        print('---------------------------------')