# Experiment Findings: naturalagi-normalizer-tuning-cmaes-v2

**Date:** 2026-04-03
**Analyst:** Classification Analyst Agent

---

## TL;DR

- Best proxy accuracy: **79.85% [QUICK, 25% sample, fold 1]** (trial #133 of 200)
- Full validation accuracy: **77.12% [FULL, 7,794 images, 10 classes]** (run_20260403_033532, 20 DLQ)
- **Critical fold bias**: all top-5 trials land on fold 1 (mean 78.47%) vs fold 0 (mean 76.68%) -- a ~1.8pp systematic offset that inflates reported proxy accuracy
- `diagnostic_weight_epsilon` is the most important parameter (fANOVA: 25.3%), followed by `norm_distance_to_centroid` (15.3%)
- Most normalizers show wide effective ranges with no sharp optima -- the objective landscape is relatively flat in normalizer space
- Search space is adequately sized: no best-trial parameter sits at a boundary

---

## 1. Study Configuration

| Field | Value |
|-------|-------|
| Study name | `naturalagi-normalizer-tuning-cmaes-v2` |
| DB path | `src/training/experiments/naturalagi-normalizer-tuning-cmaes-v2.db` |
| Sampler | CmaEsSampler (seed=42, n_startup_trials=20, x0 seeded from trial #185 of `naturalagi-dynamic-feature-selection`) |
| Direction | maximize |
| Objective | `accuracy_score(y_true, y_pred)` on 25% sample, K=4 folds (trial_number % 4) |
| n_trials | 200 budgeted, 200 completed, 0 failed, 0 pruned |
| Classes | 10 (0-9) |
| Sample fraction | 0.25 |
| Total compute | ~10.2 hours wall-clock (200 trials x ~3 min median) |
| Date range | 2026-04-02 17:22 to 2026-04-03 03:35 |

### Search Space (13D continuous)

**Tuned parameters (12 normalizers + 1 epsilon):**

| Parameter | Type | Range | Seed (x0) |
|-----------|------|-------|------------|
| `diagnostic_weight_epsilon` | float | [0.5, 2.0] | 1.0 |
| `norm_normalized_x` | float | [1.0, 10.0] | 3.75 |
| `norm_normalized_y` | float | [1.0, 10.0] | 3.67 |
| `norm_distance_to_centroid` | float | [0.3, 5.0] | 1.0 |
| `norm_horizontal_direction` | float | [1.0, 8.0] | 3.11 |
| `norm_vertical_direction` | float | [1.0, 8.0] | 3.11 |
| `norm_angle_with_ox` | float | [30.0, 360.0] | 279.4 |
| `norm_junction_angle_min` | float | [30.0, 360.0] | 180.0 |
| `norm_length_ratio_to_max` | float | [0.3, 5.0] | 1.0 |
| `norm_eccentricity` | float | [2.0, 20.0] | 10.0 |
| `norm_avg_neighbor_vector_length` | float | [10.0, 100.0] | 50.0 |
| `norm_neighbor_endpoint_count` | float | [1.0, 10.0] | 3.0 |
| `norm_neighbor_junction_count` | float | [1.0, 10.0] | 3.0 |

**Fixed parameters:**

| Parameter | Value | Source |
|-----------|-------|--------|
| `ged_timeout` | 8.72 | trial #185 of feature-selection |
| `skeletonization_threshold` | 110 | trial #185 |
| `simplification_epsilon` | 4.55 | trial #185 |
| `comparison_method` | "ged" | fixed |
| `node_costs.NO_COST` | 0.0 | trial #185 |
| `node_costs.MINOR` | 0.254 | trial #185 |
| `node_costs.GENERAL` | 0.450 | trial #185 |
| `node_costs.SEVERE` | 0.726 | trial #185 |
| `node_costs.NO_MATCH` | 1.304 | trial #185 |
| `node_costs.IMPOSSIBLE` | 6.681 | trial #185 |
| `is_endpoint` normalizer | 1.0 | fixed (binary) |
| `is_corner` normalizer | 1.0 | fixed (binary) |

**Fixed feature set (14 features):**
`normalized_x`, `normalized_y`, `distance_to_centroid`, `horizontal_direction`, `vertical_direction`, `angle_with_ox`, `junction_angle_min`, `is_endpoint`, `is_corner`, `length_ratio_to_max`, `eccentricity`, `avg_neighbor_vector_length`, `neighbor_endpoint_count`, `neighbor_junction_count`

---

## 2. Results Summary

### Objective Distribution (200 completed trials)

| Statistic | Value |
|-----------|-------|
| Min | 75.39% |
| Q1 (25th pctl) | 77.03% |
| Median | 77.52% |
| Mean | 77.56% |
| Q3 (75th pctl) | 78.18% |
| Max | 79.85% |
| Stdev | 0.80pp |
| Total range | 4.46pp |

### Best Trial (#133)

| Parameter | Value |
|-----------|-------|
| Accuracy | **79.85% [QUICK, 25% sample, fold 1]** |
| `diagnostic_weight_epsilon` | 1.055 |
| `norm_normalized_x` | 2.917 |
| `norm_normalized_y` | 4.123 |
| `norm_distance_to_centroid` | 1.631 |
| `norm_horizontal_direction` | 1.684 |
| `norm_vertical_direction` | 3.125 |
| `norm_angle_with_ox` | 164.4 |
| `norm_junction_angle_min` | 201.0 |
| `norm_length_ratio_to_max` | 2.809 |
| `norm_eccentricity` | 14.684 |
| `norm_avg_neighbor_vector_length` | 65.781 |
| `norm_neighbor_endpoint_count` | 5.964 |
| `norm_neighbor_junction_count` | 3.934 |
| Duration | 160s |

### Worst Trial (#80)

| Parameter | Value |
|-----------|-------|
| Accuracy | **75.39% [QUICK, 25% sample, fold 0]** |
| `diagnostic_weight_epsilon` | 0.980 |
| `norm_eccentricity` | 7.115 |
| Duration | 167s |

See `top_trials.csv` and `bottom_trials.csv` for full parameter listings.

### Full Validation of Best Trial

| Metric | Value |
|--------|-------|
| Accuracy | **77.12% [FULL, 7,794 images, 10 classes]** |
| Total images | 7,814 |
| DLQ failures | 20 (0.26%) |
| Successfully classified | 7,794 |
| Precision (macro) | 79.25% |
| Recall (macro) | 77.12% |
| F1 (macro) | 77.09% |
| Run ID | `run_20260403_033532` |

**Per-class recall at best configuration [FULL]:**

| Class | Recall | Precision | F1 | Support |
|-------|--------|-----------|-----|---------|
| 0 | 79.0% | 100.0% | 88.3% | 1,000 |
| 1 | 96.6% | 77.2% | 85.8% | 995 |
| 2 | 60.0% | 76.5% | 67.3% | 946 |
| 3 | 55.7% | 73.2% | 63.3% | 982 |
| 4 | 79.2% | 70.5% | 74.6% | 495 |
| 5 | 50.5% | 75.6% | 60.6% | 479 |
| 6 | 86.3% | 73.5% | 79.4% | 753 |
| 7 | 89.9% | 65.9% | 76.1% | 989 |
| 8 | 73.4% | 96.8% | 83.5% | 372 |
| 9 | 89.3% | 87.9% | 88.6% | 783 |

Classes 3 (55.7%) and 5 (50.5%) have recall below 60%. Class 2 at 60.0% is also weak.

---

## 3. Parameter Importances (fANOVA)

Computed over 200 completed trials. Reliable threshold met (>>20 trials).

| Parameter | Importance | Rank |
|-----------|-----------|------|
| `diagnostic_weight_epsilon` | **0.2528** | 1 |
| `norm_distance_to_centroid` | **0.1530** | 2 |
| `norm_eccentricity` | 0.0914 | 3 |
| `norm_neighbor_endpoint_count` | 0.0675 | 4 |
| `norm_normalized_x` | 0.0633 | 5 |
| `norm_normalized_y` | 0.0617 | 6 |
| `norm_length_ratio_to_max` | 0.0595 | 7 |
| `norm_neighbor_junction_count` | 0.0560 | 8 |
| `norm_vertical_direction` | 0.0559 | 9 |
| `norm_junction_angle_min` | 0.0390 | 10 |
| `norm_horizontal_direction` | 0.0367 | 11 |
| `norm_angle_with_ox` | 0.0324 | 12 |
| `norm_avg_neighbor_vector_length` | 0.0310 | 13 |

**Key observations:**
- `diagnostic_weight_epsilon` alone explains 25.3% of objective variance. This is not a normalizer but the epsilon controlling per-concept diagnostic weights.
- `norm_distance_to_centroid` is the most important normalizer at 15.3%.
- The bottom 4 parameters (`norm_junction_angle_min`, `norm_horizontal_direction`, `norm_angle_with_ox`, `norm_avg_neighbor_vector_length`) collectively explain only 13.9% -- they are relatively insensitive in this search space.
- No single normalizer exceeds 16% importance. The landscape is distributed across multiple parameters with no single dominant knob.

---

## 4. Convergence Analysis

### Running Best Progression

| Trial | Accuracy | % Through Budget |
|-------|----------|-----------------|
| 1 | 78.46% | 0.5% |
| 3 | 78.58% | 1.5% |
| 9 | 78.69% | 4.5% |
| 17 | 79.01% | 8.5% |
| 25 | 79.05% | 12.5% |
| 65 | 79.50% | 32.5% |
| **133** | **79.85%** | **66.5%** |

- Last improvement at trial 133 (66.5% through budget).
- No improvement in the final 67 trials (33.5% of budget).
- Last-25% (trials 150-199): mean 77.59%, stdev 0.71pp, max 79.32%.
- **[Inference]**: The study shows convergence behavior. The final third of the budget produced no improvement, and objective variance remained stable at 0.71pp.

### Best-per-Quarter Analysis

| Quarter | Trials | Best Accuracy |
|---------|--------|--------------|
| Q1 (0-49) | 0-49 | 79.05% |
| Q2 (50-99) | 50-99 | 79.50% |
| Q3 (100-149) | 100-149 | **79.85%** |
| Q4 (150-199) | 150-199 | 79.32% |

The best value improved from Q1 to Q3 but Q4 did not surpass Q3.

---

## 5. K-Fold Bias (CRITICAL)

This study uses `fold = trial.number % 4` with `random.seed(fold)` to select a different 25% sample per fold. The fold assignment is deterministic and cyclic.

### Per-Fold Statistics

| Fold | Trials | Mean Accuracy | Stdev | Max Accuracy |
|------|--------|--------------|-------|-------------|
| 0 | 50 | 76.68% | 0.54pp | 77.73% |
| 1 | 50 | **78.47%** | 0.47pp | **79.85%** |
| 2 | 50 | 77.39% | 0.41pp | 78.20% |
| 3 | 50 | 77.70% | 0.51pp | 78.62% |

**Fold 1 is systematically 1.8pp higher than fold 0, and 0.8-1.1pp higher than folds 2-3.**

The top 5 trials by objective value are ALL on fold 1:
- #133: 79.85% (fold 1)
- #65: 79.50% (fold 1)
- #137: 79.32% (fold 1)
- #189: 79.32% (fold 1)
- #117: 79.10% (fold 1)

Cross-fold spread around trial #133: nearby trials with similar parameters score 76.57-78.25% on other folds, vs 79.85% on fold 1 -- a ~2pp gap.

**[Inference]**: The 25% sample selected by `random.seed(1)` (fold 1) is systematically easier than other folds. This means the reported best accuracy of 79.85% is inflated by approximately 1-2pp relative to the expected performance on a random 25% sample. The full validation at 77.12% is consistent with this interpretation (2.7pp drop from proxy).

**[Inference]**: The CMA-ES sampler optimizes a noisy objective where fold assignment adds ~1.8pp systematic variance. Since fold cycles every 4 trials, the sampler cannot distinguish parameter improvements from fold luck. This may have caused CMA-ES to converge toward configurations that happen to perform well on fold 1 rather than configurations that are broadly best across all folds.

---

## 6. Per-Parameter Effective Ranges

Top-quartile threshold: >= 78.18% (50 trials). Bottom-quartile threshold: <= 77.03% (51 trials).

### `diagnostic_weight_epsilon` (importance: 0.253)

| Metric | Top-Q | Bottom-Q | Search Space |
|--------|-------|----------|-------------|
| Min | 0.672 | 0.508 | 0.5 |
| Median | 1.050 | 1.062 | -- |
| Max | 1.391 | 1.909 | 2.0 |
| Best trial | 1.055 | -- | -- |

- Top-quartile confined to [0.67, 1.39]; bottom-quartile extends to 1.91.
- 7 bottom-Q trials have epsilon > 1.39 (above top-Q max); only 1 bottom-Q trial below top-Q min.
- **[Inference]**: Values above ~1.4 consistently underperform. The effective range is approximately [0.7, 1.4], centered near 1.05.

### `norm_distance_to_centroid` (importance: 0.153)

| Metric | Top-Q | Bottom-Q | Search Space |
|--------|-------|----------|-------------|
| Min | 0.360 | 0.381 | 0.3 |
| Median | 1.408 | 1.510 | -- |
| Max | 4.095 | 4.633 | 5.0 |
| Best trial | 1.631 | -- | -- |

- Ranges nearly identical between top and bottom quartiles. The importance (15.3%) may come from interaction effects rather than a clear good/bad split.

### `norm_eccentricity` (importance: 0.091)

| Metric | Top-Q | Bottom-Q | Search Space |
|--------|-------|----------|-------------|
| Min | 4.341 | 2.566 | 2.0 |
| Median | 12.879 | 12.764 | -- |
| Max | 18.861 | 18.199 | 20.0 |
| Best trial | 14.684 | -- | -- |

- 1 bottom-Q trial at eccentricity 2.566 (below top-Q min of 4.341).
- **[Inference]**: Very low eccentricity values (<4) may be harmful, but the evidence is thin (1 trial).

### `norm_normalized_x` (importance: 0.063)

| Metric | Top-Q | Bottom-Q | Search Space |
|--------|-------|----------|-------------|
| Min | 1.602 | 1.145 | 1.0 |
| Median | 3.456 | 3.156 | -- |
| Max | 9.033 | 9.556 | 10.0 |
| Best trial | 2.917 | -- | -- |

- 3 bottom-Q trials below top-Q min (1.145-1.537); 2 bottom-Q trials above top-Q max (9.053-9.556).
- **[Inference]**: Extreme values (<1.6 or >9.0) appear only in bottom quartile, but sample sizes are small.

### `norm_horizontal_direction` (importance: 0.037)

| Metric | Top-Q | Bottom-Q | Search Space |
|--------|-------|----------|-------------|
| Min | 1.230 | 1.030 | 1.0 |
| Median | 2.404 | 2.602 | -- |
| Max | 7.908 | 6.721 | 8.0 |
| Best trial | 1.684 | -- | -- |

- Best trial at 1.684, only 10% from the lower bound. 3 bottom-Q trials below 1.23.
- Low importance (3.7%) -- the parameter is relatively insensitive.

### Remaining Parameters

For `norm_normalized_y`, `norm_vertical_direction`, `norm_angle_with_ox`, `norm_junction_angle_min`, `norm_length_ratio_to_max`, `norm_avg_neighbor_vector_length`, `norm_neighbor_endpoint_count`, `norm_neighbor_junction_count`: the top-quartile and bottom-quartile ranges overlap extensively. No clear separation is visible. See `effective_ranges.csv` for complete data.

---

## 7. Dead Zones

Parameters or combinations that consistently appear in bottom-quartile trials but not in top-quartile:

### High-confidence dead zones

1. **`diagnostic_weight_epsilon` > 1.4**: 7 bottom-Q trials in [1.39, 1.91]; 0 top-Q trials above 1.39. Combined with the #1 fANOVA importance, this is the strongest dead zone signal in the study.

### Low-confidence dead zones (thin evidence)

2. **`norm_normalized_x` extremes**: 3 bottom-Q trials below 1.6, 2 above 9.0 -- all outside top-Q range. But importance is only 6.3%.
3. **`norm_eccentricity` < 4.3**: 1 bottom-Q trial at 2.566 below top-Q min 4.341. Insufficient evidence.
4. **`norm_angle_with_ox` extremes**: 3 bottom-Q trials below 51 (vs top-Q min 51.5), 3 above 309 (vs top-Q max 309). Suggests avoiding the extreme ends of the angular normalizer space.
5. **`norm_vertical_direction` < 1.9**: 3 bottom-Q trials in [1.45, 1.77] below top-Q min 1.86.

### Notable non-dead-zone

Most normalizer parameters show heavily overlapping top-Q and bottom-Q ranges. This indicates the objective landscape is relatively flat with respect to individual normalizer values, and the 4.46pp total range across 200 trials is driven by interactions between parameters (and fold assignment) rather than any single normalizer being critically wrong.

---

## 8. Open Questions

1. **[Hypothesis]** The fold bias (~1.8pp) may mask real parameter effects. A study with stratified cross-validation (averaging all 4 folds per trial) would produce a less noisy objective, potentially allowing the sampler to find better configurations. The cost is 4x compute per trial.

2. **[Hypothesis]** The flat landscape for most normalizers may indicate that the diagnostic weight system (controlled by `diagnostic_weight_epsilon`) absorbs much of the normalizer tuning effect -- when per-concept-node weights adjust based on feature range widths, the normalizer values become less critical.

3. **[Hypothesis]** The 2.7pp proxy-to-full drop (79.85% -> 77.12%) exceeds the typical ~2pp drop observed in prior studies. This may be partly explained by the fold bias (the best trial was evaluated on the "easiest" fold).

4. **[Hypothesis]** `norm_horizontal_direction` best value at 1.684 (10% from lower bound of 1.0) -- the true optimum may be below 1.0. Extending the lower bound could be worth testing if horizontal_direction sensitivity is investigated.

5. **[Hypothesis]** Per-class recall for classes 3 (55.7%) and 5 (50.5%) at the best configuration suggests that normalizer tuning alone cannot resolve the structural confusion patterns for these classes. Different concept structures or additional features may be needed.

---

## 9. Artifacts

| File | Description |
|------|-------------|
| `findings.md` | This document |
| `objective_distribution.csv` | All 200 completed trials: trial_number, value, fold, and all 13 parameters |
| `top_trials.csv` | Top 10 trials by objective value with full parameters and duration |
| `bottom_trials.csv` | Bottom 10 trials by objective value with full parameters and duration |
| `parameter_importances.csv` | fANOVA importance scores for all 13 parameters |
| `effective_ranges.csv` | Per-parameter quartile statistics: search bounds, top-Q/bottom-Q min/median/max, best value |

Study database: `src/training/experiments/naturalagi-normalizer-tuning-cmaes-v2.db`
