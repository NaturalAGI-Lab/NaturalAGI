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
    return run_offline_session(
        FIXTURES / "seven_flipped", steps=None, mismatch_threshold=0.35
    )


def test_payload_steps_and_meta(flipped_payload):
    p = flipped_payload
    assert len(p["steps"]) == 3
    assert p["steps"][0]["description"] == "Initial concept"
    assert p["meta"]["verdict"] == "SUSPECT"
    assert p["meta"]["mean_xy_width"] > 0.1
    first = p["steps"][1]
    for key in ("concept_before", "sample", "concept_after"):
        assert "nodes" in first[key] and "links" in first[key]


def test_payload_mismatch_events(flipped_payload):
    merges = [e for e in flipped_payload["events"] if e["type"] == "merge"]
    assert sum(1 for e in merges if e.get("mismatch")) == 2


def test_payload_contains_only_plain_types(flipped_payload):
    _assert_plain(flipped_payload)


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
