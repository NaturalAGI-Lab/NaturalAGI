"""CC-16 regression: debug_mode runs must never delete sample data from Neo4j.

Skip-on-error was removed (every training image must contribute): a failing
merge now propagates instead of dropping the image, and no image data may be
removed when formation fails.
"""
import logging
from unittest.mock import MagicMock

import networkx as nx
import pytest

from src.critical_point_concept_service import CriticalPointConceptService


def _tiny_graph(gid: str) -> nx.Graph:
    g = nx.Graph(graph_id=gid)
    g.add_node(0, labels=["Point", "StartPoint"], normalized_x=0.0, normalized_y=0.0)
    g.add_node(1, labels=["Point", "EndPoint"], normalized_x=0.5, normalized_y=0.5)
    g.add_edge(0, 1)
    return g


def _service_with_minor_finder(side_effect) -> CriticalPointConceptService:
    svc = object.__new__(CriticalPointConceptService)
    svc.logger = logging.getLogger("test_cc16")
    svc.repository = MagicMock()
    svc.repository.get_image_ids_for_session.return_value = ["img_a", "img_b"]
    svc.repository.get_image_graph.side_effect = lambda iid: _tiny_graph(iid)
    svc._determine_start_point = lambda graphs: graphs
    svc._analyze_graph = lambda g: g
    svc.graph_minor_finder = MagicMock()
    svc.graph_minor_finder.find_max_common_minor.side_effect = side_effect
    return svc


def test_merge_error_propagates_and_debug_mode_never_removes_image_data():
    svc = _service_with_minor_finder(RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        svc.create_concept_incrementally("s", concept_id="c", debug_mode=True)
    svc.repository.remove_image_data.assert_not_called()
    svc.repository.save_concept.assert_not_called()


def test_merge_error_in_production_mode_removes_nothing():
    svc = _service_with_minor_finder(RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        svc.create_concept_incrementally("s", concept_id="c", debug_mode=False)
    svc.repository.remove_image_data.assert_not_called()
    svc.repository.save_concept.assert_not_called()


def test_empty_common_minor_raises():
    svc = _service_with_minor_finder(lambda *a, **k: nx.Graph())
    with pytest.raises(ValueError, match="img_b"):
        svc.create_concept_incrementally("s", concept_id="c", debug_mode=True)
    svc.repository.remove_image_data.assert_not_called()


def test_successful_run_saves_concept_and_removes_all_image_data():
    svc = _service_with_minor_finder(lambda *a, **k: _tiny_graph("minor"))
    svc.create_concept_incrementally("s", concept_id="c", debug_mode=False)
    svc.repository.save_concept.assert_called_once()
    removed = [c.args[0] for c in svc.repository.remove_image_data.call_args_list]
    assert removed == ["img_a", "img_b"]


def test_capture_failure_returns_partial_result_instead_of_raising():
    svc = _service_with_minor_finder(RuntimeError("boom"))
    result = svc.create_concept_incrementally(
        "s", concept_id="c", debug_mode=True, capture_failure=True
    )
    assert result.is_error is True
    assert "boom" in result.error_message
    # last step is the failing pair: the image that triggered the exception
    last = result.steps_debug[-1]
    assert last.current_image_id == "img_b"
    assert last.current_image.number_of_nodes() == 2  # the failing image graph
    # never persists or deletes on failure (CC-16 invariant still holds)
    svc.repository.save_concept.assert_not_called()
    svc.repository.remove_image_data.assert_not_called()


def test_capture_failure_keeps_successful_steps_before_the_exception():
    # img_a = initial concept (step 1); img_b raises at step 2.
    svc = _service_with_minor_finder(RuntimeError("boom"))
    result = svc.create_concept_incrementally(
        "s", concept_id="c", debug_mode=True, capture_failure=True
    )
    steps = result.steps_debug
    assert [s.current_step for s in steps] == [1, 2]
    assert steps[0].current_step_description == "Initial concept"
    assert "EXCEPTION" in steps[-1].current_step_description.upper()


def test_capture_failure_false_still_propagates():
    svc = _service_with_minor_finder(RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        svc.create_concept_incrementally(
            "s", concept_id="c", debug_mode=True, capture_failure=False
        )
