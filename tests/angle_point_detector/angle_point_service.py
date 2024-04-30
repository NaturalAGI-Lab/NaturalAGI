import unittest
from src.angle_point_detector.angle_points_repository import line_intersection, calculate_angle, calculate_angle_points


class LineIntersectionTests(unittest.TestCase):
    def test_lines_intersecting_at_origin(self):
        line1 = [0, 0, 10, 10]
        line2 = [0, 10, 10, 0]
        self.assertEqual(line_intersection(line1, line2), [5, 5])

    def test_parallel_lines_no_intersection(self):
        line1 = [0, 0, 10, 10]
        line2 = [0, 1, 10, 11]
        self.assertIsNone(line_intersection(line1, line2))

    def test_lines_intersecting_within_boundaries(self):
        line1 = [0, 0, 10, 10]
        line2 = [5, 0, 5, 10]
        self.assertEqual(line_intersection(line1, line2), [5, 5])

    def test_lines_intersecting_outside_boundaries(self):
        line1 = [0, 0, 5, 5]
        line2 = [6, 6, 10, 10]
        self.assertIsNone(line_intersection(line1, line2))


class CalculateAngleTests(unittest.TestCase):
    def test_perpendicular_lines_angle_90(self):
        line1 = [0, 0, 10, 10]
        line2 = [0, 10, 10, 0]
        self.assertEqual(calculate_angle(line1, line2), 90)

    def test_parallel_lines_angle_0(self):
        line1 = [0, 0, 10, 10]
        line2 = [0, 1, 10, 11]
        self.assertEqual(calculate_angle(line1, line2), 0)

    def test_identical_lines_angle_0(self):
        line1 = [0, 0, 10, 10]
        line2 = [0, 0, 10, 10]
        self.assertEqual(calculate_angle(line1, line2), 0)


class CalculateAnglePointsTests(unittest.TestCase):
    def test_multiple_lines_multiple_intersections(self):
        lines = [[0, 0, 10, 10], [0, 10, 10, 0], [5, 0, 5, 10]]
        result = calculate_angle_points(lines)
        self.assertEqual(len(result), 3)

    def test_parallel_lines_no_intersections(self):
        lines = [[0, 0, 10, 10], [0, 1, 10, 11]]
        result = calculate_angle_points(lines)
        self.assertEqual(len(result), 0)

    def test_angle_as_integer(self):
        line1 = [0, 0, 10, 10]
        line2 = [0, 10, 10, 0]
        self.assertIsInstance(calculate_angle(line1, line2), int)


if __name__ == '__main__':
    unittest.main()
