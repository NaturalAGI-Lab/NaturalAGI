from typing import List
import unittest
import networkx as nx
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from graph_minor_finder import GraphMinorFinder
from utils import load_graphs_from_file, find_start_point

class TestConceptCreator(unittest.TestCase):
    """Unit tests for the ConceptCreator class."""

    def setUp(self):
        self.concept_creator = GraphMinorFinder()

    def test_concept_creator_one_one(self):
        """Test that the ConceptCreator initializes correctly."""
        # Test initialization of ConceptCreator
        graphs = load_graphs_from_file(
            os.path.join(os.path.dirname(__file__), "data", "1_1.json")
        )
        concept_graph = self.concept_creator.find_max_common_minor(graphs[0], graphs[1])
        assert len(concept_graph.nodes) == 5
        assert len(concept_graph.edges) == 4
        start_point = find_start_point(concept_graph)
        assert start_point is not None
        print(start_point)


if __name__ == "__main__":
    unittest.main()
