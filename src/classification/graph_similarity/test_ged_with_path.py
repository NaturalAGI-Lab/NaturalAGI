import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import networkx as nx

from graph_similarity.graph_edit_distance_comparator import GraphEditDistanceComparator


def _graph():
    g = nx.Graph()
    g.add_node(1, labels=["Point", "EndPoint"], normalized_x=0.2, normalized_y=0.3)
    g.add_node(2, labels=["Point", "CornerPoint"], normalized_x=0.6, normalized_y=0.7)
    g.add_edge(1, 2)
    return g


def test_identical_graphs_have_zero_cost_and_full_similarity():
    g1 = _graph()
    g2 = _graph()
    sim, cost, node_path, edge_path = (
        GraphEditDistanceComparator.compare_graphs_ged_with_path(g1, g2, "self", 5.0)
    )
    assert cost == 0.0
    assert sim == 1.0
    assert len(node_path) == 2
