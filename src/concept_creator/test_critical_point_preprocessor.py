import unittest
import networkx as nx
from concept_creator.critical_point_preprocessor import CriticalPointPreprocessor


class TestCriticalPointPreprocessor(unittest.TestCase):

    def setUp(self):
        self.preprocessor = CriticalPointPreprocessor()

    def test_preprocess_graphs_with_differing_critical_points(self):
        """Test preprocessing graphs with different numbers of critical points"""

        # Create two test graphs
        # Graph 1: StartPoint, IntersectionPoint, CornerPoint, 2 EndPoints
        graph1 = nx.Graph()
        graph1.add_node("start", labels=["Point", "StartPoint"])
        graph1.add_node("intersection", labels=["Point", "IntersectionPoint"])
        graph1.add_node("corner", labels=["Point", "CornerPoint"])
        graph1.add_node("end1", labels=["Point", "EndPoint"])
        graph1.add_node("end2", labels=["Point", "EndPoint"])

        # Graph 2: StartPoint, IntersectionPoint, 2 EndPoints (no CornerPoint)
        graph2 = nx.Graph()
        graph2.add_node("start2", labels=["Point", "StartPoint"])
        graph2.add_node("intersection2", labels=["Point", "IntersectionPoint"])
        graph2.add_node("end3", labels=["Point", "EndPoint"])
        graph2.add_node("end4", labels=["Point", "EndPoint"])

        # Process the graphs
        processed_g1, processed_g2 = self.preprocessor.preprocess_graphs(graph1, graph2)

        # Check that the number of each type of critical point is now the same
        critical_points1 = self.preprocessor._identify_critical_points(processed_g1)
        critical_points2 = self.preprocessor._identify_critical_points(processed_g2)

        count1 = {cp_type: len(points) for cp_type, points in critical_points1.items()}
        count2 = {cp_type: len(points) for cp_type, points in critical_points2.items()}

        # The CornerPoint should have been reduced to a Point in graph1
        self.assertEqual(
            count1["CornerPoint"], 0, "CornerPoint should be reduced to Point"
        )
        self.assertEqual(
            count1["StartPoint"], 1, "StartPoint count should be unchanged"
        )
        self.assertEqual(count1["EndPoint"], 2, "EndPoint count should be unchanged")
        self.assertEqual(
            count1["IntersectionPoint"],
            1,
            "IntersectionPoint count should be unchanged",
        )

        # Graph2 should be unchanged
        self.assertEqual(
            count2["CornerPoint"], 0, "Graph2 CornerPoint count should be unchanged"
        )
        self.assertEqual(
            count2["StartPoint"], 1, "Graph2 StartPoint count should be unchanged"
        )
        self.assertEqual(
            count2["EndPoint"], 2, "Graph2 EndPoint count should be unchanged"
        )
        self.assertEqual(
            count2["IntersectionPoint"],
            1,
            "Graph2 IntersectionPoint count should be unchanged",
        )

    def test_preprocess_graphs_with_same_critical_points(self):
        """Test preprocessing graphs with same number of critical points"""

        # Create two test graphs with the same number of critical points
        graph1 = nx.Graph()
        graph1.add_node("start", labels=["Point", "StartPoint"])
        graph1.add_node("intersection", labels=["Point", "IntersectionPoint"])
        graph1.add_node("end1", labels=["Point", "EndPoint"])

        graph2 = nx.Graph()
        graph2.add_node("start2", labels=["Point", "StartPoint"])
        graph2.add_node("intersection2", labels=["Point", "IntersectionPoint"])
        graph2.add_node("end2", labels=["Point", "EndPoint"])

        # Process the graphs
        processed_g1, processed_g2 = self.preprocessor.preprocess_graphs(graph1, graph2)

        # Both graphs should be unchanged
        critical_points1 = self.preprocessor._identify_critical_points(processed_g1)
        critical_points2 = self.preprocessor._identify_critical_points(processed_g2)

        count1 = {cp_type: len(points) for cp_type, points in critical_points1.items()}
        count2 = {cp_type: len(points) for cp_type, points in critical_points2.items()}

        self.assertEqual(count1["StartPoint"], 1)
        self.assertEqual(count1["IntersectionPoint"], 1)
        self.assertEqual(count1["EndPoint"], 1)

        self.assertEqual(count2["StartPoint"], 1)
        self.assertEqual(count2["IntersectionPoint"], 1)
        self.assertEqual(count2["EndPoint"], 1)

    def test_preprocess_graphs_with_different_critical_point_types(self):
        """Test preprocessing graphs with same number but different types of critical points"""

        # Graph 1: StartPoint, IntersectionPoint, EndPoint
        graph1 = nx.Graph()
        graph1.add_node("start", labels=["Point", "StartPoint"])
        graph1.add_node("intersection", labels=["Point", "IntersectionPoint"])
        graph1.add_node("end1", labels=["Point", "EndPoint"])

        # Graph 2: StartPoint, CornerPoint, EndPoint
        graph2 = nx.Graph()
        graph2.add_node("start2", labels=["Point", "StartPoint"])
        graph2.add_node("corner", labels=["Point", "CornerPoint"])
        graph2.add_node("end2", labels=["Point", "EndPoint"])

        # Process the graphs
        processed_g1, processed_g2 = self.preprocessor.preprocess_graphs(graph1, graph2)

        # Check that types are aligned
        critical_points1 = self.preprocessor._identify_critical_points(processed_g1)
        critical_points2 = self.preprocessor._identify_critical_points(processed_g2)

        # Should have transformed IntersectionPoint → CornerPoint or vice versa
        self.assertEqual(
            len(critical_points1["IntersectionPoint"]),
            len(critical_points2["IntersectionPoint"]),
        )
        self.assertEqual(
            len(critical_points1["CornerPoint"]), len(critical_points2["CornerPoint"])
        )


if __name__ == "__main__":
    unittest.main()
