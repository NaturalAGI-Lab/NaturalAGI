import argparse
from PIL import Image, ImageDraw
import random
import os

from image_aggregator import do_intersect


def generate_triangle_images(output_dir, num_images, img_size, is_noised):
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(num_images):
        # Create a blank image with white background
        img = Image.new('RGB', (img_size, img_size), 'black')
        draw = ImageDraw.Draw(img)

        # Generate random points for the triangle
        points = [(random.randint(0, img_size - 1), random.randint(0, img_size - 1)) for _ in range(3)]

        # Generate lines width
        line_width = random.randint(1, 5)

        # Draw lines forming a triangle
        draw.line([points[0], points[1]], fill='white', width=line_width)
        draw.line([points[1], points[2]], fill='white', width=line_width)
        draw.line([points[2], points[0]], fill='white', width=line_width)

        if is_noised:
            line_count = random.randint(0, 3)
            for _ in range(line_count):
                while True:
                    line = [(random.randint(0, img_size - 1), random.randint(0, img_size - 1)),
                            (random.randint(0, img_size - 1), random.randint(0, img_size - 1))]
                    if not any(do_intersect(line[0], line[1], points[i], points[(i + 1) % 3]) for i in range(3)):
                        break

                draw.line(line, fill='white')

        # Save the image
        img.save(f"{output_dir}/triangle_{i}.bmp")

    print(f"{num_images} images have been saved to {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images with random triangles.")
    parser.add_argument('--num_images', type=int, default=5, help="Number of images to generate")
    parser.add_argument('--num_triangles', type=int, default=1, help="Number of triangles per image")
    parser.add_argument('--img_size', type=int, default=32, help="Size of each image in pixels")
    parser.add_argument('--output_dir', type=str, default="../../tests/generated_samples",
                        help="Directory to save images")
    parser.add_argument('--is_noised', type=bool, default=False,
                        help="Flag to include noise besides 3 lines which have 3 intersection points")

    args = parser.parse_args()

    generate_triangle_images(args.output_dir, args.num_images, args.img_size, args.is_noised)
