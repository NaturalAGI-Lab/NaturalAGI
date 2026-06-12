"""CC-16 regression: debug_mode runs must never delete sample data from Neo4j."""
import logging
from unittest.mock import MagicMock

import networkx as nx

from src.critical_point_concept_service import CriticalPointConceptService


def _tiny_graph(gid: str) -> nx.Graph:
    g = nx.Graph(graph_id=gid)
    g.add_node(0, labels=["Point", "StartPoint"], normalized_x=0.0, normalized_y=0.0)
    g.add_node(1, labels=["Point", "EndPoint"], normalized_x=0.5, normalized_y=0.5)
    g.add_edge(0, 1)
    return g


def _service_with_failing_merge() -> CriticalPointConceptService:
    svc = object.__new__(CriticalPointConceptService)
    svc.logger = logging.getLogger("test_cc16")
    svc.repository = MagicMock()
    svc.repository.get_image_ids_for_session.return_value = ["img_a", "img_b"]
    svc.repository.get_image_graph.side_effect = lambda iid: _tiny_graph(iid)
    svc._determine_start_point = lambda graphs: graphs
    svc._analyze_graph = lambda g: g
    svc.graph_minor_finder = MagicMock()
    svc.graph_minor_finder.find_max_common_minor.side_effect = RuntimeError("boom")
    return svc


def test_debug_mode_never_removes_image_data():
    svc = _service_with_failing_merge()
    result = svc.create_concept_incrementally("s", concept_id="c", debug_mode=True)
    assert result.skipped_images == ["img_b"]
    svc.repository.remove_image_data.assert_not_called()
    svc.repository.save_concept.assert_not_called()


def test_production_mode_still_removes_skipped_image_data():
    svc = _service_with_failing_merge()
    svc.create_concept_incrementally("s", concept_id="c", debug_mode=False)
    removed = [c.args[0] for c in svc.repository.remove_image_data.call_args_list]
    assert "img_b" in removed  # skipped sample removed at raise time (unchanged)
    assert "img_a" in removed  # surviving sample removed at save time (unchanged)
