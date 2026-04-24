"""One-shot driver: full-suite baseline re-measurement against
`datasets/mnist_all/` filtered by `structure=complete` (8,707 images).

Re-runs the exp_059 H1 winning config (MINOR=0.65, Family E removal of the
per-feature cost cap, log-complexity prior) to establish a comparable
baseline for the new default evaluation dataset.
"""

from __future__ import annotations

from evaluation import test_mnist_all

PARAMS = {
    "ged_timeout": 15,
    "skeletonization_threshold": 110,
    "simplification_epsilon": 4.55,
    "comparison_method": "ged",
    "diagnostic_weight_epsilon": 1.0,
    "node_costs": {
        "NO_COST": 0.0,
        "MINOR": 0.65,
        "GENERAL": 0.45,
        "SEVERE": 0.726,
        "NO_MATCH": 1.304,
        "IMPOSSIBLE": 6.681,
    },
    "features": [
        "normalized_x", "normalized_y",
        "distance_to_centroid",
        "horizontal_direction", "vertical_direction", "angle_with_ox",
        "junction_angle_min",
        "is_endpoint", "is_corner",
        "length_ratio_to_max",
        "eccentricity",
        "avg_neighbor_vector_length",
        "neighbor_endpoint_count", "neighbor_junction_count",
    ],
}

DESCRIPTION = (
    "Baseline re-measurement: exp_059 H1 config (MINOR=0.65) on the new default "
    "`datasets/mnist_all/` filtered to structure=complete (8,707 images). "
    "Establishes a comparable baseline for future hypotheses now that evaluation "
    "reads the annotated dataset by default."
)

if __name__ == "__main__":
    results, y_true, y_pred, run_dir = test_mnist_all(
        classes=list(range(10)),
        params=PARAMS,
        sample_fraction=1.0,
        description=DESCRIPTION,
    )
    print(f"\nDONE. run_dir={run_dir}")
