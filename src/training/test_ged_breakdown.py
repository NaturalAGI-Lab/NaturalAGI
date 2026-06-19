import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import networkx as nx

import ged_breakdown


def _node_graph(n):
    g = nx.Graph()
    for i in range(1, n + 1):
        g.add_node(i, labels=["Point", "EndPoint"],
                   normalized_x=0.1 * i, normalized_y=0.2 * i)
    if n >= 2:
        g.add_edge(1, 2)
    return g


def test_expected_concepts_filters_sorts_annotates():
    all_ids = ["3_1", "7_1", "7_2", "9_2"]
    results = [
        {"concept_id": "7_1", "similarity": 0.67},
        {"concept_id": "3_1", "similarity": 0.74},
    ]
    rows = ged_breakdown.expected_concepts(all_ids, results, "7")
    assert [r["concept_id"] for r in rows] == ["7_1", "7_2"]
    assert rows[0]["similarity"] == 0.67   # scored first
    assert rows[1]["similarity"] is None   # 7_2 pre-filtered


def test_get_image_graph_if_present_returns_none_on_empty(monkeypatch):
    monkeypatch.setattr(ged_breakdown, "ImageRepository",
                        lambda driver: type("R", (), {"get_image_graph": lambda self, i: nx.Graph()})())
    assert ged_breakdown.get_image_graph_if_present(None, "img1") is None


def test_get_concept_graph_delegates_to_repo(monkeypatch):
    sentinel = nx.Graph()
    sentinel.add_node(1)
    fake_repo = type("R", (), {
        "get_concept_graph": lambda self, cid: sentinel,
    })
    monkeypatch.setattr(ged_breakdown, "ConceptRepository", lambda driver: fake_repo())
    result = ged_breakdown.get_concept_graph(None, "1_1")
    assert result is sentinel


def test_run_ged_breakdown_returns_payload():
    out = ged_breakdown._run_ged_breakdown(_node_graph(2), _node_graph(2), "7_1", 5.0)
    assert set(out) == {"image_nodelink", "concept_nodelink", "edit_ops",
                        "cost", "n1", "n2", "similarity"}
    assert "nodes" in out["image_nodelink"] and "links" in out["image_nodelink"]
    assert 0.0 <= out["similarity"] <= 1.0
