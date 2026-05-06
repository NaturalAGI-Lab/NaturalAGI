# Run Analysis: run_20260410_153216

**Date:** 2026-04-10
**Analyst:** Classification Analyst (manual)
**MLflow Run ID:** `1c0b6867ba5a4beb971b78ca046f8148`
**MLflow Experiment:** 4

---

## TL;DR

- **Accuracy: 74.12% [FULL, 12,000 images, 10 classes]** — full MNIST test set validation of CMA-ES v2 best trial #133 (79.85% proxy on 25% sample)
- **5.7pp proxy-to-full drop** (79.85% → 74.12%), significantly exceeding the ~2pp typical drop and the 2.7pp drop observed in the prior 7,794-image validation
- **Concept 7_1 is the dominant false attractor**: wins 690 incorrect predictions (23.8% of all errors), passing preprocessing in 2,025 error cases
- **1,286 near-misses** (correct concept available but lost by < 3% margin) — 44.3% of all errors are marginal discrimination failures
- **191 unclassifiable images** (1.6%), dominated by class 8 (130) — preprocessing filters reject all 13 concepts
- Classes 3 (56.0%), 5 (54.1%), and 8 (58.2%) have recall below 60% — structural confusion problems unresolved by normalizer tuning
- Winning similarity for incorrect predictions is extremely compressed: p10=0.772, p90=0.805 — the system cannot spread concepts apart

---

## 1. Run Configuration

| Field | Value |
|-------|-------|
| Run name | `run_20260410_153216` |
| Source | `training.ipynb` |
| Git commit | `3aa11b64` (dirty) |
| Git branch | `feat/graph-features-and-cleanup` |
| Common lib version | 0.1.0 |
| Comparison method | GED |
| GED timeout | 8.72s |
| Skeletonization threshold | 110 |
| Simplification epsilon | 4.55 |
| Diagnostic weight epsilon | 1.055 |
| Dataset | MNIST test, 12,000 images, 10 classes (1,184–1,200 per class) |
| Sample fraction | 1.0 (full) |
| Duration | ~57 minutes |
| DLQ failures | 54 (0.45%) |

### Feature Set (14 features)

`normalized_x`, `normalized_y`, `distance_to_centroid`, `horizontal_direction`, `vertical_direction`, `angle_with_ox`, `junction_angle_min`, `is_endpoint`, `is_corner`, `length_ratio_to_max`, `eccentricity`, `avg_neighbor_vector_length`, `neighbor_endpoint_count`, `neighbor_junction_count`

### Property Normalizers

| Feature | Normalizer |
|---------|-----------|
| normalized_x | 2.917 |
| normalized_y | 4.123 |
| distance_to_centroid | 1.631 |
| horizontal_direction | 1.684 |
| vertical_direction | 3.125 |
| angle_with_ox | 164.395 |
| junction_angle_min | 201.041 |
| is_endpoint | 1.0 (binary) |
| is_corner | 1.0 (binary) |
| length_ratio_to_max | 2.809 |
| eccentricity | 14.684 |
| avg_neighbor_vector_length | 65.781 |
| neighbor_endpoint_count | 5.964 |
| neighbor_junction_count | 3.934 |

### Node Costs

| Level | Cost |
|-------|------|
| NO_COST | 0.000 |
| MINOR | 0.254 |
| GENERAL | 0.450 |
| SEVERE | 0.726 |
| NO_MATCH | 1.304 |
| IMPOSSIBLE | 6.681 |

### Concepts (13 concepts, node counts)

| Concept | Nodes |
|---------|-------|
| 0_1 | 10 |
| 1_1 | 7 |
| 1_3 | 3 |
| 2_1 | 7 |
| 2_2 | 12 |
| 3_1 | 11 |
| 4_1 | 8 |
| 4_2 | 7 |
| 5_1 | 7 |
| 6_1 | 10 |
| 7_1 | 5 |
| 8_1 | 13 |
| 9_2 | 8 |

---

## 2. Overall Metrics

| Metric | Value |
|--------|-------|
| Total images | 12,000 |
| DLQ failures | 54 (0.45%) |
| Successfully classified | 11,946 |
| **Accuracy** | **74.12%** |
| Precision (macro) | 78.04% |
| Recall (macro) | 74.12% |
| F1 (macro) | 74.49% |

---

## 3. Per-Class Metrics

| Class | Precision | Recall | F1 | Support | Errors |
|-------|-----------|--------|-----|---------|--------|
| 0 | 99.9% | 79.4% | 88.5% | 1,200 | 247 |
| 1 | 71.4% | 96.0% | 81.9% | 1,196 | 52 |
| 2 | 73.2% | 61.8% | 67.0% | 1,196 | 461 |
| 3 | 60.9% | 56.0% | 58.4% | 1,195 | 531 |
| 4 | 77.7% | 79.0% | 78.3% | 1,197 | 254 |
| 5 | 86.0% | 54.1% | 66.5% | 1,184 | 559 |
| 6 | 66.2% | 81.0% | 72.8% | 1,197 | 231 |
| 7 | 61.0% | 90.1% | 72.8% | 1,197 | 121 |
| 8 | 98.3% | 58.2% | 73.1% | 1,196 | 504 |
| 9 | 85.8% | 85.4% | 85.6% | 1,188 | 186 |

### Class Archetypes

**High-recall, low-precision (attractors)**: Classes 1 (96.0%R, 71.4%P) and 7 (90.1%R, 61.0%P) pull in images from other classes.

**High-precision, low-recall (underclassified)**: Classes 0 (99.9%P, 79.4%R), 5 (86.0%P, 54.1%R), and 8 (98.3%P, 58.2%R) are precise when they win but fail to claim many of their own images.

**Balanced**: Classes 4 (77.7%P, 79.0%R) and 9 (85.8%P, 85.4%R) are the best-performing classes.

**Weak overall**: Class 3 (60.9%P, 56.0%R) has both low precision and low recall.

---

## 4. Confusion Analysis

### Top 15 Confusion Pairs

| True → Predicted | Count | % of True Class |
|------------------|-------|-----------------|
| 5 → 3 | 394 | 33.3% of class 5 |
| 3 → 7 | 252 | 21.1% of class 3 |
| 8 → 6 | 239 | 20.0% of class 8 |
| 2 → 7 | 178 | 14.9% of class 2 |
| 2 → 6 | 152 | 12.7% of class 2 |
| 8 → NC | 130 | 10.9% of class 8 |
| 4 → 7 | 118 | 9.9% of class 4 |
| 3 → 2 | 114 | 9.5% of class 3 |
| 6 → 1 | 98 | 8.2% of class 6 |
| 4 → 1 | 85 | 7.1% of class 4 |
| 9 → 4 | 78 | 6.6% of class 9 |
| 0 → 6 | 69 | 5.8% of class 0 |
| 0 → 1 | 68 | 5.7% of class 0 |
| 3 → 5 | 54 | 4.5% of class 3 |
| 8 → 9 | 53 | 4.4% of class 8 |

### Confusion Clusters

**Cluster 1 — Class 7 as false attractor** (→7 total: 252+178+118+37+38 = 623):
Classes 3, 2, 4, 5, and 9 all lose images to class 7. Concept 7_1 has only 5 nodes — the smallest concept — making it structurally compatible with many images that pass preprocessing. It wins 690 incorrect predictions out of 2,025 eligible error cases (34.1% hit rate when eligible).

**Cluster 2 — Closed-curve confusion** (0↔6↔8↔9):
- 8→6: 239, 0→6: 69, 6→9: 21, 9→6: 15, 8→9: 53
- These classes share loop/closed-curve topology, and the system cannot differentiate them by GED alone.

**Cluster 3 — Class 5→3 dominance** (394 images, 33.3% of class 5):
The single largest confusion pair. Class 5 images are frequently mistaken for class 3. Concept 3_1 wins 429 incorrect predictions total.

**Cluster 4 — Low-complexity attraction** (→1 total: 98+85+38+32+39 = 292):
Classes 6, 4, 7, 9, and 2 lose images to class 1. Concepts 1_1 (7 nodes) and 1_3 (3 nodes) are small, acting as catch-alls.

### Not Classified (191 images)

| Class | Count |
|-------|-------|
| 8 | 130 (68.1%) |
| 6 | 28 |
| 0 | 16 |
| 2 | 7 |
| 9 | 4 |
| 5 | 3 |
| 4 | 2 |
| 7 | 1 |

Class 8 dominates the not-classified category. These images fail preprocessing against all 13 concepts. The primary preprocessing failure reasons are:
- "Concept has endpoints but image does not" (1,299 occurrences across all not-classified preprocessing checks)
- "Reached maximum reduction iterations" (695 occurrences)

**[Inference]**: Class 8 images that are true closed curves (no endpoints, no corners) fail to match any concept that has endpoints. Since concept 8_1 has 13 nodes and complex topology, the "maximum reduction iterations" failure suggests graph reduction cannot align these images to 8_1 within the iteration budget.

---

## 5. Margin Analysis

Of 2,901 images that were classified (but incorrectly), the correct concept was also among the eligible candidates in many cases:

| Metric | Value |
|--------|-------|
| Near misses (correct concept available, lost by < 3%) | 1,286 (44.3%) |
| Wide misses (correct concept available, lost by ≥ 3%) | 258 (8.9%) |
| Correct concept not in eligible set | 1,357 (46.8%) |

**[Inference]**: 44.3% of classification errors are marginal — the correct concept passed preprocessing and scored within 3% of the winner but was not the top scorer. This suggests the feature/normalizer combination cannot create enough separation between concepts in ~45% of error cases.

### Winning Similarity Distribution (incorrect predictions)

| Percentile | Similarity |
|------------|-----------|
| p10 | 0.7723 |
| p25 | 0.7786 |
| p50 | 0.7862 |
| p75 | 0.7957 |
| p90 | 0.8053 |

The interquartile range is only **0.017** (1.7%) — winning similarities for incorrect predictions are extremely compressed. This means most errors occur in a narrow similarity band around 0.78–0.80, where the system has no discriminative power.

---

## 6. Concept-Level Error Contribution

### Concepts ranked by wrong wins

| Concept | Wrong Wins | Eligible in Errors | Hit Rate |
|---------|-----------|-------------------|----------|
| **7_1** | **690** | 2,025 | **34.1%** |
| 6_1 | 495 | 694 | 71.3% |
| 3_1 | 429 | 873 | 49.1% |
| 1_3 | 318 | 2,413 | 13.2% |
| 2_1 | 250 | 1,918 | 13.0% |
| 4_2 | 195 | 1,028 | 19.0% |
| 9_2 | 168 | 804 | 20.9% |
| 1_1 | 142 | 1,061 | 13.4% |
| 5_1 | 104 | 1,651 | 6.3% |
| 4_1 | 77 | 803 | 9.6% |
| 2_2 | 20 | 450 | 4.4% |
| 8_1 | 12 | 12 | 100.0% |
| 0_1 | 1 | 52 | 1.9% |

**Key observations:**
- **7_1** passes preprocessing in 2,025 error cases (most of any concept) AND has a 34.1% wrong-win rate. Its 5-node structure is too small to be selective.
- **6_1** has the highest hit rate among widely-eligible concepts (71.3%) — when it passes preprocessing, it usually wins. This drives the 8→6 confusion (239 images).
- **8_1** only passes preprocessing in 12 error cases total, and wins all 12. Its strict preprocessing (13 nodes, complex topology) almost never lets through non-8 images — but it also rejects 130 true class-8 images.
- **0_1** almost never wins incorrectly (1 wrong win out of 52 eligible) — high selectivity, but at the cost of recall (79.4%).

---

## 7. Preprocessing Filter Analysis

On incorrectly classified images, the average number of concepts passing preprocessing is **4.4** out of 13.

| Concepts Passing | Count | % of Errors |
|-----------------|-------|-------------|
| 0 (not classified) | 245 | 7.8% |
| 1 (forced choice) | 34 | 1.1% |
| 2+ | 2,867 | 91.1% |
| 5+ | 1,957 | 62.2% |

**[Inference]**: The preprocessing stage is not too aggressive overall — 91% of error images have 2+ concepts competing. The bottleneck is GED discrimination, not candidate filtering.

### Preprocessing Failure Reasons (across all not-classified images)

| Reason | Count |
|--------|-------|
| Concept has endpoints but image does not | 1,299 |
| Reached maximum reduction iterations | 695 |
| Concept has more corner points than image | 173 |
| Concept has intersection points but image does not | 160 |
| Concept has corner points but image does not | 122 |
| Concept has more endpoints than image | 22 |
| No path found for endpoint | 3 |

---

## 8. Artifacts

| File | Description |
|------|-------------|
| `findings.md` | This document |
| MLflow artifacts | `confusion_matrix.png`, `per_class_metrics.csv`, `metrics.csv`, `incorrect_results.csv`, `run_config.json`, `concept_graphs.json` |

**MLflow URL:** http://localhost:5050/#/experiments/4/runs/1c0b6867ba5a4beb971b78ca046f8148
