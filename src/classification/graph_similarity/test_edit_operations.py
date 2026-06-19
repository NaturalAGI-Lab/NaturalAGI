import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import networkx as nx

from graph_similarity.graph_edit_distance_comparator import build_edit_operations
from graph_similarity.cost_functions import NodeCost


def _img():
    g = nx.Graph()
    g.add_node("a", labels=["Point", "EndPoint"], normalized_x=0.1)
    g.add_node("b", labels=["Point", "CornerPoint"], normalized_x=0.9)
    g.add_edge("a", "b")
    return g


def _concept():
    g = nx.Graph()
    g.add_node("x", labels=["Point", "EndPoint"], normalized_x=0.1)
    return g


def test_build_edit_operations_classifies_and_costs():
    node_path = [("a", "x"), ("b", None)]
    edge_path = [(("a", "b"), None)]

    ops = build_edit_operations(node_path, edge_path, _img(), _concept())

    by = {(o["op"], o["kind"]): o for o in ops}
    assert by[("MATCH", "node")]["cost"] == NodeCost.NO_COST
    assert by[("MATCH", "node")]["image_ref"] == "a"
    assert by[("MATCH", "node")]["concept_ref"] == "x"
    assert by[("DELETE", "node")]["cost"] == NodeCost.MINOR
    assert by[("DELETE", "node")]["image_ref"] == "b"
    assert by[("DELETE", "edge")]["cost"] == NodeCost.MINOR
