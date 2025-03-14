import networkx as nx
import unittest
import logging
import sys
import os

# Adjust import path for the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from networkx_to_neo4j import NetworkxToNeo4j
from concept_creation_repository import ConceptCreationRepository

# Configure logging
logging.basicConfig(level=logging.INFO)


class TestNetworkxToNeo4j(unittest.TestCase):
    def setUp(self):
        self.converter = NetworkxToNeo4j()

    def test_convert_with_range_properties(self):
        """Test that range dictionary properties are correctly converted to strings."""
        # Create a test graph with range properties
        G = nx.Graph()

        # Add a node with a range property
        G.add_node(
            1,
            labels=["Point", "StartPoint"],
            relative_distance={"min": 0.2, "max": 0.3, "type": "range", "center": 0.25},
        )

        # Add another node with a standard property
        G.add_node(2, labels=["Point"], exact_value=42)

        # Add an edge with a range property
        G.add_edge(
            1, 2, strength={"min": 0.5, "max": 0.7, "type": "range", "center": 0.6}
        )

        # Convert the graph
        result = self.converter.convert(G)

        # Check that nodes were converted correctly
        nodes = [item for item in result if item["type"] == "node"]
        self.assertEqual(len(nodes), 2)

        # Find the node with the range property
        start_point_node = next(
            node for node in nodes if "StartPoint" in node["labels"]
        )

        # Check that the range property was converted to a string
        self.assertIsInstance(start_point_node["properties"]["relative_distance"], str)
        self.assertTrue(
            start_point_node["properties"]["relative_distance"].startswith(
                "range(min=0.2,max=0.3"
            )
        )

        # Check that edges were converted correctly
        edges = [item for item in result if item["type"] == "relationship"]
        self.assertEqual(len(edges), 1)

        # Check that the range property in the edge was converted to a string
        self.assertIsInstance(edges[0]["properties"]["strength"], str)
        self.assertTrue(
            edges[0]["properties"]["strength"].startswith("range(min=0.5,max=0.7")
        )

    def test_convert_sets_to_lists(self):
        """Test that the conversion of properties handles sets and other complex types."""
        # Create a repository instance just to test its _convert_sets_to_lists method
        # We're not actually connecting to Neo4j here
        repo = ConceptCreationRepository("bolt://localhost:7687", "neo4j", "password")

        # Test with a range dictionary
        props = {
            "range_prop": {"min": 1, "max": 5, "type": "range", "center": 3},
            "list_with_ranges": [
                {"min": 1, "max": 2, "type": "range", "center": 1.5},
                {"min": 3, "max": 4, "type": "range", "center": 3.5},
            ],
            "set_prop": {1, 2, 3},
            "normal_prop": "hello",
        }

        result = repo._convert_sets_to_lists(props)

        # Check that range dictionaries are converted to strings
        self.assertIsInstance(result["range_prop"], str)
        self.assertTrue(result["range_prop"].startswith("range(min=1,max=5"))

        # Check that ranges in lists are converted to strings
        self.assertIsInstance(result["list_with_ranges"], list)
        self.assertIsInstance(result["list_with_ranges"][0], str)
        self.assertTrue(result["list_with_ranges"][0].startswith("range(min=1,max=2"))

        # Check that sets are converted to lists
        self.assertIsInstance(result["set_prop"], list)
        self.assertEqual(set(result["set_prop"]), {1, 2, 3})

        # Check that normal properties are unchanged
        self.assertEqual(result["normal_prop"], "hello")


if __name__ == "__main__":
    unittest.main()
