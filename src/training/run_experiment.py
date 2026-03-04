#!/usr/bin/env python3
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in [_HERE, os.path.join(_PROJECT_ROOT, "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

from sklearn.metrics import accuracy_score
from evaluation import test_mnist_all, compare_against_best, MLFLOW_EXPERIMENT, MLFLOW_DEFAULT_URI

QUEUE_PATH = os.path.join(_HERE, "experiments", "queue.json")


def _load_queue() -> dict:
    with open(QUEUE_PATH) as f:
        return json.load(f)


def _save_queue(queue: dict) -> None:
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)


def _find_experiment(queue: dict, exp_id: str) -> dict:
    for exp in queue["experiments"]:
        if exp["id"] == exp_id:
            return exp
    raise ValueError(f"Experiment '{exp_id}' not found in queue.json")


def _build_description(exp: dict) -> str:
    parts = []
    if exp.get("description"):
        parts.append(exp["description"])
    if exp.get("notes"):
        parts.append(f"Notes: {exp['notes']}")
    return "\n".join(parts)


def run(exp_id: str, fraction: float) -> None:
    queue = _load_queue()
    exp = _find_experiment(queue, exp_id)

    needs_quick_run = exp["quick_run_id"] is None
    if not needs_quick_run and exp["full_run_id"] is not None:
        print(json.dumps({
            "run_id": exp["full_run_id"],
            "accuracy": exp["full_accuracy"],
            "status": exp["status"],
        }))
        return

    exp["status"] = "running_quick" if needs_quick_run else "running_full"
    _save_queue(queue)

    description = _build_description(exp)

    try:
        import mlflow
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", MLFLOW_DEFAULT_URI))
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
    except ImportError:
        mlflow = None

    def _run_test():
        return test_mnist_all(
            exp["classes"], exp["params"],
            sample_fraction=fraction, description=description,
        )

    if mlflow is not None:
        parent_run_id = exp.get("mlflow_parent_run_id")
        if needs_quick_run:
            with mlflow.start_run(run_name=f"{exp_id}_{exp['name']}") as parent:
                exp["mlflow_parent_run_id"] = parent.info.run_id
                _save_queue(queue)
                results, y_true, y_pred, run_dir = _run_test()
        else:
            if parent_run_id:
                with mlflow.start_run(run_id=parent_run_id):
                    results, y_true, y_pred, run_dir = _run_test()
            else:
                results, y_true, y_pred, run_dir = _run_test()
    else:
        results, y_true, y_pred, run_dir = _run_test()

    run_id = os.path.basename(run_dir)
    accuracy = round(accuracy_score(y_true, y_pred) * 100, 2) if y_true else 0.0

    if needs_quick_run:
        exp["quick_run_id"] = run_id
        exp["quick_accuracy"] = accuracy
        exp["status"] = "quick_done"
    else:
        exp["full_run_id"] = run_id
        exp["full_accuracy"] = accuracy
        exp["status"] = "full_done"

    # Log summary metrics on parent run
    if mlflow is not None and exp.get("mlflow_parent_run_id"):
        try:
            with mlflow.start_run(run_id=exp["mlflow_parent_run_id"]):
                summary = {}
                if exp.get("quick_accuracy") is not None:
                    summary["quick_accuracy"] = exp["quick_accuracy"]
                if exp.get("full_accuracy") is not None:
                    summary["full_accuracy"] = exp["full_accuracy"]
                best = max(v for v in [exp.get("quick_accuracy"), exp.get("full_accuracy")] if v is not None)
                summary["best_accuracy"] = best
                mlflow.log_metrics(summary)
        except Exception:
            pass

    _save_queue(queue)

    comparison = compare_against_best(accuracy / 100.0, sample_fraction_filter=fraction)
    output = {"run_id": run_id, "accuracy": accuracy, "status": exp["status"]}
    if comparison.get("delta") is not None:
        output["delta"] = round(comparison["delta"] * 100, 2)
        output["is_improvement"] = comparison["is_improvement"]
    print(json.dumps(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a single experiment from queue.json")
    parser.add_argument("--id", required=True, help="Experiment ID (e.g. exp_001)")
    parser.add_argument(
        "--fraction",
        type=float,
        default=float(os.environ.get("QUICK_SAMPLE_FRACTION", "0.25")),
        help="Sample fraction (default: QUICK_SAMPLE_FRACTION from .env)",
    )
    args = parser.parse_args()
    run(args.id, args.fraction)
