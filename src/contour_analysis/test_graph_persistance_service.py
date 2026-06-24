import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).parent))

from service.graph_persistance_service import GraphPersistenceService


class _FakeTx:
    """Captures the parameters passed to each tx.run() call."""

    def __init__(self):
        self.calls = []

    def run(self, query, **kwargs):
        self.calls.append((query, kwargs))


def _service():
    return GraphPersistenceService(driver=None)


def _flatten(tx, key):
    return [item for _, kw in tx.calls if key in kw for item in kw[key]]


def test_image_path_persisted_on_point_nodes():
    graph = nx.Graph()
    graph.add_node(1, x=0.0, y=0.0)
    tx = _FakeTx()

    _service()._save_graph(
        tx, graph, "img-1", "7_1", {}, "datasets/mnist_all/7/foo.png"
    )

    nodes = _flatten(tx, "nodes")
    assert nodes[0]["image_path"] == "datasets/mnist_all/7/foo.png"


def test_image_path_persisted_on_vector_edges():
    graph = nx.Graph()
    graph.add_node(1, x=0.0, y=0.0)
    graph.add_node(2, x=1.0, y=1.0)
    graph.add_edge(1, 2, id="vec-1", length=1.41)
    tx = _FakeTx()

    _service()._save_graph(
        tx, graph, "img-1", "7_1", {}, "datasets/mnist_all/7/foo.png"
    )

    edges = _flatten(tx, "edges")
    assert edges[0]["image_path"] == "datasets/mnist_all/7/foo.png"


def test_image_path_defaults_to_none_when_absent():
    graph = nx.Graph()
    graph.add_node(1, x=0.0, y=0.0)
    tx = _FakeTx()

    _service()._save_graph(tx, graph, "img-1", "7_1", {})

    nodes = _flatten(tx, "nodes")
    assert nodes[0]["image_path"] is None
