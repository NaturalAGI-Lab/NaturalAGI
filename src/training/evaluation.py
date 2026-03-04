"""
Evaluation utilities: batch testing, metrics, confusion matrix.
Extracted from training.ipynb.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import random
import re
import subprocess
import uuid
from datetime import datetime
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from neo4j import GraphDatabase
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

def _is_notebook() -> bool:
    try:
        return get_ipython().__class__.__name__ in ("ZMQInteractiveShell", "Shell")  # noqa: F821
    except NameError:
        return False


class _PrintProgress:
    """Newline-based progress for non-interactive terminals (e.g. Claude Code)."""

    def __init__(self, total: int, desc: str = "", step_pct: int = 10, **_kwargs):
        self.total = total
        self.desc = desc
        self.done = 0
        self.step = max(1, total * step_pct // 100)
        self.next_report = self.step

    def update(self, n: int = 1) -> None:
        self.done += n
        if self.done >= self.next_report or self.done == self.total:
            pct = self.done * 100 // self.total
            print(f"{self.desc}: {pct}% ({self.done}/{self.total})", flush=True)
            self.next_report += self.step

    def close(self) -> None:
        pass

from classifier import classify_images_stream, extract_class_from_concept_id

logger = logging.getLogger(__name__)

_TRAINING_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_TRAINING_DIR, "..", ".."))

CONFUSION_MATRIX_FIGSIZE = (10, 7)

MLFLOW_EXPERIMENT = "naturalagi-classification"
MLFLOW_DEFAULT_URI = "http://localhost:5050"

_NEO4J_URI = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "111122223333")


def save_confusion_matrix(cm: np.ndarray, classes: List[str], run_dir: str) -> None:
    """Plot and save confusion matrix as PNG."""
    plt.figure(figsize=CONFUSION_MATRIX_FIGSIZE)
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix")
    plt.colorbar()

    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    thresh = cm.max() / 2.0
    for i, j in np.ndindex(cm.shape):
        plt.text(j, i, format(cm[i, j], "d"),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.ylabel("True label")
    plt.xlabel("Predicted label")
    plt.tight_layout()
    plt.savefig(os.path.join(run_dir, "confusion_matrix.png"))
    plt.close()


def test_mnist_all(
    classes: List[int],
    params: Dict[str, Any],
    sample_fraction: float = 1.0,
    description: str = "",
    results_dir: str = os.path.join(_TRAINING_DIR, "training_results"),
    nuclio_volume_path_template: str = "/opt/nuclio/shared_storage/generated_samples/mnist_{cls}/test",
    local_path_template: str = os.path.join(_TRAINING_DIR, "../../tests/generated_samples/mnist_{cls}/test"),
    kafka_bootstrap_servers: str = "localhost:29092",
    neo4j_uri: str = _NEO4J_URI,
    neo4j_user: str = _NEO4J_USER,
    neo4j_password: str = _NEO4J_PASS,
) -> Tuple[Dict[str, Any], List[str], List[str], str]:
    """
    Test MNIST classification for all given classes and compute overall metrics.

    Returns:
        (all_results, y_true, y_pred, run_dir)
    """
    all_results: Dict[str, Any] = {}
    all_y_true: List[str] = []
    all_y_pred: List[str] = []
    incorrect_results: List[Dict[str, Any]] = []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(results_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    # Snapshot concept state from Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    concept_complexities: Dict[str, int] = {}
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            WHERE n.concept_id IS NOT NULL AND (n:Point OR n:Vector)
            WITH n.concept_id AS cid, count(n) AS node_count
            RETURN cid, node_count
            ORDER BY cid
        """)
        for record in result:
            concept_complexities[record["cid"]] = record["node_count"]
    driver.close()

    run_config = _build_run_config(classes, params, sample_fraction, concept_complexities)
    with open(os.path.join(run_dir, "run_config.json"), "w") as f:
        json.dump(run_config, f, indent=2)

    # Collect all test images
    all_images: List[Tuple[str, str, str, Dict[str, Any]]] = []
    for cls in classes:
        local_folder = local_path_template.format(cls=cls)
        nuclio_folder = nuclio_volume_path_template.format(cls=cls)
        images = [f for f in os.listdir(local_folder) if f.endswith((".png", ".jpg", ".jpeg"))]
        if sample_fraction < 1.0:
            images = random.sample(images, max(1, int(len(images) * sample_fraction)))
        for fname in images:
            image_id = str(uuid.uuid4())
            image_params = {**params, "image_id": image_id}
            all_images.append((os.path.join(nuclio_folder, fname), image_id, str(cls), image_params))

    total_images = len(all_images)
    if sample_fraction < 1.0:
        print(f"Fast mode: {sample_fraction*100:.0f}% of data ({total_images} images)")

    id_to_expected = {img_id: expected for _, img_id, expected, _ in all_images}
    id_to_path = {img_id: path for path, img_id, _, _ in all_images}

    # MLflow: start run BEFORE classification so duration reflects actual work
    mlflow_run_ctx = None
    try:
        import mlflow
        import mlflow.data
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", MLFLOW_DEFAULT_URI))
        mlflow.set_experiment(MLFLOW_EXPERIMENT)

        _has_psutil = importlib.util.find_spec("psutil") is not None
        parent_active = mlflow.active_run() is not None
        mlflow_run_ctx = mlflow.start_run(
            run_name=f"run_{timestamp}",
            nested=parent_active,
            log_system_metrics=_has_psutil,
        )
        mlflow_run_ctx.__enter__()
    except ImportError:
        mlflow = None
    except Exception:
        mlflow = None

    try:
        if mlflow is not None:
            mlflow.log_params({
                "ged_timeout": params.get("ged_timeout", 5),
                "skeletonization_threshold": params.get("skeletonization_threshold", 180),
                "simplification_epsilon": params.get("simplification_epsilon"),
                "sample_fraction": sample_fraction,
                "num_classes": len(classes),
                "classes": str(sorted(classes)),
                "total_images": total_images,
                "common_lib_version": run_config.get("common_lib_version", "unknown"),
                "git_commit": run_config.get("git", {}).get("commit", "unknown")[:8],
                "git_branch": run_config.get("git", {}).get("branch", "unknown"),
                "features": str(run_config.get("features", {}).get("features", [])),
            })

            feature_config = run_config.get("features", {})
            normalizers = feature_config.get("property_normalizers", {})
            if normalizers:
                mlflow.log_params({f"normalizer.{k}": v for k, v in normalizers.items()})
            node_costs = feature_config.get("node_costs", {})
            if node_costs:
                mlflow.log_params({f"node_cost.{k}": v for k, v in node_costs.items()})

            mlflow.set_tag("researcher", os.environ.get("USER", "unknown"))
            mlflow.set_tag("git_dirty", str(run_config.get("git", {}).get("dirty", False)))
            if description:
                mlflow.set_tag("mlflow.note.content", description)

            try:
                dataset_df = pd.DataFrame([
                    {"image_path": path, "expected_class": expected}
                    for path, _, expected, _ in all_images
                ])
                dataset = mlflow.data.from_pandas(
                    dataset_df,
                    name=f"mnist_test_{len(classes)}cls_{total_images}img",
                    targets="expected_class",
                )
                mlflow.log_input(dataset, context="evaluation")
            except Exception:
                logger.debug("dataset tracking failed, continuing")

        if _is_notebook():
            from tqdm.notebook import tqdm
            pbar = tqdm(total=total_images, desc="Classifying", leave=True)
        else:
            pbar = _PrintProgress(total=total_images, desc="Classifying")
        stream_input = [(path, img_id, img_params) for path, img_id, _, img_params in all_images]
        stream_results = classify_images_stream(
            stream_input,
            on_result=lambda img_id, _r: pbar.update(1),
            kafka_bootstrap_servers=kafka_bootstrap_servers,
        )
        pbar.close()

        for img_id, result in stream_results.items():
            expected_name = id_to_expected[img_id]
            image_path = id_to_path[img_id]
            result["image_path"] = image_path
            result["expected"] = expected_name
            all_results[image_path] = result

            if result["status"] == "success":
                class_results = result.get("classification_results", [])
                if class_results and class_results[0].get("is_minor", False):
                    predicted = extract_class_from_concept_id(class_results[0]["concept_id"])
                    result["predicted"] = predicted
                    result["correct"] = predicted == expected_name
                else:
                    result["correct"] = False
                    result["predicted"] = "not classified"
                all_y_true.append(expected_name)
                all_y_pred.append(result["predicted"])
                if not result["correct"]:
                    incorrect_results.append({
                        **result,
                        "classification_results": json.dumps(result.get("classification_results", [])),
                    })
            else:
                incorrect_results.append({**result, "classification_results": json.dumps([])})

        failed_dlq = sum(1 for r in incorrect_results if r.get("error") == "DLQ")
        successful = len(all_y_true)

        if incorrect_results:
            pd.DataFrame(incorrect_results).to_csv(
                os.path.join(run_dir, "incorrect_results.csv"), index=False
            )

        if successful > 0:
            labels = sorted(set(all_y_true + all_y_pred))
            overall_precision, overall_recall, overall_f1, _ = precision_recall_fscore_support(
                all_y_true, all_y_pred, labels=labels, average="weighted"
            )
            overall_accuracy = accuracy_score(all_y_true, all_y_pred)
            class_precision, class_recall, class_f1, support = precision_recall_fscore_support(
                all_y_true, all_y_pred, labels=labels, average=None
            )

            _save_metrics(
                run_dir, total_images, failed_dlq, successful,
                overall_accuracy, overall_precision, overall_recall, overall_f1,
                labels, class_precision, class_recall, class_f1, support,
            )

            cm = confusion_matrix(all_y_true, all_y_pred, labels=labels)
            save_confusion_matrix(cm, labels, run_dir)
            print(f"\nResults saved to: {run_dir}")

            if mlflow is not None:
                mlflow.log_metrics({
                    "accuracy": overall_accuracy,
                    "precision": overall_precision,
                    "recall": overall_recall,
                    "f1": overall_f1,
                    "failed_dlq": float(failed_dlq),
                })
                for i, label in enumerate(labels):
                    if label not in ("error", "timeout", "not classified"):
                        mlflow.log_metric(f"recall_{label}", class_recall[i])
                        mlflow.log_metric(f"precision_{label}", class_precision[i])
                        mlflow.log_metric(f"f1_{label}", class_f1[i])
                mlflow.log_artifact(os.path.join(run_dir, "run_config.json"))
                mlflow.log_artifact(os.path.join(run_dir, "confusion_matrix.png"))
                mlflow.log_artifact(os.path.join(run_dir, "metrics.csv"))
                mlflow.log_artifact(os.path.join(run_dir, "per_class_metrics.csv"))
                if incorrect_results:
                    mlflow.log_artifact(os.path.join(run_dir, "incorrect_results.csv"))
        else:
            logger.warning("No successful classifications to calculate metrics.")
    finally:
        if mlflow_run_ctx is not None:
            mlflow_run_ctx.__exit__(None, None, None)

    return all_results, all_y_true, all_y_pred, run_dir


def _build_run_config(
    classes: List[int],
    params: Dict[str, Any],
    sample_fraction: float,
    concept_complexities: Dict[str, int],
) -> Dict[str, Any]:
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_PROJECT_ROOT
    ).stdout.strip()
    git_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=_PROJECT_ROOT
    ).stdout.strip()
    git_dirty = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_PROJECT_ROOT
    ).stdout.strip() != ""

    return {
        "timestamp": datetime.now().isoformat(),
        "git": {"commit": git_commit, "branch": git_branch, "dirty": git_dirty},
        "common_lib_version": _get_common_lib_version(),
        "classification_params": params,
        "sample_fraction": sample_fraction,
        "classes": sorted(classes),
        "concepts": concept_complexities,
        "features": _read_feature_config(),
    }


def _get_common_lib_version() -> str:
    try:
        pyproject_path = os.path.join(_PROJECT_ROOT, "pyproject.toml")
        with open(pyproject_path) as f:
            for line in f:
                m = re.match(r'version\s*=\s*"(.+)"', line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return "unknown"


def _read_feature_config() -> Dict[str, Any]:
    """Load feature config by dynamically importing cost_functions.py."""
    cost_functions_path = os.path.join(
        _TRAINING_DIR, "..", "classification", "graph_similarity", "cost_functions.py"
    )
    try:
        spec = importlib.util.spec_from_file_location("_cf_snapshot", cost_functions_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return {
            "features": list(mod.features),
            "property_normalizers": dict(mod.PROPERTY_NORMALIZERS),
            "node_costs": {
                k: v for k, v in vars(mod.NodeCost).items()
                if not k.startswith("_") and isinstance(v, (int, float))
            },
        }
    except Exception as exc:
        return {"error": f"Could not read {cost_functions_path}: {exc}"}


def _save_metrics(
    run_dir: str,
    total: int,
    failed_dlq: int,
    successful: int,
    overall_accuracy: float,
    overall_precision: float,
    overall_recall: float,
    overall_f1: float,
    labels: List[str],
    class_precision: np.ndarray,
    class_recall: np.ndarray,
    class_f1: np.ndarray,
    support: np.ndarray,
) -> None:
    pd.DataFrame({
        "Metric": ["Total Images", "Failed (DLQ)", "Successfully Classified",
                   "Success Rate (%)", "Accuracy (%)", "Precision (%)", "Recall (%)", "F1 Score (%)"],
        "Value": [
            total, failed_dlq, successful,
            (successful / max(total - failed_dlq, 1)) * 100,
            overall_accuracy * 100, overall_precision * 100,
            overall_recall * 100, overall_f1 * 100,
        ],
    }).to_csv(os.path.join(run_dir, "metrics.csv"), index=False)

    per_class = [
        {"class": lbl,
         "precision": class_precision[i] * 100,
         "recall": class_recall[i] * 100,
         "f1_score": class_f1[i] * 100,
         "support": support[i]}
        for i, lbl in enumerate(labels)
        if lbl not in ("error", "timeout", "not classified")
    ]
    pd.DataFrame(per_class).to_csv(os.path.join(run_dir, "per_class_metrics.csv"), index=False)

    print(f"\n{'='*50}")
    print(f"Total: {total}  |  DLQ: {failed_dlq}  |  Success: {successful}")
    print(f"Accuracy:  {overall_accuracy*100:.2f}%")
    print(f"Precision: {overall_precision*100:.2f}%")
    print(f"Recall:    {overall_recall*100:.2f}%")
    print(f"F1:        {overall_f1*100:.2f}%")
    print(f"{'='*50}")


def search_best_run(
    experiment_name: str = MLFLOW_EXPERIMENT,
    metric: str = "accuracy",
    filter_string: str = "",
) -> Dict[str, Any] | None:
    try:
        import mlflow
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", MLFLOW_DEFAULT_URI))
        runs = mlflow.search_runs(
            experiment_names=[experiment_name],
            filter_string=filter_string,
            order_by=[f"metrics.{metric} DESC"],
            max_results=1,
        )
        if runs.empty:
            return None
        best = runs.iloc[0]
        return {
            "run_id": best["run_id"],
            "accuracy": best.get(f"metrics.{metric}"),
            "run_name": best.get("tags.mlflow.runName", ""),
        }
    except Exception as exc:
        logger.debug("search_best_run failed: %s", exc)
        return None


def compare_against_best(
    current_accuracy: float,
    sample_fraction_filter: float | None = None,
) -> Dict[str, Any]:
    filter_str = ""
    if sample_fraction_filter is not None:
        filter_str = f"params.sample_fraction = '{sample_fraction_filter}'"
    best = search_best_run(filter_string=filter_str)
    if best is None or best["accuracy"] is None:
        return {"best_accuracy": None, "delta": None, "is_improvement": None, "best_run_id": None}
    best_acc = float(best["accuracy"])
    delta = current_accuracy - best_acc
    return {
        "best_accuracy": round(best_acc, 4),
        "delta": round(delta, 4),
        "is_improvement": delta > 0,
        "best_run_id": best["run_id"],
    }
