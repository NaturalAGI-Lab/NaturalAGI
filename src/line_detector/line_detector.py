import cv2
import numpy as np


class LineDetector:

    @staticmethod
    def detect_lines(image):
        H, W = image.shape[:2]
        lsd = cv2.createLineSegmentDetector(0)

        lines = lsd.detect(image)[0]

        # Initialize an empty list to hold the clamped lines
        clamped_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Clamp the coordinates
            x1 = min(max(round(x1), 0), W - 1)
            y1 = min(max(round(y1), 0), H - 1)
            x2 = min(max(round(x2), 0), W - 1)
            y2 = min(max(round(y2), 0), H - 1)

            # Append the clamped line to the list
            clamped_lines.append([[x1, y1, x2, y2]])

        print(f'Original lines detected: {len(lines)}')
        print(f'Clamped lines: {clamped_lines}')
        return clamped_lines


if __name__ == '__main__':
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    cv2.line(img, (0, 3), (7, 3), (255, 255, 255), 1)
    cv2.imwrite("1.png", img)

    # img = cv2.imread("img.png")
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # lines = LineDetector.detect_lines(img)
    #
    # # Draw detected lines in the image
    # blank_img = np.zeros_like(img)
    #
    # for dline in lines:
    #     x0 = int(round(dline[0][0]))
    #     y0 = int(round(dline[0][1]))
    #     x1 = int(round(dline[0][2]))
    #     y1 = int(round(dline[0][3]))
    #     print(f"Drawing line: x0: {x0}, y0: {y0}, x1: {x1}, y1: {y1}")
    #     cv2.line(blank_img, (x0, y0), (x1, y1), 255, 1)
    #
    # cv2.imwrite("image_with_detected_lines.jpg", blank_img)
