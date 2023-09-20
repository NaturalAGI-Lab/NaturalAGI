from handler import detect_lines
import cv2
import numpy as np

if __name__ == '__main__':
    img = np.zeros((1000, 1000, 3), dtype=np.uint8)
    cv2.line(img, (100, 100), (900, 900), (255, 255, 255), 1)
    cv2.imwrite("image_generated.jpg", img)

    detected_img = detect_lines(img.copy())
    cv2.imwrite("image_with_detected_lines.jpg", detected_img)

    # print(len(detected_img[:,:,2]))
