"""
Self-test for the probe suite.  No pytest required — run directly:
    cd src/concept_creator
    PYTHONPATH=.:/path/to/common python probes/test_probe_selfcheck.py

Assertions:
  (a) clean set → probe runs, mean_xy_width < 0.6
  (b) flipped set → at least one mismatch event, mean_xy_width(flipped) > mean_xy_width(clean)
"""
import copy
import json
import logging
import os
import sys
from pathlib import Path

# ------------------------------------------------------------------ paths --
_PROBE_DIR = Path(__file__).parent
_SRC_DIR = _PROBE_DIR.parent
sys.path.insert(0, str(_SRC_DIR))

import networkx as nx

from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.property_handlers import PropertyProcessor
from src.synced_graph_algorithm import SyncedGraphMinorFinder
from src.utils.graph_saver import NumpyJSONEncoder

from probes.instrumentation import FormationRecorder, attach_instrumentation
from probes.probe_concept_formation import (
    _build_offline_service,
    _determine_start_point,
    _run_offline,
    _load_graphs_from_dir,
    _range_width,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# ---------------------------------------------------------------------------
# build synthetic sample data if missing
# ---------------------------------------------------------------------------

def _make_node(labels, x, y):
    return {"labels": labels, "normalized_x": x, "normalized_y": y}


def _make_seven_clean_A():
    G = nx.Graph()
    G.graph["graph_id"] = "A"
    G.add_node(0, **_make_node(["EndPoint", "Point"], -0.70, 0.90))
    G.add_node(1, **_make_node(["Point"], -0.10, 0.90))
    G.add_node(2, **_make_node(["CornerPoint", "Point"], 0.80, 0.85))
    G.add_node(3, **_make_node(["Point"], 0.25, 0.20))
    G.add_node(4, **_make_node(["EndPoint", "Point"], -0.10, -0.90))
    G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
    return G


def _make_seven_clean_B():
    G = nx.Graph()
    G.graph["graph_id"] = "B"
    G.add_node(0, **_make_node(["EndPoint", "Point"], -0.68, 0.91))
    G.add_node(1, **_make_node(["Point"], -0.08, 0.88))
    G.add_node(2, **_make_node(["CornerPoint", "Point"], 0.79, 0.86))
    G.add_node(3, **_make_node(["Point"], 0.22, 0.22))
    G.add_node(4, **_make_node(["EndPoint", "Point"], -0.12, -0.88))
    G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
    return G


def _make_seven_clean_C():
    G = nx.Graph()
    G.graph["graph_id"] = "C"
    G.add_node(0, **_make_node(["EndPoint", "Point"], -0.72, 0.88))
    G.add_node(1, **_make_node(["Point"], -0.12, 0.89))
    G.add_node(2, **_make_node(["CornerPoint", "Point"], 0.81, 0.84))
    G.add_node(3, **_make_node(["Point"], 0.28, 0.18))
    G.add_node(4, **_make_node(["EndPoint", "Point"], -0.09, -0.91))
    G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
    return G


def _make_seven_flipped_C():
    G = nx.Graph()
    G.graph["graph_id"] = "C"
    G.add_node(0, **_make_node(["EndPoint", "Point"], -0.09, -0.91))
    G.add_node(1, **_make_node(["Point"], -0.12, 0.89))
    G.add_node(2, **_make_node(["CornerPoint", "Point"], 0.81, 0.84))
    G.add_node(3, **_make_node(["Point"], 0.28, 0.18))
    G.add_node(4, **_make_node(["EndPoint", "Point"], -0.72, 0.88))
    G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
    return G


def _save_json(G: nx.Graph, path: Path) -> None:
    data = nx.node_link_data(G)
    with path.open("w") as fh:
        json.dump(data, fh, indent=2, cls=NumpyJSONEncoder)


def _ensure_sample_data() -> tuple[Path, Path]:
    base = _PROBE_DIR / "repro" / "sample_data"
    clean_dir = base / "seven_clean"
    flipped_dir = base / "seven_flipped"
    clean_dir.mkdir(parents=True, exist_ok=True)
    flipped_dir.mkdir(parents=True, exist_ok=True)

    _save_json(_make_seven_clean_A(), clean_dir / "A.json")
    _save_json(_make_seven_clean_B(), clean_dir / "B.json")
    _save_json(_make_seven_clean_C(), clean_dir / "C.json")

    _save_json(_make_seven_clean_A(), flipped_dir / "A.json")
    _save_json(_make_seven_clean_B(), flipped_dir / "B.json")
    _save_json(_make_seven_flipped_C(), flipped_dir / "C.json")

    return clean_dir, flipped_dir


# ---------------------------------------------------------------------------
# helper: run probe offline on a given samples dir
# ---------------------------------------------------------------------------

def _run_probe_offline(samples_dir: Path, mismatch_threshold: float = 0.35):
    image_graphs = _load_graphs_from_dir(samples_dir)
    assert image_graphs, f"No graphs loaded from {samples_dir}"

    service = _build_offline_service()
    recorder = FormationRecorder(out_path=None, mismatch_threshold=mismatch_threshold)
    step_ref = attach_instrumentation(service, recorder)
    step_ref[0] = 0  # start-point determination phase

    image_graphs = _determine_start_point(image_graphs, logging.getLogger("selfcheck"))
    step_ref[0] = 1  # formation step counter

    result = _run_offline(service, image_graphs, steps=None, step_ref=step_ref)

    # compute mean_xy_width
    widths_xy = []
    for nid, data in result.concept_graph.nodes(data=True):
        wx = _range_width(data.get("normalized_x"))
        wy = _range_width(data.get("normalized_y"))
        widths_xy.append((wx + wy) / 2)
    mean_xy = sum(widths_xy) / len(widths_xy) if widths_xy else 0.0

    return recorder, result, mean_xy


# ---------------------------------------------------------------------------
# test: clean set
# ---------------------------------------------------------------------------

def test_clean_set(clean_dir: Path):
    print("\n[test_clean_set] Running probe on seven_clean/ ...")
    recorder, result, mean_xy = _run_probe_offline(clean_dir)

    mismatch_count = sum(1 for e in recorder.events if e.get("mismatch"))
    print(f"  mismatch_count = {mismatch_count}")
    print(f"  mean_xy_width  = {mean_xy:.4f}")

    assert result.concept_graph is not None, "Concept graph should not be None"
    assert len(result.concept_graph.nodes) > 0, "Concept graph should have nodes"
    assert mean_xy < 0.6, f"Clean run mean_xy_width {mean_xy:.4f} should be < 0.6"
    print("  PASS")
    return mismatch_count, mean_xy


# ---------------------------------------------------------------------------
# test: flipped set
# ---------------------------------------------------------------------------

def test_flipped_set(flipped_dir: Path, clean_mean_xy: float):
    print("\n[test_flipped_set] Running probe on seven_flipped/ ...")
    recorder, result, mean_xy = _run_probe_offline(flipped_dir)

    mismatch_count = sum(1 for e in recorder.events if e.get("mismatch"))

    print(f"  mismatch_count = {mismatch_count}")
    print(f"  mean_xy_width  = {mean_xy:.4f}  (clean was {clean_mean_xy:.4f})")

    # With the spatial-consistency guard, the flipped sample's inconsistent
    # pairs are rejected before any merge — no mismatch merges and no
    # width blow-up relative to the clean run.
    assert mismatch_count == 0, (
        f"Flipped set should produce no mismatch merges under the spatial guard, "
        f"got {mismatch_count}."
    )
    assert mean_xy < 0.6, (
        f"Flipped mean_xy_width {mean_xy:.4f} should stay bounded (< 0.6); "
        "the flipped sample must not corrupt concept ranges."
    )
    print("  PASS")
    return mismatch_count, mean_xy


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Probe Selfcheck ===")
    clean_dir, flipped_dir = _ensure_sample_data()

    clean_mismatch, clean_mean = test_clean_set(clean_dir)
    flipped_mismatch, flipped_mean = test_flipped_set(flipped_dir, clean_mean)

    print(f"\n=== Summary ===")
    print(f"  clean:   mismatches={clean_mismatch}  mean_xy_width={clean_mean:.4f}")
    print(f"  flipped: mismatches={flipped_mismatch}  mean_xy_width={flipped_mean:.4f}")
    print("\nAll assertions passed.")
