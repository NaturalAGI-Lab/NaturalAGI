"""
Evaluation utilities: batch testing, metrics, confusion matrix.
Extracted from training.ipynb.
"""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from tqdm.notebook import tqdm

from training.classifier import classify_image
import uuid

logger = logging.getLogger(__name__)

CONFUSION_MATRIX_FIGSIZE = (10, 7)


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
    results_dir: str = "training_results",
    nuclio_volume_path_template: str = "/opt/nuclio/shared_storage/generated_samples/mnist_{cls}/test",
    local_path_template: str = "./tests/generated_samples/mnist_{cls}/test",
    kafka_bootstrap_servers: str = "localhost:29092",
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Test MNIST classification for all given classes and compute overall metrics.

    Args:
        classes: List of digit classes to test.
        params: Extra classification parameters (e.g. ged_timeout).
        sample_fraction: Fraction of test images to use (1.0 = all).
        results_dir: Directory where run results are saved.
        nuclio_volume_path_template: Path template for Nuclio-accessible images.
        local_path_template: Path template for local image lookup.
        kafka_bootstrap_servers: Kafka connection string.

    Returns:
        (all_results, y_true, y_pred)
    """
    all_results: Dict[str, Any] = {}
    all_y_true: List[str] = []
    all_y_pred: List[str] = []
    incorrect_results: List[Dict[str, Any]] = []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(results_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    # Collect images per class
    test_images_per_class: Dict[int, List[str]] = {}
    total_images = 0
    for cls in classes:
        local_folder = local_path_template.format(cls=cls)
        images = [f for f in os.listdir(local_folder) if f.endswith((".png", ".jpg", ".jpeg"))]
        if sample_fraction < 1.0:
            images = random.sample(images, max(1, int(len(images) * sample_fraction)))
        test_images_per_class[cls] = images
        total_images += len(images)

    if sample_fraction < 1.0:
        print(f"Fast mode: {sample_fraction*100:.0f}% of data ({total_images} images)")

    pbar = tqdm(total=total_images, desc="Testing MNIST classification", leave=True)

    for cls in classes:
        pbar.set_description(f"Testing class {cls}")
        nuclio_folder = nuclio_volume_path_template.format(cls=cls)
        expected_name = str(cls)

        for fname in test_images_per_class[cls]:
            image_file = os.path.join(nuclio_folder, fname)
            params["image_id"] = str(uuid.uuid4())

            result = classify_image(
                image_file,
                expected_name=expected_name,
                params=params,
                kafka_bootstrap_servers=kafka_bootstrap_servers,
            )
            all_results[image_file] = result

            if result["status"] == "success":
                all_y_true.append(result["expected"])
                all_y_pred.append(result["predicted"])
                if not result["correct"]:
                    incorrect_results.append(result)
            else:
                incorrect_results.append(result)

            pbar.update(1)

    pbar.close()

    if incorrect_results:
        pd.DataFrame(incorrect_results).to_csv(
            os.path.join(run_dir, "incorrect_results.csv"), index=False
        )

    if all_y_true:
        labels = sorted(set(all_y_true + all_y_pred))
        overall_precision, overall_recall, overall_f1, _ = precision_recall_fscore_support(
            all_y_true, all_y_pred, labels=labels, average="weighted"
        )
        overall_accuracy = accuracy_score(all_y_true, all_y_pred)
        class_precision, class_recall, class_f1, support = precision_recall_fscore_support(
            all_y_true, all_y_pred, labels=labels, average=None
        )

        _save_metrics(
            run_dir, total_images,
            sum(1 for r in incorrect_results if r.get("error") == "DLQ"),
            len(all_y_true),
            overall_accuracy, overall_precision, overall_recall, overall_f1,
            labels, class_precision, class_recall, class_f1, support,
        )

        cm = confusion_matrix(all_y_true, all_y_pred, labels=labels)
        save_confusion_matrix(cm, labels, run_dir)
        print(f"\nResults saved to: {run_dir}")
    else:
        logger.warning("No successful classifications to calculate metrics.")

    return all_results, all_y_true, all_y_pred


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
        if lbl not in ("error", "timeout")
    ]
    pd.DataFrame(per_class).to_csv(os.path.join(run_dir, "per_class_metrics.csv"), index=False)

    print(f"\n{'='*50}")
    print(f"Total: {total}  |  DLQ: {failed_dlq}  |  Success: {successful}")
    print(f"Accuracy:  {overall_accuracy*100:.2f}%")
    print(f"Precision: {overall_precision*100:.2f}%")
    print(f"Recall:    {overall_recall*100:.2f}%")
    print(f"F1:        {overall_f1*100:.2f}%")
    print(f"{'='*50}")
