from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parent / "formation_viz_app.py"

_G = {
    "directed": False, "multigraph": False, "graph": {},
    "nodes": [{"id": 0, "labels": ["Point", "StartPoint"],
               "normalized_x": 0.1, "normalized_y": 0.2}],
    "links": [],
}
_EMPTY = {"directed": False, "multigraph": False, "graph": {},
          "nodes": [], "links": []}


def _error_payload() -> dict:
    return {
        "meta": {
            "session_id": "8_1", "params": {}, "duration_s": 1.0,
            "created_at": "2026-06-18T00:00:00+00:00", "verdict": "ERROR",
            "is_error": True,
            "error_message": "Reached maximum reduction iterations, stopping",
            "mean_xy_width": 0.0, "summary": {"total_merges": 0},
        },
        "steps": [
            {"step": 1, "description": "Initial concept", "image_id": "a",
             "concept_before": _G, "sample": _G, "concept_after": _G,
             "is_exception": False},
            {"step": 2, "description": "EXCEPTION at image 2/2 (b): boom",
             "image_id": "b", "concept_before": _G, "sample": _G,
             "concept_after": _EMPTY, "is_exception": True,
             "error_message": "Reached maximum reduction iterations, stopping"},
        ],
        "events": [],
    }


def test_app_renders_without_exception():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.run()
    assert not at.exception


def test_app_renders_error_payload_with_no_steps():
    # catch-all failures (e.g. start-point determination) produce an empty
    # steps list; the app must show the error, not crash on step_values[0].
    at = AppTest.from_file(str(APP), default_timeout=30)
    payload = _error_payload()
    payload["steps"] = []
    at.session_state["payload"] = payload
    at.run()
    assert not at.exception
    error_texts = [e.value for e in at.error]
    assert any("Reached maximum reduction iterations" in t for t in error_texts)


def test_app_renders_error_payload_with_banner_and_all_steps():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["payload"] = _error_payload()
    at.run()
    # the empty final concept (exception step) must not crash the inspector tab
    assert not at.exception
    # an error banner names the failure
    error_texts = [e.value for e in at.error]
    assert any("Reached maximum reduction iterations" in t for t in error_texts)
