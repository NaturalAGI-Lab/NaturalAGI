"""Section 6 (S1): classification quality on other MNIST datasets.

Variants vs the complete-only 10k baseline (91.13%):
  A) full 10k test split, no exclusions;
  B) 60k train split, complete-only and unfiltered (heuristic annotation);
  70k numbers = post-hoc aggregation of the 10k and 60k runs (no extra run).
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from . import REPO, RUN_DIR

QUEUE_PATH = REPO / "src" / "training" / "experiments" / "queue.json"
RESULTS_DIR = REPO / "src" / "training" / "training_results"
TEST_MANIFEST = REPO / "datasets" / "mnist_all_manifest.csv"
TRAIN_MANIFEST = REPO / "datasets" / "mnist_train_all_manifest.csv"
ALL_STRUCTURES = ["complete", "incomplete", "unreviewed"]


def baseline_params() -> dict:
    cfg = json.load(open(RUN_DIR / "run_config.json"))
    return dict(cfg["classification_params"])


def manifest_counts(manifest_path: Path,
                    structure_filter: list[str] | None = None) -> pd.DataFrame:
    rows = list(csv.DictReader(open(manifest_path)))
    df = pd.DataFrame(rows)
    if structure_filter:
        df = df[df["structure"].isin(structure_filter)]
    out = df.groupby(["class", "structure"]).size().unstack(fill_value=0)
    out["total"] = out.sum(axis=1)
    return out


def load_queue() -> dict:
    return json.loads(QUEUE_PATH.read_text())


def ensure_experiment(exp: dict) -> None:
    """Insert the experiment into queue.json if an entry with this id is absent."""
    queue = load_queue()
    if any(e["id"] == exp["id"] for e in queue["experiments"]):
        print(f"{exp['id']}: вже у черзі")
        return
    defaults = {"status": "pending", "quick_run_id": None, "quick_accuracy": None,
                "full_run_id": None, "full_accuracy": None, "notes": ""}
    queue["experiments"].append({**defaults, **exp})
    QUEUE_PATH.write_text(json.dumps(queue, indent=2))
    print(f"{exp['id']}: додано до черги")


def s1_experiments() -> list[dict]:
    params = baseline_params()
    params_60k = dict(params, delete_image_nodes=True)
    classes = list(range(10))
    return [
        {
            "id": "exp_s1_test10k_unfiltered",
            "name": "s1_test10k_unfiltered",
            "description": "S1-A: повний тестовий сет MNIST (10k) без виключень, базлайн-параметри",
            "classes": classes,
            "params": params,
            "structure_filter": ALL_STRUCTURES,
        },
        {
            "id": "exp_s1_train60k_unfiltered",
            "name": "s1_train60k_unfiltered",
            "description": "S1-B: train-спліт MNIST (60k) без виключень (delete_image_nodes=true)",
            "classes": classes,
            "params": params_60k,
            "structure_filter": ALL_STRUCTURES,
            "manifest_path": str(TRAIN_MANIFEST),
            "local_path_template": str(REPO / "datasets" / "mnist_train_all" / "{cls}"),
            "nuclio_volume_path_template": "/opt/nuclio/shared_storage/mnist_train_all/{cls}",
        },
        {
            "id": "exp_s1_train60k_complete",
            "name": "s1_train60k_complete",
            "description": "S1-B: train-спліт MNIST (60k), лише complete (евристична розмітка)",
            "classes": classes,
            "params": params_60k,
            "structure_filter": ["complete"],
            "manifest_path": str(TRAIN_MANIFEST),
            "local_path_template": str(REPO / "datasets" / "mnist_train_all" / "{cls}"),
            "nuclio_volume_path_template": "/opt/nuclio/shared_storage/mnist_train_all/{cls}",
        },
    ]


def run_experiment(exp_id: str, fraction: float = 1.0) -> None:
    """Blocking run via the queue runner; streams output into the notebook."""
    cmd = [sys.executable, str(REPO / "src" / "training" / "run_experiment.py"),
           "--id", exp_id, "--fraction", str(fraction)]
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"run_experiment {exp_id} exit={proc.returncode}")


def _structure_by_basename(manifest_path: Path) -> dict[str, str]:
    rows = csv.DictReader(open(manifest_path))
    return {Path(r["image_path"]).name: r["structure"] for r in rows}


def split_metrics(run_id: str, manifest_path: Path) -> pd.DataFrame:
    """Accuracy per structure subset (повні прогони, fraction=1.0).

    total per subset — from the run's manifest_summary ∩ manifest; wrong — every
    row of incorrect_results.csv (misses + DLQ/errors) mapped by basename.
    """
    run_dir = RESULTS_DIR / run_id
    cfg = json.load(open(run_dir / "run_config.json"))
    allowed_structures = set(
        cfg.get("manifest", {}).get("structure_filter")
        or cfg.get("manifest_summary", {}).get("structure_filter")
        or ALL_STRUCTURES
    )
    structures = _structure_by_basename(manifest_path)

    totals: dict[str, int] = {}
    for name, structure in structures.items():
        if structure in allowed_structures:
            totals[structure] = totals.get(structure, 0) + 1

    wrong: dict[str, int] = {s: 0 for s in totals}
    for row in csv.DictReader(open(run_dir / "incorrect_results.csv")):
        s = structures.get(Path(str(row["image_path"])).name)
        if s in wrong:
            wrong[s] += 1

    rows = []
    for s, total in sorted(totals.items()):
        rows.append({
            "structure": s, "submitted": total, "wrong": wrong[s],
            "accuracy_%": round((1 - wrong[s] / total) * 100, 2),
        })
    rows.append({
        "structure": "ALL", "submitted": sum(totals.values()),
        "wrong": sum(wrong.values()),
        "accuracy_%": round((1 - sum(wrong.values()) / sum(totals.values())) * 100, 2),
    })
    return pd.DataFrame(rows)


def aggregate_runs(runs: list[tuple[str, Path]]) -> pd.DataFrame:
    """Post-hoc aggregation across runs, e.g. 10k + 60k => 70k numbers."""
    frames = []
    for run_id, manifest in runs:
        df = split_metrics(run_id, manifest)
        df["run_id"] = run_id
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    totals = combined[combined.structure == "ALL"]
    agg = {
        "structure": "ALL (агреговано)",
        "submitted": int(totals.submitted.sum()),
        "wrong": int(totals.wrong.sum()),
        "accuracy_%": round((1 - totals.wrong.sum() / totals.submitted.sum()) * 100, 2),
        "run_id": "+".join(r for r, _ in runs),
    }
    return pd.concat([combined, pd.DataFrame([agg])], ignore_index=True)
