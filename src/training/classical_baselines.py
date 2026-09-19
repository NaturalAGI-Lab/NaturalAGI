"""
Classical baselines (SVM, k-NN, nearest-centroid, MLP, CNN) scored on the same
frozen training corpus and test population the ISL pipeline (91.13%, commit
f34b049) was scored on, for the ITSSI XAI article comparison table.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import PIL
import sklearn
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.neighbors import KNeighborsClassifier, NearestCentroid
from sklearn.svm import SVC
from torch import nn

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import resize_mnist_all_inplace  # noqa: E402  (reuses the tracked LANCZOS upscale, applied to the cache copy only)

ARCHIVE_COMMIT = "f34b049"
CACHE_DIR = os.path.join(_PROJECT_ROOT, "experiments", ".cache", "f34b049_datasets")
EXPERIMENTS_DIR = os.path.join(_PROJECT_ROOT, "experiments")
IMAGE_SIZE = (100, 100)
CLASSES = list(range(10))

EXPECTED_TRAIN_ORIGINALS = 76
EXPECTED_TRAIN_INSTANCES = 805
EXPECTED_TRAIN_CONCEPT_DIRS = 13
EXPECTED_TEST_IMAGES = 8708

# Per-class "structure == complete" counts read directly from the archive's own
# manifest (the source of truth per plan.md), versus what run_20260630_235356's
# run_config.json recorded (that run was `dirty: true` and read a manifest edited
# after f34b049 — the excluded image is not identifiable, only its count is).
ARCHIVE_ALLOWED_PER_CLASS = {0: 830, 1: 1129, 2: 956, 3: 969, 4: 954, 5: 796, 6: 742, 7: 1014, 8: 582, 9: 736}
BASELINE_RUN_ALLOWED_PER_CLASS = {0: 830, 1: 1129, 2: 956, 3: 969, 4: 953, 5: 796, 6: 742, 7: 1014, 8: 582, 9: 736}
MANIFEST_DELTA = {
    "class": 4,
    "archive_count": 954,
    "baseline_run_count": 953,
    "note": (
        "run_20260630_235356 was dirty and scored against a manifest edited after f34b049; "
        "the excluded image is not identifiable from the run's artefacts, only its count is. "
        "These baselines are scored on the archive's reproducible 8,708."
    ),
}

# ISL's own headline numbers, as reported by run_20260630_235356/metrics.csv and
# findings.md. Fixed historical facts, not recomputed here.
ISL_TOTAL_SUBMITTED = 8707
ISL_DLQ_FAILURES = 22
ISL_CLASSIFIED = 8685
ISL_CORRECT = 7915
# Macro averages recomputed from run_20260630_235356/per_class_metrics.csv. That
# run's own metrics.csv reports weighted averages (91.92 / 91.13 / 91.34), which
# are not comparable with the macro figures every row above uses.
ISL_MACRO_PRECISION = 92.22
ISL_MACRO_RECALL = 91.22
ISL_MACRO_F1 = 91.54

SEEDS = [0, 1, 2, 3, 4]
QUICK_SEEDS = [0]
QUICK_TEST_SUBSAMPLE = 200
QUICK_CONVERGENCE_EPOCHS = 3

KNN_K_VALUES = [1, 3, 5]
MLP_HIDDEN = (512, 256)
CNN_CHANNELS = (32, 64)
CNN_FC_HIDDEN = 128
ADAM_LR = 1e-3
BATCH_SIZE = 32
INFERENCE_BATCH_SIZE = 256  # a single forward pass over all 8,708 test images would allocate ~11GB
CONVERGENCE_MAX_EPOCHS = 200
CONVERGENCE_PATIENCE = 10
VALIDATION_ORIGINALS_HELD_OUT = 10  # one per digit class

_CRITERION = nn.CrossEntropyLoss()


@dataclass
class Split:
    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray | None = None  # original-image stem, populated for the training split only


@dataclass
class SeedMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    y_pred: np.ndarray


@dataclass
class TorchRunResult:
    seed_metrics: list[SeedMetrics]
    epochs_run: list[int]


# --- Frozen corpus extraction -----------------------------------------------

def ensure_frozen_corpus(cache_dir: str) -> str:
    marker = os.path.join(cache_dir, ".prepared")
    datasets_root = os.path.join(cache_dir, "datasets")
    if os.path.isfile(marker):
        return datasets_root
    os.makedirs(cache_dir, exist_ok=True)
    _extract_archive(cache_dir)
    _upscale_test_images(os.path.join(datasets_root, "mnist_all"))
    open(marker, "w").close()
    return datasets_root


def _extract_archive(cache_dir: str) -> None:
    result = subprocess.run(
        ["git", "show", f"{ARCHIVE_COMMIT}:datasets.zip"],
        capture_output=True, cwd=_PROJECT_ROOT, check=True,
    )
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(result.stdout)
        tmp_path = tmp.name
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            zf.extractall(cache_dir)
    finally:
        os.remove(tmp_path)


def _upscale_test_images(mnist_all_dir: str) -> None:
    total_errors = 0
    for cls_name in sorted(os.listdir(mnist_all_dir)):
        cls_dir = os.path.join(mnist_all_dir, cls_name)
        if os.path.isdir(cls_dir):
            _, _, errors = resize_mnist_all_inplace.resize_dir(cls_dir)
            total_errors += errors
    if total_errors != 0:
        raise RuntimeError(f"{total_errors} test image(s) failed to resize")


# --- Loading ------------------------------------------------------------

def _assert_count(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"expected {expected} {label}, found {actual}")


def _load_image_array(path: str) -> np.ndarray:
    with Image.open(path) as im:
        if im.size != IMAGE_SIZE or im.mode != "L":
            raise AssertionError(f"{path} is {im.size} mode {im.mode}, expected {IMAGE_SIZE} mode L")
        return np.asarray(im, dtype=np.float32) / 255.0


def _assert_train_originals(train_dir: str) -> None:
    stems = set()
    for concept_dir in os.listdir(train_dir):
        cls_dir = os.path.join(train_dir, concept_dir)
        if not os.path.isdir(cls_dir):
            continue
        for fname in os.listdir(cls_dir):
            if fname.endswith(".png"):
                stems.add(re.sub(r"_aug\d+\.png$", ".png", fname))
    _assert_count(len(stems), EXPECTED_TRAIN_ORIGINALS, "distinct train originals")


def load_train_set(train_dir: str) -> Split:
    concept_dirs = sorted(d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d)))
    _assert_count(len(concept_dirs), EXPECTED_TRAIN_CONCEPT_DIRS, "train concept dirs")
    images: list[np.ndarray] = []
    labels: list[int] = []
    groups: list[str] = []
    for concept_dir in concept_dirs:
        label = int(concept_dir.split("_")[0])
        cls_dir = os.path.join(train_dir, concept_dir)
        for fname in sorted(os.listdir(cls_dir)):
            if fname.endswith(".png"):
                images.append(_load_image_array(os.path.join(cls_dir, fname)))
                labels.append(label)
                groups.append(re.sub(r"_aug\d+\.png$", ".png", fname))
    _assert_count(len(images), EXPECTED_TRAIN_INSTANCES, "train instances")
    _assert_train_originals(train_dir)
    return Split(np.stack(images), np.array(labels, dtype=np.int64), np.array(groups))


def load_test_set(manifest_path: str, datasets_root: str) -> Split:
    images: list[np.ndarray] = []
    labels: list[int] = []
    with open(manifest_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["structure"] != "complete":
                continue
            images.append(_load_image_array(os.path.join(datasets_root, row["image_path"])))
            labels.append(int(row["class"]))
    _assert_count(len(images), EXPECTED_TEST_IMAGES, "test images")
    return Split(np.stack(images), np.array(labels, dtype=np.int64))


def subsample_split(split: Split, n: int, seed: int) -> Split:
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(split.y), size=min(n, len(split.y)), replace=False)
    groups = split.groups[idx] if split.groups is not None else None
    return Split(split.X[idx], split.y[idx], groups)


def flatten_split(split: Split) -> Split:
    return Split(split.X.reshape(len(split.y), -1), split.y, split.groups)


def to_cnn_split(split: Split) -> Split:
    return Split(split.X.reshape(len(split.y), 1, *IMAGE_SIZE), split.y, split.groups)


# --- Scoring --------------------------------------------------------------

def _score(y_true: np.ndarray, y_pred: np.ndarray) -> SeedMetrics:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, average="macro", zero_division=0
    )
    accuracy = accuracy_score(y_true, y_pred)
    return SeedMetrics(accuracy * 100, precision * 100, recall * 100, f1 * 100, y_pred)


def per_class_frame(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    return pd.DataFrame({
        "class": CLASSES, "precision": precision * 100, "recall": recall * 100,
        "f1_score": f1 * 100, "support": support,
    })


# --- Deterministic models ---------------------------------------------------

def run_deterministic_models(train: Split, test: Split) -> dict[str, SeedMetrics]:
    models: dict[str, Any] = {"svm": SVC(kernel="rbf"), "nearest_centroid": NearestCentroid()}
    for k in KNN_K_VALUES:
        models[f"knn_k{k}"] = KNeighborsClassifier(n_neighbors=k)
    results: dict[str, SeedMetrics] = {}
    for name, model in models.items():
        model.fit(train.X, train.y)
        y_pred = model.predict(test.X)
        results[name] = _score(test.y, y_pred)
    return results


# --- Torch models -----------------------------------------------------------

def build_mlp() -> nn.Module:
    return nn.Sequential(
        nn.Linear(IMAGE_SIZE[0] * IMAGE_SIZE[1], MLP_HIDDEN[0]), nn.ReLU(),
        nn.Linear(MLP_HIDDEN[0], MLP_HIDDEN[1]), nn.ReLU(),
        nn.Linear(MLP_HIDDEN[1], len(CLASSES)),
    )


class CNN(nn.Module):
    # Global average pooling was measured and rejected: it collapses the 25x25
    # map to c2 numbers and throws away spatial layout, capping accuracy at
    # ~21% after 20 epochs versus ~77% for this flatten head (see plan.md).
    def __init__(self) -> None:
        super().__init__()
        c1, c2 = CNN_CHANNELS
        self.block1 = nn.Sequential(nn.Conv2d(1, c1, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2))
        self.block2 = nn.Sequential(nn.Conv2d(c1, c2, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2))
        pooled_h, pooled_w = IMAGE_SIZE[0] // 4, IMAGE_SIZE[1] // 4
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(c2 * pooled_h * pooled_w, CNN_FC_HIDDEN), nn.ReLU(),
            nn.Linear(CNN_FC_HIDDEN, len(CLASSES)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.block1(x)
        x = self.block2(x)
        return self.head(x)


def build_cnn() -> nn.Module:
    return CNN()


def _run_epoch(model: nn.Module, optimizer: torch.optim.Optimizer, split: Split, shuffle_seed: int) -> None:
    model.train()
    rng = np.random.default_rng(shuffle_seed)
    order = rng.permutation(len(split.y))
    X = torch.from_numpy(split.X[order])
    y = torch.from_numpy(split.y[order])
    for start in range(0, len(y), BATCH_SIZE):
        xb, yb = X[start:start + BATCH_SIZE], y[start:start + BATCH_SIZE]
        optimizer.zero_grad()
        loss = _CRITERION(model(xb), yb)
        loss.backward()
        optimizer.step()


def _batched_predictions(model: nn.Module, split: Split) -> np.ndarray:
    # A single forward pass over the full test set would allocate ~11GB for the
    # first conv block's activations alone — batch it.
    model.eval()
    X = torch.from_numpy(split.X)
    preds = np.empty(len(split.y), dtype=np.int64)
    with torch.no_grad():
        for start in range(0, len(split.y), INFERENCE_BATCH_SIZE):
            xb = X[start:start + INFERENCE_BATCH_SIZE]
            preds[start:start + INFERENCE_BATCH_SIZE] = model(xb).argmax(dim=1).numpy()
    return preds


def _evaluate_accuracy(model: nn.Module, split: Split) -> float:
    return float(accuracy_score(split.y, _batched_predictions(model, split)))


def _pick_held_out_originals(train: Split, seed: int) -> set[str]:
    # Held-out originals, not instances: an original and its `_augN` variants
    # must land on the same side, or validation accuracy measures memorization.
    if train.groups is None:
        raise ValueError("train split has no groups; cannot build a grouped validation split")
    rng = np.random.default_rng(seed)
    held_out: set[str] = set()
    for cls in CLASSES:
        cls_originals = np.unique(train.groups[train.y == cls])
        held_out.add(str(rng.choice(cls_originals)))
    return held_out


def _assert_disjoint_originals(fit_groups: np.ndarray, val_groups: np.ndarray) -> None:
    overlap = set(fit_groups) & set(val_groups)
    if overlap:
        raise AssertionError(f"originals present on both sides of the validation split: {overlap}")


def _grouped_val_split(train: Split, seed: int) -> tuple[Split, Split]:
    held_out = _pick_held_out_originals(train, seed)
    _assert_count(len(held_out), VALIDATION_ORIGINALS_HELD_OUT, "validation originals held out")
    groups = train.groups
    if groups is None:
        raise ValueError("train split has no groups; cannot build a grouped validation split")
    val_mask = np.isin(groups, list(held_out))
    fit_mask = ~val_mask
    _assert_disjoint_originals(groups[fit_mask], groups[val_mask])
    fit = Split(train.X[fit_mask], train.y[fit_mask], groups[fit_mask])
    val = Split(train.X[val_mask], train.y[val_mask], groups[val_mask])
    return fit, val


def train_one_epoch(model_fn: Any, train: Split, seed: int) -> nn.Module:
    torch.manual_seed(seed)
    model = model_fn()
    optimizer = torch.optim.Adam(model.parameters(), lr=ADAM_LR)
    _run_epoch(model, optimizer, train, shuffle_seed=seed)
    return model


def train_to_convergence(model_fn: Any, train: Split, seed: int, max_epochs: int) -> tuple[nn.Module, int]:
    fit, val = _grouped_val_split(train, seed)
    torch.manual_seed(seed)
    model = model_fn()
    optimizer = torch.optim.Adam(model.parameters(), lr=ADAM_LR)
    best_state = {k: v.clone() for k, v in model.state_dict().items()}
    best_val_acc, epochs_since_improve, epoch = -1.0, 0, 0
    for epoch in range(max_epochs):
        _run_epoch(model, optimizer, fit, shuffle_seed=seed * 10_000 + epoch)
        val_acc = _evaluate_accuracy(model, val)
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_since_improve = 0
        else:
            epochs_since_improve += 1
        if epochs_since_improve >= CONVERGENCE_PATIENCE:
            break
    model.load_state_dict(best_state)
    return model, epoch + 1


def predict_torch(model: nn.Module, test: Split) -> np.ndarray:
    return _batched_predictions(model, test)


def _run_budget(
    model_fn: Any, train: Split, test: Split, seeds: list[int], converge: bool, max_epochs: int
) -> TorchRunResult:
    seed_metrics: list[SeedMetrics] = []
    epochs_run: list[int] = []
    for seed in seeds:
        if converge:
            model, epochs = train_to_convergence(model_fn, train, seed, max_epochs)
        else:
            model, epochs = train_one_epoch(model_fn, train, seed), 1
        seed_metrics.append(_score(test.y, predict_torch(model, test)))
        epochs_run.append(epochs)
    return TorchRunResult(seed_metrics, epochs_run)


def run_torch_model(
    name: str, model_fn: Any, train: Split, test: Split, seeds: list[int], convergence_max_epochs: int
) -> dict[str, TorchRunResult]:
    return {
        f"{name}_1epoch": _run_budget(model_fn, train, test, seeds, converge=False, max_epochs=1),
        f"{name}_converged": _run_budget(model_fn, train, test, seeds, converge=True, max_epochs=convergence_max_epochs),
    }


# --- Aggregation and artefacts ----------------------------------------------

def aggregate_seed_metrics(seed_metrics: list[SeedMetrics]) -> dict[str, float | None]:
    def mean_sd(values: list[float]) -> tuple[float, float | None]:
        return float(np.mean(values)), (float(np.std(values, ddof=1)) if len(values) > 1 else None)

    accuracy, accuracy_sd = mean_sd([m.accuracy for m in seed_metrics])
    precision, precision_sd = mean_sd([m.precision for m in seed_metrics])
    recall, recall_sd = mean_sd([m.recall for m in seed_metrics])
    f1, f1_sd = mean_sd([m.f1 for m in seed_metrics])
    return {
        "accuracy": accuracy, "accuracy_sd": accuracy_sd,
        "precision": precision, "precision_sd": precision_sd,
        "recall": recall, "recall_sd": recall_sd,
        "f1": f1, "f1_sd": f1_sd,
    }


def build_metrics_rows(
    det_results: dict[str, SeedMetrics], torch_results: dict[str, TorchRunResult], seeds: list[int]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, metrics in det_results.items():
        rows.append({
            "model": name, "budget": "single_fit", "n_seeds": 1,
            "accuracy": metrics.accuracy, "accuracy_sd": None,
            "precision": metrics.precision, "precision_sd": None,
            "recall": metrics.recall, "recall_sd": None,
            "f1": metrics.f1, "f1_sd": None,
        })
    for name, result in torch_results.items():
        base_name, budget = name.rsplit("_", 1)
        row = {"model": base_name, "budget": budget, "n_seeds": len(seeds)}
        row.update(aggregate_seed_metrics(result.seed_metrics))
        rows.append(row)
    return rows


def build_per_class_rows(
    test: Split, det_results: dict[str, SeedMetrics], torch_results: dict[str, TorchRunResult]
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for name, metrics in det_results.items():
        df = per_class_frame(test.y, metrics.y_pred)
        df.insert(0, "budget", "single_fit")
        df.insert(0, "model", name)
        frames.append(df)
    for name, result in torch_results.items():
        base_name, budget = name.rsplit("_", 1)
        seed_frames = [per_class_frame(test.y, m.y_pred) for m in result.seed_metrics]
        df = seed_frames[0].copy()
        for col in ("precision", "recall", "f1_score"):
            df[col] = np.mean([f[col].to_numpy() for f in seed_frames], axis=0)
        df.insert(0, "budget", budget)
        df.insert(0, "model", base_name)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def save_confusion_plot(y_true: np.ndarray, y_pred: np.ndarray, out_path: str) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)
    plt.figure(figsize=(8, 8))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(len(CLASSES))
    plt.xticks(tick_marks, CLASSES)
    plt.yticks(tick_marks, CLASSES)
    thresh = cm.max() / 2.0
    for i, j in np.ndindex(cm.shape):
        plt.text(j, i, format(cm[i, j], "d"), ha="center", color="white" if cm[i, j] > thresh else "black")
    plt.ylabel("True label")
    plt.xlabel("Predicted label")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def save_confusion_plots(
    out_dir: str, test: Split, det_results: dict[str, SeedMetrics], torch_results: dict[str, TorchRunResult]
) -> None:
    for name, metrics in det_results.items():
        save_confusion_plot(test.y, metrics.y_pred, os.path.join(out_dir, f"confusion_{name}.png"))
    for name, result in torch_results.items():
        # Stochastic models: the first seed's predictions stand in as the representative run.
        save_confusion_plot(test.y, result.seed_metrics[0].y_pred, os.path.join(out_dir, f"confusion_{name}.png"))


def repo_git_info() -> dict[str, Any]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_PROJECT_ROOT).stdout.strip()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=_PROJECT_ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_PROJECT_ROOT).stdout.strip() != ""
    return {"commit": commit, "branch": branch, "dirty": dirty}


def package_versions() -> dict[str, str]:
    return {
        "torch": torch.__version__, "scikit_learn": sklearn.__version__,
        "numpy": np.__version__, "pandas": pd.__version__, "pillow": PIL.__version__,
    }


def build_run_config(
    quick: bool, seeds: list[int], resolved_test_count: int,
    torch_results: dict[str, TorchRunResult], convergence_max_epochs: int,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quick": quick,
        "repo_git": repo_git_info(),
        "archive_commit": ARCHIVE_COMMIT,
        "package_versions": package_versions(),
        "seeds": seeds,
        "hyperparameters": {
            "svm": {"kernel": "rbf"},
            "knn": {"k_values": KNN_K_VALUES},
            "nearest_centroid": {},
            "mlp": {"hidden": list(MLP_HIDDEN), "activation": "relu"},
            "cnn": {
                "channels": list(CNN_CHANNELS), "kernel_size": 3, "pool": "2x2_max",
                "head": "flatten_fc128",
            },
            "optimizer": {"name": "adam", "lr": ADAM_LR, "batch_size": BATCH_SIZE},
            "convergence": {
                "max_epochs": convergence_max_epochs,
                "patience": CONVERGENCE_PATIENCE,
                "validation_scheme": "grouped_by_original_one_per_class",
                "validation_originals_held_out": VALIDATION_ORIGINALS_HELD_OUT,
            },
        },
        "epochs_run": {name: result.epochs_run for name, result in torch_results.items()},
        "train_set": {
            "originals": EXPECTED_TRAIN_ORIGINALS,
            "instances": EXPECTED_TRAIN_INSTANCES,
            "concept_dirs": EXPECTED_TRAIN_CONCEPT_DIRS,
        },
        "test_set": {
            "expected_count": EXPECTED_TEST_IMAGES,
            "resolved_count": resolved_test_count,
            "archive_allowed_per_class": ARCHIVE_ALLOWED_PER_CLASS,
            "baseline_run_allowed_per_class": BASELINE_RUN_ALLOWED_PER_CLASS,
            "manifest_delta": MANIFEST_DELTA,
        },
        "isl_reference": {
            "total_submitted": ISL_TOTAL_SUBMITTED,
            "dlq_failures": ISL_DLQ_FAILURES,
            "classified": ISL_CLASSIFIED,
            "correct": ISL_CORRECT,
            "source_run": "run_20260630_235356",
        },
    }


def _format_cell(mean: float, sd: float | None) -> str:
    # A deterministic model has no spread; so does an sd read back from a CSV's
    # empty cell, which arrives as NaN rather than None.
    if sd is None or np.isnan(sd):
        return f"{mean:.2f}"
    return f"{mean:.2f} ± {sd:.2f}"


def build_article_table(metrics_rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Model | Budget | Accuracy (%)[^2] | Precision (%) | Recall (%) | F1 (%) |",
        "|---|---|---|---|---|---|",
    ]
    isl_cell = "91.13 (8,685 classified) / 90.90 (all 8,707)[^1]"
    isl_row = (
        ISL_CORRECT / ISL_TOTAL_SUBMITTED * 100,
        f"| isl | single_fit | {isl_cell} | {ISL_MACRO_PRECISION:.2f}[^3] | "
        f"{ISL_MACRO_RECALL:.2f}[^3] | {ISL_MACRO_F1:.2f}[^3] |",
    )
    rendered = [isl_row]
    for row in metrics_rows:
        rendered.append((row["accuracy"], (
            f"| {row['model']} | {row['budget']} | "
            f"{_format_cell(row['accuracy'], row['accuracy_sd'])} | "
            f"{_format_cell(row['precision'], row['precision_sd'])} | "
            f"{_format_cell(row['recall'], row['recall_sd'])} | "
            f"{_format_cell(row['f1'], row['f1_sd'])} |"
        )))
    # ISL sorts on 90.90, the figure measured over the same full population.
    rendered.sort(key=lambda pair: pair[0], reverse=True)
    for _, line in rendered:
        lines.append(line)
    lines.append("")
    lines.append(
        "[^1]: 8,707 images submitted, 22 failed in the pipeline (skeletonization failures, "
        "recorded as DLQ) and were never scored; 8,685 were classified at 91.13% "
        "(7,915 correct), or 90.90% counting the 22 failures as wrong over all 8,707. "
        "Source: `experiments/run_20260630_235356/`."
    )
    lines.append(
        "[^2]: The four classical/MLP/CNN models above are scored on the archive's "
        "reproducible 8,708 complete-only test images — one more than ISL's 8,707 "
        "(`experiments/run_20260630_235356` read a manifest edited after commit f34b049 "
        "and its config records 8,707). One image out of 8,708 moves accuracy by 0.011pp."
    )
    lines.append(
        "[^3]: Every precision, recall and F1 in this table is a macro average over the ten "
        "digits. ISL's are recomputed from `run_20260630_235356/per_class_metrics.csv` over "
        "the 8,685 images it classified; that run's own `metrics.csv` reports weighted "
        "averages (91.92 / 91.13 / 91.34), which are not comparable with the rows above."
    )
    return "\n".join(lines) + "\n"


# --- Orchestration -----------------------------------------------------------

def default_out_dir(quick: bool) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = "_quick" if quick else ""
    return os.path.join(EXPERIMENTS_DIR, f"classical_baselines_{timestamp}{suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classical baselines (SVM, k-NN, nearest-centroid, MLP, CNN) vs the ISL pipeline."
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Smoke test only: subsample the test set to 200 images, seed 0, 3-epoch convergence cap.",
    )
    parser.add_argument("--out-dir", default=None, help="Override the output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.set_num_threads(min(10, os.cpu_count() or 10))
    seeds = QUICK_SEEDS if args.quick else SEEDS
    convergence_max_epochs = QUICK_CONVERGENCE_EPOCHS if args.quick else CONVERGENCE_MAX_EPOCHS

    datasets_root = ensure_frozen_corpus(CACHE_DIR)
    train_images = load_train_set(os.path.join(datasets_root, "train"))
    test_images = load_test_set(os.path.join(datasets_root, "mnist_all_manifest.csv"), datasets_root)
    if args.quick:
        test_images = subsample_split(test_images, QUICK_TEST_SUBSAMPLE, seed=0)

    train_flat, test_flat = flatten_split(train_images), flatten_split(test_images)
    train_cnn, test_cnn = to_cnn_split(train_images), to_cnn_split(test_images)

    det_results = run_deterministic_models(train_flat, test_flat)
    torch_results = run_torch_model("mlp", build_mlp, train_flat, test_flat, seeds, convergence_max_epochs)
    torch_results.update(run_torch_model("cnn", build_cnn, train_cnn, test_cnn, seeds, convergence_max_epochs))

    out_dir = args.out_dir or default_out_dir(args.quick)
    os.makedirs(out_dir, exist_ok=True)
    write_artefacts(out_dir, test_flat, det_results, torch_results, seeds, args.quick, convergence_max_epochs)


def write_artefacts(
    out_dir: str, test: Split, det_results: dict[str, SeedMetrics],
    torch_results: dict[str, TorchRunResult], seeds: list[int], quick: bool, convergence_max_epochs: int,
) -> None:
    metrics_rows = build_metrics_rows(det_results, torch_results, seeds)
    pd.DataFrame(metrics_rows).to_csv(os.path.join(out_dir, "metrics.csv"), index=False)
    build_per_class_rows(test, det_results, torch_results).to_csv(
        os.path.join(out_dir, "per_class_metrics.csv"), index=False
    )
    save_confusion_plots(out_dir, test, det_results, torch_results)

    run_config = build_run_config(quick, seeds, len(test.y), torch_results, convergence_max_epochs)
    with open(os.path.join(out_dir, "run_config.json"), "w") as f:
        json.dump(run_config, f, indent=2)

    with open(os.path.join(out_dir, "article_table.md"), "w") as f:
        f.write(build_article_table(metrics_rows))

    print(f"Artefacts written to {out_dir}")


if __name__ == "__main__":
    main()
