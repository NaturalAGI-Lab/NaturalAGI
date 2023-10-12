import cv2
import numpy as np


class LineDetector:

    @staticmethod
    def detect_lines(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lsd = cv2.createLineSegmentDetector(
            scale=10,
            sigma_scale=.001,
            quant=5,
        )

        lines = lsd.detect(gray)[0]
        print(f'Lines detected: {len(lines)}, {lines}')

        # Draw detected lines in the image
        blank_img = np.zeros_like(gray)
        for line in lines:
            x1, y1, x2, y2 = map(int, line[0])  # Get the endpoints of the line segment
            cv2.line(blank_img, (x1, y1), (x2, y2), (255, 255, 255), 1)

        return blank_img


if __name__ == '__main__':
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    cv2.line(img, (0, 3), (7, 3), (255, 255, 255), 1)
    cv2.imwrite("1.png", img)

    # img = cv2.imread("1.png", 1)

    detected_img = LineDetector.detect_lines(img)
    cv2.imwrite("image_with_detected_lines.jpg", detected_img)
