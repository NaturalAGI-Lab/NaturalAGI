"""One-shot retrain script: clear Neo4j, then train all 13 active subclasses
deterministically from `tests/prepared_samples/<X_Y>/` and create each concept.

Subclasses match the 2026-04-27 baseline run (run_20260427_144233):
0_1, 1_1, 1_3, 2_1, 2_2, 3_1, 4_1, 4_2, 5_1, 6_1, 7_1, 8_1, 9_2.
"""
from __future__ import annotations

import os
import subprocess

from infrastructure import wait_for_kafka_idle, verify_concept_created

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


def train_one(class_number: int, subclass: int) -> None:
    concept_id = f"{class_number}_{subclass}"
    print(f"\n=== Training {concept_id} ===", flush=True)

    subprocess.run(
        ["make", f"train_prepared_samples_{class_number}", str(subclass)],
        cwd=_PROJECT_ROOT,
        check=True,
    )

    wait_for_kafka_idle(
        topic="contour-analysis-output-topic",
        idle_timeout=10,
        bootstrap_servers="localhost:29092",
    )

    subprocess.run(
        ["make", "create_concept", concept_id, f"mnist-{class_number}"],
        cwd=_PROJECT_ROOT,
        check=True,
    )

    if not verify_concept_created(concept_id):
        raise RuntimeError(f"Concept {concept_id} not found in Neo4j after training")
    print(f"=== {concept_id} trained ===", flush=True)


if __name__ == "__main__":
    for cls, sub in SUBCLASSES:
        train_one(cls, sub)
    print("\nAll concepts trained.")

    # Concepts are cached per-instance in classification's init_context(); fan out
    # a reload so the running instances pick up the retrained concepts without a
    # redeploy.
    subprocess.run(["make", "reload_concepts"], cwd=_PROJECT_ROOT, check=True)
    print("Concept cache reloaded on all classification instances.")
