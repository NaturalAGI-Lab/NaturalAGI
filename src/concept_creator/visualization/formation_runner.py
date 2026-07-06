"""
formation_runner.py — run concept formation in a FRESH interpreter and emit a
plain-types payload pickle for the Streamlit app.

Neo4j mode:   python visualization/formation_runner.py --session 7_1 --out out.pkl
Offline mode: python visualization/formation_runner.py \
                  --samples-dir /path/to/graph/json/dir --out out.pkl

This module is the ONLY place concept_creator code is imported by the viz tool —
each subprocess run picks up the current source.
"""
import argparse
import json
import os
import pickle
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

_CC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_CC_DIR))

from instrumentation import FormationRecorder, attach_instrumentation
from probe_concept_formation import (
    _build_offline_service,
    _determine_start_point,
    _load_graphs_from_dir,
    _range_width,
    _run_offline,
)
import logging

logger = logging.getLogger("formation_runner")

SUSPECT_WIDTH = 0.6


class ProgressRecorder(FormationRecorder):
    """Prints PROGRESS lines so the parent app can show live status."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_step = None

    def emit(self, event: dict) -> None:
        step = event.get("step")
        if step is not None and step != self._last_step:
            self._last_step = step
            print(f"PROGRESS step={step}", flush=True)
        super().emit(event)


def _plain(obj):
    try:
        return float(obj)
    except (TypeError, ValueError):
        return str(obj)


def _sanitize(obj):
    return json.loads(json.dumps(obj, default=_plain))


def serialize_graph(g: nx.Graph) -> dict:
    return _sanitize(nx.node_link_data(g, edges="links"))


def _mean_xy_width(concept: nx.Graph) -> float:
    widths = [
        (_range_width(d.get("normalized_x")) + _range_width(d.get("normalized_y"))) / 2
        for _, d in concept.nodes(data=True)
    ]
    return sum(widths) / len(widths) if widths else 0.0


def attach_step_advancer(service, step_ref: list[int]) -> None:
    """Neo4j mode has no _run_offline loop; tick the step counter per merge call."""
    original = service.graph_minor_finder.find_max_common_minor

    def advancing_find_max_common_minor(*args, **kwargs):
        step_ref[0] += 1
        return original(*args, **kwargs)

    service.graph_minor_finder.find_max_common_minor = advancing_find_max_common_minor


def build_payload(result, recorder, params: dict, duration_s: float) -> dict:
    is_error = bool(getattr(result, "is_error", False))
    error_message = getattr(result, "error_message", None)
    last_idx = len(result.steps_debug) - 1
    steps = []
    for idx, st in enumerate(result.steps_debug):
        # the terminal step of a failed run holds the concept-so-far + the image
        # that broke formation; flag it so the UI can label the empty result panel
        is_exception = is_error and idx == last_idx
        step = {
            "step": int(st.current_step),
            "description": str(st.current_step_description),
            "image_id": str(st.current_image_id),
            "concept_before": serialize_graph(st.current_concept),
            "sample": serialize_graph(st.current_image),
            "concept_after": serialize_graph(st.resulted_concept),
            "is_exception": is_exception,
        }
        if is_exception:
            step["error_message"] = error_message
        steps.append(step)
    summ = recorder.summary()
    mean_xy = _mean_xy_width(result.concept_graph)
    if is_error:
        verdict = "ERROR"
    elif mean_xy < SUSPECT_WIDTH:
        verdict = "CLEAN"
    else:
        verdict = "SUSPECT"
    return {
        "meta": _sanitize({
            "session_id": params.get("session_id", "offline"),
            "params": params,
            "duration_s": round(duration_s, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "is_error": is_error,
            "error_message": error_message,
            "mean_xy_width": round(mean_xy, 4),
            "summary": summ,
        }),
        "steps": steps,
        "events": [_sanitize(e) for e in recorder.events],
    }


def run_offline_session(samples_dir: Path, steps) -> dict:
    t0 = time.monotonic()
    recorder = ProgressRecorder()
    image_graphs = _load_graphs_from_dir(Path(samples_dir))
    if not image_graphs:
        raise ValueError(f"No JSON graphs found in {samples_dir}")
    service = _build_offline_service()
    step_ref = attach_instrumentation(service, recorder)
    step_ref[0] = 0
    image_graphs = _determine_start_point(image_graphs, logger)
    step_ref[0] = 1
    result = _run_offline(service, image_graphs, steps, step_ref,
                          capture_failure=True)
    recorder.close()
    params = {
        "session_id": "offline",
        "samples_dir": str(samples_dir),
        "steps": steps,
    }
    return build_payload(result, recorder, params, time.monotonic() - t0)


def run_neo4j_session(session_id: str, steps) -> dict:
    from src.critical_point_concept_service import CriticalPointConceptService

    t0 = time.monotonic()
    uri = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "111122223333")

    recorder = ProgressRecorder()
    service = CriticalPointConceptService(uri, user, pwd)
    step_ref = attach_instrumentation(service, recorder)
    attach_step_advancer(service, step_ref)
    result = service.create_concept_incrementally(
        session_id, concept_id=f"viz_{session_id}", steps=steps, debug_mode=True,
        capture_failure=True,
    )
    recorder.close()
    params = {
        "session_id": session_id,
        "steps": steps,
    }
    return build_payload(result, recorder, params, time.monotonic() - t0)


def _error_payload(params: dict, exc: Exception, duration_s: float) -> dict:
    """Minimal payload for failures that escape the in-loop capture (e.g. start
    point determination), so the app can still show the error instead of a bare
    'Runner failed'."""
    return {
        "meta": _sanitize({
            "session_id": params.get("session_id", "offline"),
            "params": params,
            "duration_s": round(duration_s, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verdict": "ERROR",
            "is_error": True,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "mean_xy_width": 0.0,
            "summary": {},
        }),
        "steps": [],
        "events": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Concept formation viz runner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--session", help="Neo4j session ID")
    mode.add_argument("--samples-dir", help="Directory of node-link JSON graphs")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--out", required=True, help="Output pickle path")
    args = parser.parse_args()

    params = {
        "session_id": args.session or "offline",
        "samples_dir": args.samples_dir,
        "steps": args.steps,
    }
    t0 = time.monotonic()
    try:
        if args.session:
            payload = run_neo4j_session(args.session, args.steps)
        else:
            payload = run_offline_session(Path(args.samples_dir), args.steps)
    except Exception as exc:  # never leave the app with no payload to render
        payload = _error_payload(params, exc, time.monotonic() - t0)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        pickle.dump(payload, fh)
    print(f"DONE steps={len(payload['steps'])} verdict={payload['meta']['verdict']}",
          flush=True)


if __name__ == "__main__":
    main()
