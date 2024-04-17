import argparse
import os
import random
from PIL import Image, ImageDraw


def _generate_square(img_size):
    img = Image.new("L", (img_size, img_size), color="black")
    draw = ImageDraw.Draw(img)

    square_size = random.randint(round(img_size * 0.1), round(img_size * 0.5))
    start_point = (
        random.randint(0, img_size - square_size),
        random.randint(0, img_size - square_size),
    )
    end_point = (start_point[0] + square_size, start_point[1] + square_size)

    draw.rectangle([start_point, end_point], outline="white", width=img_size // 50)

    # Add random rotation
    angle = random.randint(0, 360)
    img = img.rotate(angle)

    return img


def generate_square_samples(output_dir, num_images, img_size):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(num_images):
        _generate_square(img_size).save(os.path.join(output_dir, f"square_{i}.png"))


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
