"""Offline concept-formation lab: export graphs from Neo4j, run the probe CLI.

The probe (`src/concept_creator/visualization/probe_concept_formation.py`) runs
the production formation code in-process without persisting anything. Training
sessions are consumed (deleted) by successful concept creation, so sample graphs
must be re-ingested through the pipeline before session exports (see
`sessions_status` / `ingest_session`).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import networkx as nx

from . import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, REPO
from .infra import driver

_PROBE = REPO / "src" / "concept_creator" / "visualization" / "probe_concept_formation.py"
SAMPLES_ROOT = REPO / "src" / "training" / "training_results" / "formation_samples"
PROBE_OUT_ROOT = REPO / "src" / "training" / "training_results" / "formation_probes"

ALL_CONCEPTS = ["0_1", "1_1", "1_3", "2_1", "2_2", "3_1", "4_1", "4_2",
                "5_1", "6_1", "7_1", "8_1", "9_2"]


def _json_default(o):
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    try:
        return float(o)
    except (TypeError, ValueError):
        return str(o)


def _write_graph(g: nx.Graph, path: Path) -> None:
    data = nx.node_link_data(g, edges="edges")
    path.write_text(json.dumps(data, default=_json_default))


def export_images(image_ids: list[str], out_dir: Path) -> Path:
    """Export image graphs (contour-analysis output) as node-link JSONs."""
    import ged_breakdown

    out_dir.mkdir(parents=True, exist_ok=True)
    exported = 0
    for image_id in image_ids:
        g = ged_breakdown.get_image_graph_if_present(driver(), image_id)
        if g is None:
            print(f"  skip {image_id}: not in Neo4j")
            continue
        _write_graph(g, out_dir / f"{image_id}.json")
        exported += 1
    print(f"exported {exported}/{len(image_ids)} graphs to {out_dir}")
    return out_dir


def session_image_ids(session_id: str) -> list[str]:
    with driver().session() as s:
        result = s.run(
            "MATCH (n {session_id: $sid}) WHERE n.image_id IS NOT NULL "
            "RETURN DISTINCT n.image_id AS iid ORDER BY iid",
            sid=session_id,
        )
        return [r["iid"] for r in result]


def export_session_graphs(session_id: str, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or (SAMPLES_ROOT / session_id)
    ids = session_image_ids(session_id)
    if not ids:
        raise RuntimeError(
            f"Session '{session_id}' has no image graphs in Neo4j. "
            f"Re-ingest first: ingest_session(...) (додатковий, неруйнівний крок)."
        )
    return export_images(ids, out_dir)


def sessions_status() -> dict:
    """Per training session: images in Neo4j vs sample files on disk."""
    status = {}
    for cid in ALL_CONCEPTS:
        on_disk = len(list((REPO / "datasets" / "train" / cid).glob("*.png")))
        in_neo4j = len(session_image_ids(cid))
        status[cid] = {"files_on_disk": on_disk, "graphs_in_neo4j": in_neo4j}
    return status


def ingest_session(class_number: int, subclass: int, wait: bool = True) -> None:
    """Additively re-ingest datasets/train/<cls>_<sub> through the live pipeline.

    Requires connector/skeletonization/contour_analysis up (make start_services).
    Does NOT create a concept — only repopulates session image graphs.
    """
    subprocess.run(
        ["make", f"train_prepared_samples_{class_number}", str(subclass)],
        cwd=REPO, check=True,
    )
    if wait:
        sys.path.insert(0, str(REPO / "src" / "training"))
        from infrastructure import wait_for_kafka_idle
        wait_for_kafka_idle(
            topic="contour-analysis-output-topic",
            idle_timeout=10,
            bootstrap_servers="localhost:29092",
        )


def ingest_missing_sessions() -> None:
    for cid, st in sessions_status().items():
        if st["graphs_in_neo4j"] >= st["files_on_disk"] > 0:
            print(f"  {cid}: OK ({st['graphs_in_neo4j']} graphs)")
            continue
        cls, sub = cid.split("_")
        print(f"  {cid}: ingesting {st['files_on_disk']} samples ...")
        ingest_session(int(cls), int(sub))


def run_probe(
    samples_dir: Path,
    out_dir: Path,
    concept_id: str = "probe",
    order_seed: int | None = None,
    steps: int | None = None,
    capture_failure: bool = True,
) -> dict:
    """Run the offline probe CLI; returns its summary.json contents."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(_PROBE),
           "--samples-dir", str(samples_dir),
           "--concept-id", concept_id,
           "--out", str(out_dir)]
    if order_seed is not None:
        cmd += ["--order-seed", str(order_seed)]
    if steps is not None:
        cmd += ["--steps", str(steps)]
    if capture_failure:
        cmd += ["--capture-failure"]
    env = dict(os.environ,
               PYTHONPATH=str(REPO / "common"),
               NEO4J_DSN=NEO4J_URI, NEO4J_USER=NEO4J_USER,
               NEO4J_PASSWORD=NEO4J_PASSWORD)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                          cwd=REPO, timeout=1800)
    summary_path = out_dir / "summary.json"
    if proc.returncode != 0 or not summary_path.exists():
        raise RuntimeError(
            f"probe failed (exit {proc.returncode}):\n{proc.stdout[-1500:]}\n{proc.stderr[-1500:]}"
        )
    summary = json.loads(summary_path.read_text())
    summary["_probe_stdout"] = proc.stdout.strip().splitlines()[-2:]
    return summary


def load_events(out_dir: Path) -> list[dict]:
    events_path = out_dir / "events.jsonl"
    if not events_path.exists():
        return []
    return [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
