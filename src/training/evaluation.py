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
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Tuple

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from neo4j import GraphDatabase
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from classification.repository.neo4j_to_networkx import Neo4jToNetworkX

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
_EXPERIMENTS_DIR = os.path.join(_PROJECT_ROOT, "experiments")

CONFUSION_MATRIX_FIGSIZE = (10, 7)

MLFLOW_EXPERIMENT = "naturalagi-classification"
MLFLOW_DEFAULT_URI = "http://localhost:5050"

_NEO4J_URI = os.environ.get("NEO4J_DSN", "bolt://localhost:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "111122223333")

_CONCEPT_GRAPH_QUERY = """
CALL {
    MATCH (n:Point {concept_id: $concept_id}) RETURN n
    UNION ALL
    MATCH (n:Vector {concept_id: $concept_id}) RETURN n
    UNION ALL
    MATCH (n:StartPoint {concept_id: $concept_id}) RETURN n
}
WITH n, labels(n) AS node_labels, properties(n) as node_props
OPTIONAL MATCH (n)-[r]-(m {concept_id: $concept_id})
WITH n, node_labels, r, m, node_props
RETURN elementId(n) AS node_id,
    node_labels,
    node_props,
    type(r) AS rel_type,
    elementId(r) AS rel_id,
    elementId(m) AS target_id
"""


def _json_default(obj: Any) -> Any:
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _load_concept_graphs(driver) -> Dict[str, nx.Graph]:
    concept_ids: list[str] = []
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Point)
            WHERE c.concept_id IS NOT NULL
            RETURN DISTINCT c.concept_id AS concept_id
        """)
        concept_ids = [r["concept_id"] for r in result]

    graphs: Dict[str, nx.Graph] = {}
    for cid in concept_ids:
        with driver.session() as session:
            result = session.run(_CONCEPT_GRAPH_QUERY, concept_id=cid)
            graphs[cid] = Neo4jToNetworkX.build_networkx_graph(result, is_concept=True)
    return graphs


def export_concept_snapshot(concept_graphs: Dict[str, nx.Graph], path: str) -> str:
    snapshot = {cid: nx.node_link_data(g) for cid, g in concept_graphs.items()}
    filepath = os.path.join(path, "concept_graphs.json")
    with open(filepath, "w") as f:
        json.dump(snapshot, f, default=_json_default)
    return filepath


def restore_concept_snapshot(path: str) -> Dict[str, nx.Graph]:
    with open(path) as f:
        snapshot = json.load(f)
    graphs: Dict[str, nx.Graph] = {}
    for cid, data in snapshot.items():
        g = nx.node_link_graph(data)
        for _, node_data in g.nodes(data=True):
            if "labels" in node_data:
                node_data["labels"] = set(node_data["labels"])
        graphs[cid] = g
    return graphs


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
    quiet: bool = False,
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

    _quiet_state: Dict[str, Any] = {}
    if quiet:
        import warnings
        _quiet_state["warn_ctx"] = warnings.catch_warnings()
        _quiet_state["warn_ctx"].__enter__()
        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
        warnings.filterwarnings("ignore", message=".*UndefinedMetric.*")
        _noisy_loggers = {
            "neo4j": logging.ERROR,
            "neo4j.notifications": logging.ERROR,
            "neo4j.io": logging.ERROR,
            "mlflow": logging.WARNING,
            "mlflow.system_metrics": logging.ERROR,
            "mlflow.tracking": logging.WARNING,
        }
        for _name, _target_level in _noisy_loggers.items():
            _log = logging.getLogger(_name)
            _quiet_state.setdefault("log_levels", {})[_name] = _log.level
            _log.setLevel(_target_level)

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
    concept_graphs = _load_concept_graphs(driver)
    driver.close()

    snapshot_path = export_concept_snapshot(concept_graphs, run_dir)

    run_config = _build_run_config(classes, params, sample_fraction, concept_complexities)
    with open(os.path.join(run_dir, "run_config.json"), "w") as f:
        json.dump(run_config, f, indent=2)

    # MLflow: start run BEFORE image list so experiment_id and run_id can be injected
    mlflow_run_ctx = None
    mlflow_experiment_id = None
    mlflow_run_id = None
    try:
        import mlflow
        import mlflow.data
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", MLFLOW_DEFAULT_URI))
        _experiment = mlflow.set_experiment(MLFLOW_EXPERIMENT)
        mlflow_experiment_id = _experiment.experiment_id

        _has_psutil = importlib.util.find_spec("psutil") is not None
        parent_active = mlflow.active_run() is not None
        mlflow_run_ctx = mlflow.start_run(
            run_name=f"run_{timestamp}",
            nested=parent_active,
            log_system_metrics=_has_psutil and not quiet,
        )
        mlflow_run_ctx.__enter__()
        _active_run = mlflow.active_run()
        mlflow_run_id = _active_run.info.run_id if _active_run else None
    except ImportError:
        mlflow = None
    except Exception:
        mlflow = None

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
            if mlflow_experiment_id:
                image_params["mlflow_experiment_id"] = mlflow_experiment_id
            if mlflow_run_id:
                image_params["mlflow_run_id"] = mlflow_run_id
            all_images.append((os.path.join(nuclio_folder, fname), image_id, str(cls), image_params))

    total_images = len(all_images)
    if sample_fraction < 1.0 and not quiet:
        print(f"Fast mode: {sample_fraction*100:.0f}% of data ({total_images} images)")

    id_to_expected = {img_id: expected for _, img_id, expected, _ in all_images}
    id_to_path = {img_id: path for path, img_id, _, _ in all_images}

    try:
        if mlflow is not None:
            mlflow.log_params({
                "ged_timeout": params.get("ged_timeout", 5),
                "skeletonization_threshold": params.get("skeletonization_threshold", 180),
                "simplification_epsilon": params.get("simplification_epsilon"),
                "comparison_method": params.get("comparison_method", "ged"),
                "fgw_alpha": params.get("fgw_alpha", 0.5),
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
            pbar = tqdm(total=total_images, desc="Classifying", leave=not quiet)
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
                quiet=quiet,
            )

            cm = confusion_matrix(all_y_true, all_y_pred, labels=labels)
            save_confusion_matrix(cm, labels, run_dir)
            if not quiet:
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
                mlflow.log_artifact(snapshot_path)
                if incorrect_results:
                    mlflow.log_artifact(os.path.join(run_dir, "incorrect_results.csv"))
        else:
            logger.warning("No successful classifications to calculate metrics.")
    finally:
        if mlflow_run_ctx is not None:
            mlflow_run_ctx.__exit__(None, None, None)
        if _quiet_state:
            for _name, _lvl in _quiet_state.get("log_levels", {}).items():
                logging.getLogger(_name).setLevel(_lvl)
            if "warn_ctx" in _quiet_state:
                _quiet_state["warn_ctx"].__exit__(None, None, None)

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
        "features": {
            **_read_feature_config(),
            **({
                "features": params["features"],
            } if "features" in params else {}),
            **({
                "property_normalizers": params["property_normalizers"],
            } if "property_normalizers" in params else {}),
            **({
                "node_costs": params["node_costs"],
            } if "node_costs" in params else {}),
        },
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
    quiet: bool = False,
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

    if not quiet:
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


_ACCURACY_KEYS = ("accuracy_quick", "accuracy_quick_25pct", "accuracy")

_NORMALIZER_SHORT_TO_FULL = {
    "norm_x": "normalized_x",
    "norm_y": "normalized_y",
    "norm_hdir": "horizontal_direction",
    "norm_vdir": "vertical_direction",
    "norm_cycle": "cycle_count",
    "norm_angle": "angle_with_ox",
}


def _scan_param_files(exp_dir: str) -> List[Tuple[str, Dict[str, Any], float | None]]:
    results: List[Tuple[str, Dict[str, Any], float | None]] = []
    for fname in sorted(os.listdir(exp_dir)):
        if not (fname.startswith("best_params") and fname.endswith(".json")):
            continue
        with open(os.path.join(exp_dir, fname)) as f:
            data = json.load(f)
        accuracy = None
        for key in _ACCURACY_KEYS:
            if key in data:
                accuracy = data[key]
                break
        results.append((fname, data, accuracy))
    return results


def list_experiments() -> List[Dict[str, Any]]:
    if not os.path.isdir(_EXPERIMENTS_DIR):
        return []
    experiments = []
    for name in sorted(os.listdir(_EXPERIMENTS_DIR)):
        exp_dir = os.path.join(_EXPERIMENTS_DIR, name)
        if not os.path.isdir(exp_dir):
            continue
        entries = _scan_param_files(exp_dir)
        best_acc = None
        for _, _, acc in entries:
            if acc is not None and (best_acc is None or acc > best_acc):
                best_acc = acc
        experiments.append({
            "name": name,
            "best_accuracy": best_acc,
            "param_files": [fname for fname, _, _ in entries],
        })
    return experiments


def load_best_params(experiment: str) -> Dict[str, Any]:
    exp_dir = os.path.join(_EXPERIMENTS_DIR, experiment)
    if not os.path.isdir(exp_dir):
        available = [e["name"] for e in list_experiments()]
        raise FileNotFoundError(
            f"Experiment '{experiment}' not found. Available: {available}"
        )

    candidates = _scan_param_files(exp_dir)

    if not candidates:
        raise FileNotFoundError(f"No best_params*.json in {exp_dir}")

    with_acc = [(n, d, a) for n, d, a in candidates if a is not None]
    if with_acc:
        fname, data, accuracy = max(with_acc, key=lambda x: x[2])  # type: ignore[arg-type]
    else:
        fname, data, accuracy = candidates[0]

    params = _normalize_experiment_params(data)
    acc_str = f" (accuracy: {accuracy * 100:.2f}%)" if accuracy else ""
    print(f"Loaded {experiment}/{fname}{acc_str}")
    return params


def _normalize_experiment_params(raw: Dict[str, Any]) -> Dict[str, Any]:
    if "params" in raw and isinstance(raw["params"], dict):
        return _normalize_nested_format(raw)
    metadata = {"trial_number", "accuracy_quick_25pct", "accuracy_quick", "accuracy", "trial"}
    return {k: v for k, v in raw.items() if k not in metadata}


def _normalize_nested_format(raw: Dict[str, Any]) -> Dict[str, Any]:
    p = raw["params"]

    params: Dict[str, Any] = {}

    if "comparison_method" in p:
        params["comparison_method"] = p["comparison_method"]
    elif "comparison_method" in raw:
        params["comparison_method"] = raw["comparison_method"]
    elif "fgw_alpha" in p:
        params["comparison_method"] = "fgw"
    else:
        params["comparison_method"] = "ged"

    if "fgw_alpha" in p:
        params["fgw_alpha"] = p["fgw_alpha"]

    for key in ("ged_timeout", "simplification_epsilon"):
        if key in p:
            params[key] = p[key]
    if "skel_threshold" in p:
        params["skeletonization_threshold"] = p["skel_threshold"]

    if raw.get("features"):
        params["features"] = raw["features"]

    normalizers = {}
    for short, full in _NORMALIZER_SHORT_TO_FULL.items():
        if short in p:
            normalizers[full] = p[short]
    if normalizers:
        params["property_normalizers"] = normalizers

    if raw.get("derived_costs"):
        params["node_costs"] = raw["derived_costs"]
    elif "cost_minor" in p:
        minor = p["cost_minor"]
        general = minor + p.get("gap_minor_general", 0)
        severe = general + p.get("gap_general_severe", 0)
        params["node_costs"] = {
            "NO_COST": 0.0,
            "MINOR": minor,
            "GENERAL": general,
            "SEVERE": severe,
            "NO_MATCH": p.get("cost_no_match", 1.0),
            "IMPOSSIBLE": p.get("cost_impossible", 100.0),
        }

    return params
