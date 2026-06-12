"""
formation_runner.py — run concept formation in a FRESH interpreter and emit a
plain-types payload pickle for the Streamlit app.

Neo4j mode:   python visualization/formation_runner.py --session 7_1 --out out.pkl
Offline mode: python visualization/formation_runner.py \
                  --samples-dir probes/repro/sample_data/seven_flipped --out out.pkl

This module is the ONLY place concept_creator code is imported by the viz tool —
each subprocess run picks up the current source.
"""
import argparse
import json
import os
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

_CC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_CC_DIR))

from probes.instrumentation import FormationRecorder, attach_instrumentation
from probes.probe_concept_formation import (
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


def build_payload(result, recorder, params: dict, duration_s: float) -> dict:
    steps = []
    for st in result.steps_debug:
        steps.append({
            "step": int(st.current_step),
            "description": str(st.current_step_description),
            "image_id": str(st.current_image_id),
            "concept_before": serialize_graph(st.current_concept),
            "sample": serialize_graph(st.current_image),
            "concept_after": serialize_graph(st.resulted_concept),
        })
    summ = recorder.summary()
    mean_xy = _mean_xy_width(result.concept_graph)
    verdict = (
        "CLEAN" if summ["mismatch_merges"] == 0 and mean_xy < SUSPECT_WIDTH else "SUSPECT"
    )
    return {
        "meta": _sanitize({
            "session_id": params.get("session_id", "offline"),
            "params": params,
            "duration_s": round(duration_s, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "mean_xy_width": round(mean_xy, 4),
            "skipped_images": list(result.skipped_images or []),
            "summary": summ,
        }),
        "steps": steps,
        "events": [_sanitize(e) for e in recorder.events],
    }


def run_offline_session(samples_dir: Path, steps, mismatch_threshold: float) -> dict:
    t0 = time.monotonic()
    recorder = ProgressRecorder(mismatch_threshold=mismatch_threshold)
    image_graphs = _load_graphs_from_dir(Path(samples_dir))
    if not image_graphs:
        raise ValueError(f"No JSON graphs found in {samples_dir}")
    service = _build_offline_service()
    step_ref = attach_instrumentation(service, recorder)
    step_ref[0] = 0
    image_graphs = _determine_start_point(image_graphs, logger)
    step_ref[0] = 1
    result = _run_offline(service, image_graphs, steps, step_ref)
    recorder.close()
    params = {
        "session_id": "offline",
        "samples_dir": str(samples_dir),
        "steps": steps,
        "mismatch_threshold": mismatch_threshold,
    }
    return build_payload(result, recorder, params, time.monotonic() - t0)


def run_neo4j_session(session_id: str, steps, mismatch_threshold: float) -> dict:
    from src.critical_point_concept_service import CriticalPointConceptService

    t0 = time.monotonic()
    uri = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "111122223333")

    recorder = ProgressRecorder(mismatch_threshold=mismatch_threshold)
    service = CriticalPointConceptService(uri, user, pwd)
    attach_instrumentation(service, recorder)
    result = service.create_concept_incrementally(
        session_id, concept_id=f"viz_{session_id}", steps=steps, debug_mode=True
    )
    recorder.close()
    params = {
        "session_id": session_id,
        "steps": steps,
        "mismatch_threshold": mismatch_threshold,
    }
    return build_payload(result, recorder, params, time.monotonic() - t0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Concept formation viz runner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--session", help="Neo4j session ID")
    mode.add_argument("--samples-dir", help="Directory of node-link JSON graphs")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--mismatch-threshold", type=float, default=0.35)
    parser.add_argument("--out", required=True, help="Output pickle path")
    args = parser.parse_args()

    if args.session:
        payload = run_neo4j_session(args.session, args.steps, args.mismatch_threshold)
    else:
        payload = run_offline_session(
            Path(args.samples_dir), args.steps, args.mismatch_threshold
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        pickle.dump(payload, fh)
    print(f"DONE steps={len(payload['steps'])} verdict={payload['meta']['verdict']}",
          flush=True)


if __name__ == "__main__":
    main()
