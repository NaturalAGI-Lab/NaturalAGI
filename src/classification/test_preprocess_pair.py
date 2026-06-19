import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import networkx as nx

from concept_minor_classifier import ConceptMinorClassifier
from models import ClassificationResult


def test_check_single_concept_uses_preprocess_pair(monkeypatch):
    clf = ConceptMinorClassifier()

    sentinel_img = nx.Graph()
    sentinel_img.add_node(1, labels=["Point"])
    sentinel_con = nx.Graph()
    sentinel_con.add_node(1, labels=["Point"])

    monkeypatch.setattr(clf, "preprocess_pair",
                        lambda image_graph, concept_graph: (sentinel_img, sentinel_con))

    captured = {}

    def fake_compare(image_graph, concept_graph, concept_name):
        captured["image"] = image_graph
        captured["concept"] = concept_graph
        return 0.5

    monkeypatch.setattr(clf.comparator, "compare", fake_compare)

    result = clf.check_single_concept(nx.Graph(), "7_1", nx.Graph())

    assert isinstance(result, ClassificationResult)
    assert captured["image"] is sentinel_img
    assert captured["concept"] is sentinel_con
