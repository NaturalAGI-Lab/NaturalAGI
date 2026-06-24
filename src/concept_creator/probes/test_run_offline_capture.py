"""Offline formation must capture the failing pair when capture_failure=True,
mirroring CriticalPointConceptService.create_concept_incrementally.
"""
from unittest.mock import MagicMock

import networkx as nx
import pytest

from probes import probe_concept_formation as pcf


def _tiny_graph(gid: str) -> nx.Graph:
    g = nx.Graph(graph_id=gid)
    g.add_node(0, labels=["Point", "StartPoint"], normalized_x=0.0, normalized_y=0.0)
    g.add_node(1, labels=["Point", "EndPoint"], normalized_x=0.5, normalized_y=0.5)
    g.add_edge(0, 1)
    return g


def _service_with_side_effect(side_effect):
    svc = MagicMock()
    svc.graph_minor_finder.find_max_common_minor.side_effect = side_effect
    return svc


def test_run_offline_capture_failure_returns_partial(monkeypatch):
    # skip the heavy visitor pass; identity keeps the tiny graphs intact
    monkeypatch.setattr(pcf, "_analyze_graph", lambda g: g)
    image_graphs = {"a": _tiny_graph("a"), "b": _tiny_graph("b")}
    svc = _service_with_side_effect(RuntimeError("boom"))

    result = pcf._run_offline(svc, image_graphs, None, [1], capture_failure=True)

    assert result.is_error is True
    assert "boom" in result.error_message
    last = result.steps_debug[-1]
    assert last.current_image_id == "b"
    assert "EXCEPTION" in last.current_step_description.upper()


def test_run_offline_default_still_propagates(monkeypatch):
    monkeypatch.setattr(pcf, "_analyze_graph", lambda g: g)
    image_graphs = {"a": _tiny_graph("a"), "b": _tiny_graph("b")}
    svc = _service_with_side_effect(RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        pcf._run_offline(svc, image_graphs, None, [1])
