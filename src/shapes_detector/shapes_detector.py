import networkx as nx
from matplotlib import pyplot as plt


class ShapesDetection:

    @staticmethod
    def find_intersection(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

        if den == 0:
            return None

        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den

        return px, py

    @staticmethod
    def find_intersections(lines):
        intersections = set()
        for i, line1 in enumerate(lines):
            for j, line2 in enumerate(lines):
                if i >= j:
                    continue

                intersection = ShapesDetection.find_intersection(line1, line2)
                if intersection:
                    intersections.add(intersection)

        return list(intersections)

    @staticmethod
    def point_on_line(point, line, epsilon=1e-6):
        """Check if point is on the line within a tolerance epsilon."""
        x, y = point
        x1, y1, x2, y2 = line
        # Line equation Ax + By = C
        A = y2 - y1
        B = x1 - x2
        C = A * x1 + B * y1
        return abs(A * x + B * y - C) < epsilon

    @staticmethod
    def create_graph(lines, intersection_points):
        G = nx.Graph()
        for x1, y1, x2, y2 in lines:
            G.add_edge((x1, y1), (x2, y2))

        for point in intersection_points:
            for x1, y1, x2, y2 in lines:
                if ShapesDetection.point_on_line(point, (x1, y1, x2, y2)):
                    G.add_edge(point, (x1, y1))
                    G.add_edge(point, (x2, y2))

        return G

    @staticmethod
    def detect_shapes(G):
        shapes = list(nx.cycle_basis(G))
        detected_shapes = []

        for shape in shapes:
            if len(shape) == 3:
                detected_shapes.append(('Triangle', shape))
            elif len(shape) == 4:
                detected_shapes.append(('Square', shape))
            elif len(shape) > 4:
                detected_shapes.append(('Polygon', shape))

        return detected_shapes

    @staticmethod
    def detect(lines):
        intersection_points = ShapesDetection.find_intersections(lines)
        print(f'Intersection points: {intersection_points}')
        G = ShapesDetection.create_graph(lines, intersection_points)

        # Uncomment to visualize the graph
        nx.draw(G, with_labels=True)
        plt.show()

        return ShapesDetection.detect_shapes(G)


if __name__ == '__main__':
    # Example usage
    lines = [(0, 0, 3, 3), (2, 1, 1, 4), (1, 3, 5, 1)]
    shapes = ShapesDetection.detect(lines)
    for shape_type, vertices in shapes:
        print(f"Detected {shape_type} with vertices {vertices}")
