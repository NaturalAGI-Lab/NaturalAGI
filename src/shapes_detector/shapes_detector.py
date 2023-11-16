from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, polygonize


class ShapesDetection:

    @staticmethod
    def detect(lines):
        # Convert lines to LineString objects
        line_objects = [LineString(pair) for pair in lines]
        # Compute the union of the lines, which automatically calculates intersections
        unified_lines = unary_union(line_objects)
        # Polygonize the unified line structure
        polygons = list(polygonize(unified_lines))
        
        ShapesDetection.print_polygon_details(polygons)
        return polygons
    
    # Function to print detailed info about polygons
    @staticmethod
    def print_polygon_details(polygons):
        for i, polygon in enumerate(polygons, 1):
            # Get the exterior coordinates of the polygon
            exterior_coords = list(polygon.exterior.coords)
            num_sides = len(exterior_coords) - 1  # Last point is the same as the first
            area = polygon.area
            perimeter = polygon.length
            
            # Print details
            print(f"Polygon {i}:")
            print(f"  Number of Sides: {num_sides}")
            print(f"  Area: {area:.2f}")
            print(f"  Perimeter: {perimeter:.2f}")
            print(f"  Coordinates of Vertices:")
            for coord in exterior_coords[:-1]:  # Exclude the last point because it's a repeat of the first
                print(f"    {coord}")
            print("")  # Add a blank line for readability between polygons


if __name__ == '__main__':
    # Example usage
    # lines = [(0, 0, 3, 3), (2, 1, 1, 4), (1, 3, 5, 1)]
    lines = [
    # Square perimeter
    (0, 0, 3, 0),  # Bottom side
    (3, 0, 3, 3),  # Right side
    (3, 3, 0, 3),  # Top side
    (0, 3, 0, 0),  # Left side
    
    # Additional lines that intersect but also contribute to forming a square
    (1, -1, 1, 4),  # Vertical line intersecting bottom side
    (-1, 1, 4, 1),  # Horizontal line intersecting left side
    (2, -1, 2, 4),  # Another vertical line intersecting bottom side
    (-1, 2, 4, 2),  # Another horizontal line intersecting left side
    
    # Diagonals inside the square
    (0, 0, 3, 3),  # Diagonal from bottom-left to top-right
    (3, 0, 0, 3),  # Diagonal from bottom-right to top-left
    ]
    # Preprocess lines to fit the format ((x1, y1), (x2, y2))
    preprocessed_lines = [((line[0], line[1]), (line[2], line[3])) for line in lines]
    shapes = ShapesDetection.detect(preprocessed_lines)
