import sys
from pathlib import Path

import pytest

from visualization.formation_runner import run_offline_session

FIXTURES = Path(__file__).parent.parent / "probes" / "repro" / "sample_data"

PLAIN = (dict, list, str, int, float, bool, type(None))


def _assert_plain(obj, path="payload"):
    assert isinstance(obj, PLAIN), f"{path} has non-plain type {type(obj)}"
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, (str, int)), f"{path} key {k!r} type {type(k)}"
            _assert_plain(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_plain(v, f"{path}[{i}]")


@pytest.fixture(scope="module")
def flipped_payload():
    return run_offline_session(FIXTURES / "seven_flipped", steps=None)


def test_payload_steps_and_meta(flipped_payload):
    p = flipped_payload
    assert len(p["steps"]) == 3
    assert p["steps"][0]["description"] == "Initial concept"
    # verdict is now width-only (the mismatch-count input was removed); this
    # fixture's mean width is below SUSPECT_WIDTH, so it reads CLEAN.
    assert p["meta"]["verdict"] == "CLEAN"
    assert p["meta"]["mean_xy_width"] > 0.1
    first = p["steps"][1]
    for key in ("concept_before", "sample", "concept_after"):
        assert "nodes" in first[key] and "links" in first[key]


def test_merge_events_have_no_mismatch_flag(flipped_payload):
    # the threshold-based "potential mismatch" flag is fully removed; merges
    # record only the actual match and its (factual) distance.
    merges = [e for e in flipped_payload["events"] if e["type"] == "merge"]
    assert merges
    assert all("mismatch" not in e for e in merges)
    assert all("distance" in e for e in merges)


def test_payload_contains_only_plain_types(flipped_payload):
    _assert_plain(flipped_payload)


def test_build_payload_marks_error_and_flags_exception_step():
    import networkx as nx

    from src.model.concept_result import ConceptFormationStep, ConceptResult
    from visualization.formation_runner import build_payload

    concept = nx.Graph()
    concept.add_node(0, labels=["Point", "StartPoint"], normalized_x=0.0,
                     normalized_y=0.0)
    image = nx.Graph()
    image.add_node(0, labels=["Point", "CornerPoint"], normalized_x=0.1,
                   normalized_y=0.1)
    steps = [
        ConceptFormationStep(concept, concept, "a", 1, "Initial concept", concept),
        ConceptFormationStep(concept, image, "b", 2,
                             "EXCEPTION at image 2/2 (b): boom", nx.Graph()),
    ]
    result = ConceptResult("c", concept, {"a": concept, "b": image}, steps,
                           is_error=True, error_message="boom")

    class _Recorder:
        events: list = []

        def summary(self) -> dict:
            return {}

    payload = build_payload(result, _Recorder(), {"session_id": "8_1"}, 1.23)

    assert payload["meta"]["is_error"] is True
    assert payload["meta"]["error_message"] == "boom"
    assert payload["meta"]["verdict"] == "ERROR"
    # the failing pair is the last step and is flagged for the UI
    assert payload["steps"][-1]["is_exception"] is True
    assert payload["steps"][-1]["error_message"] == "boom"
    assert payload["steps"][-1]["sample"]["nodes"][0]["id"] == 0
    # earlier successful steps are not flagged
    assert payload["steps"][0]["is_exception"] is False


def test_build_payload_success_has_no_error(flipped_payload):
    assert flipped_payload["meta"]["is_error"] is False
    assert flipped_payload["meta"]["verdict"] in ("CLEAN", "SUSPECT")
    assert all(not s["is_exception"] for s in flipped_payload["steps"])


def test_run_offline_session_enables_capture_failure(monkeypatch):
    import visualization.formation_runner as fr

    captured = {}

    def fake_run_offline(service, image_graphs, steps, step_ref, capture_failure=False):
        captured["capture_failure"] = capture_failure
        return ConceptResultStub()

    class ConceptResultStub:
        concept_graph = __import__("networkx").Graph()
        steps_debug: list = []
        is_error = False
        error_message = None

    monkeypatch.setattr(fr, "_run_offline", fake_run_offline)
    monkeypatch.setattr(fr, "_load_graphs_from_dir", lambda d: {"a": object()})
    monkeypatch.setattr(fr, "_build_offline_service", lambda: object())
    monkeypatch.setattr(fr, "_determine_start_point", lambda g, log: g)
    monkeypatch.setattr(fr, "attach_instrumentation", lambda s, r: [0])

    fr.run_offline_session(FIXTURES / "seven_flipped", None)
    assert captured["capture_failure"] is True


def test_main_writes_error_payload_when_runner_raises(monkeypatch, tmp_path):
    import pickle

    import visualization.formation_runner as fr

    def boom(*a, **k):
        raise RuntimeError("start-point determination failed")

    monkeypatch.setattr(fr, "run_neo4j_session", boom)
    out = tmp_path / "out.pkl"
    monkeypatch.setattr(
        sys, "argv",
        ["formation_runner.py", "--session", "8_1", "--out", str(out)],
    )

    fr.main()  # must NOT raise

    assert out.exists()
    payload = pickle.loads(out.read_bytes())
    assert payload["meta"]["is_error"] is True
    assert "start-point determination failed" in payload["meta"]["error_message"]
    assert payload["steps"] == []


def test_step_advancer_increments_before_delegating():
    from unittest.mock import MagicMock

    from visualization.formation_runner import attach_step_advancer

    service = MagicMock()
    step_ref = [1]
    seen = []

    def fake_merge(*args, **kwargs):
        seen.append(step_ref[0])
        return "merged"

    service.graph_minor_finder.find_max_common_minor = fake_merge
    attach_step_advancer(service, step_ref)
    assert service.graph_minor_finder.find_max_common_minor("g", "h") == "merged"
    assert service.graph_minor_finder.find_max_common_minor("g2", "h2") == "merged"
    assert seen == [2, 3]
    assert step_ref[0] == 3
