"""Render Fig 4 — confusion matrix — for the ITSSI 2026 paper.

Reads a run directory produced by the training pipeline and emits a 300 dpi PNG
with fully English titles, axes, colourbar, and tick labels. The matrix has
10 numeric classes (MNIST 0..9) plus a trailing "not classified" column that
merges the classifier's explicit no-match decision with upstream DLQ failures.

Reconstruction:
    support[i]      from per_class_metrics.csv (successful classifications only)
    off_diag[i][j]  from incorrect_results.csv (status=success, predicted=j)
    not_class[i]    from incorrect_results.csv (predicted in {not classified, NaN})
    diag[i]         = support[i] - sum_j off_diag[i][j] - not_class_success[i]
                      (DLQ rows are appended as an additive contribution to the
                      not-classified tail column without changing the diagonal)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CLASSES = list(range(10))
NOT_CLASSIFIED_LABEL = "not classified"
TAIL_COLUMN = "not classified"
FIGSIZE_INCHES = (8.0, 6.8)
DPI = 300


def build_matrix(run_dir: Path) -> tuple[np.ndarray, int, int]:
    supports = pd.read_csv(run_dir / "per_class_metrics.csv").set_index("class")["support"]
    incorrect = pd.read_csv(run_dir / "incorrect_results.csv")

    n_cls = len(CLASSES)
    matrix = np.zeros((n_cls, n_cls + 1), dtype=int)

    success_rows = incorrect[incorrect["status"] == "success"]
    error_rows = incorrect[incorrect["status"] != "success"]

    off_diag_numeric = np.zeros(n_cls, dtype=int)
    not_class_success = np.zeros(n_cls, dtype=int)

    for _, row in success_rows.iterrows():
        i = int(row["expected"])
        pred = str(row["predicted"]).strip()
        if pred == NOT_CLASSIFIED_LABEL:
            matrix[i, n_cls] += 1
            not_class_success[i] += 1
        else:
            matrix[i, int(pred)] += 1
            off_diag_numeric[i] += 1

    for _, row in error_rows.iterrows():
        i = int(row["expected"])
        matrix[i, n_cls] += 1

    for i in CLASSES:
        matrix[i, i] = int(supports.loc[i]) - off_diag_numeric[i] - not_class_success[i]

    classified_total = int(supports.sum())
    submitted_total = int(matrix.sum())
    return matrix, classified_total, submitted_total


def render(matrix: np.ndarray, classified: int, out_path: Path) -> None:
    column_labels = [str(c) for c in CLASSES] + [TAIL_COLUMN]
    row_labels = [str(c) for c in CLASSES]

    fig, ax = plt.subplots(figsize=FIGSIZE_INCHES)
    im = ax.imshow(matrix, cmap="Blues", aspect="auto")

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Number of images", fontsize=11)

    ax.set_xticks(np.arange(len(column_labels)))
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_xticklabels(column_labels, rotation=40, ha="right", fontsize=10)
    ax.set_yticklabels(row_labels, fontsize=10)

    ax.set_xlabel("Predicted class", fontsize=12)
    ax.set_ylabel("Expected class", fontsize=12)
    ax.set_title(
        f"Confusion matrix — complete-only MNIST ({classified} classified images)",
        fontsize=12,
        pad=10,
    )

    threshold = matrix.max() / 2.0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                f"{value:d}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if value > threshold else "black",
            )

    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="Run directory")
    parser.add_argument("--out", required=True, type=Path, help="Output PNG path")
    args = parser.parse_args()

    matrix, classified, submitted = build_matrix(args.run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    render(matrix, classified, args.out)
    print(
        f"Wrote {args.out} at {DPI} dpi — {classified} classified / {submitted} submitted "
        f"({submitted - classified} DLQ + not-classified)."
    )


if __name__ == "__main__":
    main()
