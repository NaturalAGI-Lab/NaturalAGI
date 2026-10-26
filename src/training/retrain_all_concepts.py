"""One-shot retrain script: clear Neo4j, then train all 13 active subclasses
deterministically via `make train_prepared_samples_*` (samples under `datasets/`)
and create each concept.

Subclasses match the 2026-04-27 baseline run (run_20260427_144233):
0_1, 1_1, 1_3, 2_1, 2_2, 3_1, 4_1, 4_2, 5_1, 6_1, 7_1, 8_1, 9_2.
"""
from __future__ import annotations

import csv
import glob
import os
import subprocess
import time
from datetime import datetime

from neo4j import GraphDatabase

from evaluation import _load_concept_graphs, export_concept_snapshot
from infrastructure import (
    _NEO4J_PASS, _NEO4J_URI, _NEO4J_USER, wait_for_kafka_idle, verify_concept_created, reload_concept_cache,
)

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SUBCLASSES: list[tuple[int, int]] = [
    (0, 1),
    (1, 1), (1, 3),
    (2, 1), (2, 2),
    (3, 1),
    (4, 1), (4, 2),
    (5, 1),
    (6, 1),
    (7, 1),
    (8, 1),
    (9, 2),
]


def backup_concepts(out_dir: str) -> None:
    driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASS))
    try:
        export_concept_snapshot(_load_concept_graphs(driver), out_dir)
    finally:
        driver.close()


def remove_concept(concept_id: str) -> None:
    driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASS))
    try:
        with driver.session() as session:
            session.run("MATCH (n) WHERE n.concept_id = $cid DETACH DELETE n", cid=concept_id)
            # Unconsumed graphs from earlier ingests would otherwise join this formation session.
            session.run("MATCH (n) WHERE n.session_id = $cid DETACH DELETE n", cid=concept_id)
    finally:
        driver.close()


def train_one(class_number: int, subclass: int) -> dict[str, float | int | str]:
    concept_id = f"{class_number}_{subclass}"
    print(f"\n=== Training {concept_id} ===", flush=True)
    remove_concept(concept_id)

    submit_start = time.time()
    subprocess.run(
        ["make", f"train_prepared_samples_{class_number}", str(subclass)],
        cwd=_PROJECT_ROOT,
        check=True,
    )

    last_message = wait_for_kafka_idle(
        topic="contour-analysis-output-topic",
        idle_timeout=10,
        bootstrap_servers="localhost:29092",
    )

    create_start = time.time()
    subprocess.run(
        ["make", "create_concept", concept_id, f"mnist-{class_number}"],
        cwd=_PROJECT_ROOT,
        check=True,
    )
    create_s = time.time() - create_start

    if not verify_concept_created(concept_id):
        raise RuntimeError(f"Concept {concept_id} not found in Neo4j after training")
    print(f"=== {concept_id} trained ===", flush=True)
    formation_s = last_message - submit_start
    return {
        "concept": concept_id,
        "images": len(glob.glob(os.path.join(_PROJECT_ROOT, "datasets", "train", concept_id, "*.png"))),
        "pipeline_s": round(formation_s, 2),
        "create_concept_s": round(create_s, 2),
        "total_s": round(formation_s + create_s, 2),
    }


def write_timings(rows: list[dict[str, float | int | str]], out_dir: str) -> None:
    total = {"concept": "all", "images": sum(int(r["images"]) for r in rows)}
    for key in ("pipeline_s", "create_concept_s", "total_s"):
        total[key] = round(sum(float(r[key]) for r in rows), 2)
    with open(os.path.join(out_dir, "isl_training_times.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(total.keys()))
        writer.writeheader()
        writer.writerows(rows + [total])


if __name__ == "__main__":
    out_dir = os.path.join(_PROJECT_ROOT, "experiments", f"timing_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    backup_concepts(out_dir)
    timings = [train_one(cls, sub) for cls, sub in SUBCLASSES]
    write_timings(timings, out_dir)
    print(f"\nAll concepts trained. Timings in {out_dir}")

    # Concepts are cached per-instance in classification's init_context(); fan out
    # a reload so the running instances pick up the retrained concepts without a
    # redeploy.
    reload_concept_cache()
    print("Concept cache reloaded on all classification instances.")
