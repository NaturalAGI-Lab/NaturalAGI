import argparse
import datetime
import os
import random
from PIL import Image, ImageDraw


def _generate_square(img_size: int) -> Image.Image:
    img = Image.new("L", (img_size, img_size), color="black")
    draw = ImageDraw.Draw(img)

    max_square_size = round(img_size * 0.5)
    min_square_size = round(img_size * 0.1)
    square_size = random.randint(min_square_size, max_square_size)

    max_start_point = img_size - square_size
    start_point = (
        random.randint(0, max_start_point),
        random.randint(0, max_start_point),
    )
    end_point = (start_point[0] + square_size, start_point[1] + square_size)

    line_width = 3
    draw.rectangle([start_point, end_point], outline="white", width=line_width)

    angle = random.randint(0, 360)
    rotated_img = img.rotate(angle, expand=True)

    return rotated_img


def generate_square_samples(output_dir: str, num_images: int, img_size: int) -> None:
    os.makedirs(output_dir, exist_ok=True)

    for _ in range(num_images):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        square_img = _generate_square(img_size)
        square_img.save(os.path.join(output_dir, f"square_{timestamp}.png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate square samples")
    parser.add_argument(
        "--num_images", type=int, default=10, help="Number of images to generate"
    )
    parser.add_argument(
        "--img_size", type=int, default=32, help="Size of each image in pixels"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="../../tests/generated_samples",
        help="Directory to save the generated images",
    )

    args = parser.parse_args()

    generate_square_samples(args.output_dir, args.num_images, args.img_size)