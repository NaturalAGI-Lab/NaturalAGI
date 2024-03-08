import argparse

from PIL import Image, ImageDraw
import random
import os

from image_aggregator import do_intersect, extend_line, generate_curved_line_extended, generate_zigzag_points_extended, \
    is_triangle_valid


def generate_triangle_images(output_dir, num_images, img_size, is_noised, curved_sides, zigzag_sides, broken_sides):
    global curved_sides_num, zigzag_sides_num, straight_sides_num
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(num_images):
        # Create a blank image with white background
        img = Image.new('RGB', (img_size, img_size), 'black')
        draw = ImageDraw.Draw(img)

        # Generate random vertices for the triangle
        vertices = generate_triangle(img_size)
        sides = [(vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], vertices[0])]
        drawn_sides = []

        # Generate lines width
        line_width = random.randint(1, 5)

        curved_sides_num = 0
        zigzag_sides_num = 0
        broken_sides_num = 0
        if curved_sides:
            curved_sides_num = random.randint(0, 3)
        if zigzag_sides:
            zigzag_sides_num = random.randint(0, 3 - curved_sides_num)
        if broken_sides:
            broken_sides_num = 1
        straight_sides_num = 3 - curved_sides_num - zigzag_sides_num - broken_sides_num

        # Generate and draw curved sides
        for k in range(curved_sides_num):
            draw_curved_side(draw, sides[k], line_width, img_size)
            drawn_sides.append(sides[k])

        sides = [item for item in sides if item not in drawn_sides]

        # Generate and draw zigzag sides
        for m in range(zigzag_sides_num):
            draw_zigzag_side(draw, sides[m], line_width, img_size)
            drawn_sides.append(sides[m])

        sides = [item for item in sides if item not in drawn_sides]

        for n in range(broken_sides_num):
            draw_broken_side(draw, sides[n], line_width)
            drawn_sides.append(sides[n])

        sides = [item for item in sides if item not in drawn_sides]

        # Generate and draw straight sides
        for p in range(straight_sides_num):
            extended_start, extended_end = extend_line(sides[p][0], sides[p][1],
                                                       random.randint(round(img_size * 0.05), round(img_size * 0.3)))
            draw.line([extended_start, extended_end], fill='white', width=line_width)

        if is_noised:
            line_count = random.randint(0, 3)
            for _ in range(line_count):
                while True:
                    line = [(random.randint(0, img_size - 1), random.randint(0, img_size - 1)),
                            (random.randint(0, img_size - 1), random.randint(0, img_size - 1))]
                    if not any(do_intersect(line[0], line[1], vertices[i], vertices[(i + 1) % 3])
                               for i in range(3)):
                        break

                draw.line(line, fill='white')

        # Save the image
        img.save(f"{output_dir}/triangle_{i}_{curved_sides_num}_{zigzag_sides_num}_{straight_sides_num}.bmp")

    print(f"{num_images} images have been saved to {output_dir}/")


def generate_triangle(img_size):
    while True:
        vertices = [(random.randint(0, img_size - 1), random.randint(0, img_size - 1)) for _ in range(3)]
        if is_triangle_valid(vertices):
            return vertices


def draw_curved_side(draw, side, line_width, img_size):
    points = generate_curved_line_extended(side[0], side[1], curvature=random.randint(0, 10),
                                           extension=random.randint(round(img_size * 0.05), round(img_size * 0.3)),
                                           steps=random.randint(10, 20))
    draw.line(points, fill='white', width=line_width)


def draw_zigzag_side(draw, side, line_width, img_size):
    zigzag_points = generate_zigzag_points_extended(side[0], side[1], amplitude=random.randint(1, 5),
                                                    frequency=random.randint(15, 35),
                                                    extension=random.randint(round(img_size * 0.05),
                                                                             round(img_size * 0.3)))
    draw.line(zigzag_points, fill='white', width=line_width)


def draw_broken_side(draw, side, line_width):
    start_point = side[0]
    end_point = side[1]

    n_segments = 4

    # Initialize the current point to the start point
    current_point = start_point

    # Calculate the total vector from start to end
    total_dx = end_point[0] - start_point[0]
    total_dy = end_point[1] - start_point[1]

    # Calculate the step size for each segment
    dx = total_dx / n_segments
    dy = total_dy / n_segments

    deviation = 10

    # Draw each segment with a deviation
    for i in range(n_segments - 1):
        # Calculate the next point with some deviation
        next_point = (current_point[0] + dx + random.uniform(-deviation, deviation),
                      current_point[1] + dy + random.uniform(-deviation, deviation))

        # Draw the segment
        draw.line([current_point, next_point], fill="white", width=line_width)

        # Update the current point
        current_point = next_point

    # Ensure the last segment reaches the end point
    draw.line([current_point, end_point], fill="white", width=line_width)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images with random triangles.")
    parser.add_argument('--num_images', type=int, default=10, help="Number of images to generate")
    parser.add_argument('--img_size', type=int, default=32, help="Size of each image in pixels")
    parser.add_argument('--output_dir', type=str, default="../../tests/generated_samples",
                        help="Directory to save images")
    parser.add_argument('--is_noised', type=bool, default=False,
                        help="Flag to allow noise besides 3 lines which have 3 intersection points")
    parser.add_argument('--curved_sides', type=bool, default=False,
                        help="Flag to allow slightly curved triangles sides")
    parser.add_argument('--zigzag_sides', type=bool, default=False,
                        help="Flag to allow zigzag polygons as triangle's sides")
    parser.add_argument('--broken_sides', type=bool, default=False,
                        help="Flag to allow broken triangle's sides")

    args = parser.parse_args()

    generate_triangle_images(args.output_dir, args.num_images, args.img_size, args.is_noised, args.curved_sides,
                             args.zigzag_sides, args.broken_sides)
