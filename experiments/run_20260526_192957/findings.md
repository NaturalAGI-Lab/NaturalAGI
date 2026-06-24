# Run analysis: `run_20260526_192957`

**Date:** 2026-05-26
**Branch:** `docs/ieee-khpi-week-2026-abstract`
**Compared to:** `run_20260427_144233` (85.80% baseline)

## TL;DR

- **Accuracy: 85.68%** on 8,685 successfully classified / 8,707 submitted complete-only MNIST images — **Δ -0.13pp vs the 2026-04-27 baseline** (within DLQ noise).
- 13 concepts retrained from `datasets/mnist_all/` (training samples per concept; `tests/prepared_samples/` data staging deprecated — use `datasets/` directly) with the same exp_059 H1 config (`MINOR=0.65`, Family E cost-cap removal, log-complexity prior, 14 features, `diagnostic_weight_epsilon=1.0`). Concept set unchanged: 0_1, 1_1, 1_3, 2_1, 2_2, 3_1, 4_1, 4_2, 5_1, 6_1, 7_1, 8_1, 9_2.
- **Three concepts came back smaller than the baseline**: 0_1 (12→10 nodes), 4_2 (9→7), 5_1 (9→7). Likely due to a subtle change in the reduction/start-point selection pipeline since the 2026-04-27 commit (`feat/graph-features-and-cleanup` was merged 2026-05-06).
- **The error budget is unchanged in shape**: same three dominant failure modes (7_1 over-fire, class-8 DLQ, class-0 DLQ).

## 1. Headline metrics

| Metric | New | Baseline | Δ |
|---|---:|---:|---:|
| Total submitted | 8,707 | 8,707 | 0 |
| DLQ | 22 | 22 | 0 |
| Successfully classified | 8,685 | 8,685 | 0 |
| **Accuracy** | **85.68%** | **85.80%** | **-0.13pp** |
| Precision | 89.40% | 89.31% | +0.08pp |
| Recall | 85.68% | 85.80% | -0.13pp |
| F1 | 86.63% | 86.66% | -0.02pp |
| Total wrong rows | 1,244 | 1,233 | +11 |

## 2. Per-class deltas (sorted by absolute F1 change)

| Class | New F1 | Base F1 | ΔF1 | New P | ΔP | New R | ΔR | Mode |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2 | 72.19 | 71.09 | **+1.10** | 88.08 | +0.87 | 61.15 | +1.15 | minor recovery |
| 0 | 93.04 | 94.00 | **-0.96** | 100.00 | 0 | 86.99 | -1.69 | DLQ jumped 22→35 |
| 7 | 77.97 | 78.78 | -0.82 | 65.12 | -1.05 | 97.13 | -0.20 | over-fire unchanged |
| 6 | 88.60 | 87.83 | +0.78 | 84.73 | +1.52 | 92.85 | -0.13 | precision up |
| 3 | 87.83 | 88.50 | -0.67 | 92.17 | +0.38 | 83.88 | -1.55 | more goes to 7 |
| 8 | 86.08 | 85.40 | +0.67 | 99.77 | 0 | 75.69 | +1.03 | minor recovery |
| 5 | 88.73 | 88.39 | +0.34 | 93.96 | +0.29 | 84.05 | +0.38 | tiny improvement |
| 1 | 92.11 | 92.38 | -0.27 | 89.77 | -0.45 | 94.57 | -0.08 | flat |
| 9 | 93.59 | 93.43 | +0.15 | 92.40 | +0.69 | 94.80 | -0.42 | flat |
| 4 | 88.76 | 88.81 | -0.05 | 95.18 | -0.79 | 83.16 | +0.51 | flat |

All within ±2pp — the reproduction is tight.

## 3. Failure mode comparison

| Mode | New | Baseline | Δ |
|---|---:|---:|---:|
| 7_1 over-fire (false 7s) | **526** | 503 | +23 |
| Class-8 DLQ ("not classified") | **120** | 127 | -7 |
| Class-0 DLQ | 35 | 22 | +13 |
| Class-6 DLQ | 16 | 17 | -1 |
| 4 → 1 confusion | 77 | 76 | +1 |
| 2 → 6 confusion | 55 | 71 | -16 |
| 5 → 3 confusion | 44 | 44 | 0 |

Same three top modes. Class-0 DLQ regressed (likely 0_1 size drop 12→10).

## 4. Concept-graph diffs (new vs baseline)

| Concept | New nodes/edges | Base nodes/edges | Δnodes |
|---|---|---|---:|
| **0_1** | 10 / 10 | **12 / 12** | **-2** |
| 1_1 | 7 / 6 | 7 / 6 | 0 |
| 1_3 | 3 / 2 | 3 / 2 | 0 |
| 2_1 | 7 / 6 | 7 / 6 | 0 |
| 2_2 | 10 / 10 | 10 / 10 | 0 |
| 3_1 | 11 / 10 | 11 / 10 | 0 |
| 4_1 | 8 / 8 | 8 / 8 | 0 |
| **4_2** | 7 / 6 | **9 / 8** | **-2** |
| **5_1** | 7 / 6 | **9 / 8** | **-2** |
| 6_1 | 10 / 10 | 10 / 10 | 0 |
| 7_1 | 5 / 4 | 5 / 4 | 0 |
| 8_1 | 15 / 16 | 15 / 16 | 0 |
| 9_2 | 8 / 8 | 8 / 8 | 0 |

Three concepts each lost two nodes — likely the same two-node motif (e.g., an
end-of-stroke endpoint + adjoining vector) was dropped by a slightly different
reduction path in current contour-analysis vs the 2026-04-27 build. Worth
diff-ing `contour-analysis/services/graph_analyzer.py` against the
`9060d87` commit if a true byte-for-byte reproduction is needed.

## 5. Issues in the trained graphs

1. **Wide-range catch-all in 7_1.** From `concept_graphs.json` in this run,
   7_1's StartPoint has `normalized_x ∈ [-0.7, 0.1]` (width 0.8) and
   `normalized_y ∈ [-0.9, 0.2]` (width 1.1). The EndPoint's
   `normalized_x ∈ [-0.7, 0.7]` (width 1.4 — i.e. anywhere on the canvas).
   Combined with `_calculate_range_similarity_cost` giving 0 cost at range
   centre regardless of range width, this concept matches virtually any
   top→bottom stroke configuration.

2. **0_1 lost 2 nodes** vs baseline. The smaller version is presumably losing
   structural anchors that were excluding non-0 images. Result: class-0 recall
   86.99% vs 88.67% baseline.

3. **8_1 too complex (15 nodes / 16 edges, complexity 31) for typical class-8
   image**. Median class-8 image after skeletonisation+contour analysis is
   ~22 complexity. So 8_1 is filtered out by the `concept_complexity ≤
   image_complexity` pre-filter in the orchestrator. Class-8 then has only
   smaller concepts to fall back on, none of which describe two-loop digits →
   DLQ.

4. **Single-concept classes (3, 5, 6, 7, 8, 9)** with no second variant covering
   stylistic outliers. Inactive subclasses on disk (`datasets/inactive/`):
   1_2 (44 samples), 7_2 (110), 8_2 (55), 9_1 (77). 7_2 and 8_2 are the most
   promising re-activations given the current failure modes.

## 6. Issues in the classification path

1. **Boria normaliser favours small concepts.**
   `sim = 1 − cost / (cost + max(n1, n2))` where `max(n1, n2)` is dominated by
   the *image* graph for any small concept. For 7_1 (post-preprocessing
   complexity ≈ 9) matched against an image (complexity ≈ 22), a cost of 3
   gives `sim = 1 − 3/25 = 0.88`. The same cost against 8_1 (complexity 31)
   gives `sim = 1 − 3/34 = 0.91` — but 8_1 is filtered out, so it never gets
   to compete.

2. **Bayesian log-complexity prior λ = 0.02 is too weak.** Gap between 7_1 (c=9)
   and 3_1 (c=21) is `0.02 · (log₂(21) − log₂(9)) = 0.024`. That's below the
   typical Boria similarity noise floor for marginally-different graphs.

3. **Complexity prefilter is hard.** When *no* concept has
   `complexity ≤ image_complexity`, classification returns no result → DLQ.
   This is the proximate cause of class-8 DLQs. A soft fallback ("pick the
   closest in complexity, lower its score") would convert DLQs into
   misclassifications, which at least have a chance of being correct.

4. **Range-cost is zero at centre, regardless of range width.**
   `cost_functions.py:259` — `graduated = max_cost * (abs(v - centre) / (width/2.0))`.
   At v = centre, cost = 0. Wide ranges get the same zero floor as tight
   ranges, even though wide-range matches carry far less discriminative
   information.

5. **`CriticalPointPreprocessor` raises after 5 iterations** on graphs whose
   critical-point structure can't be made isomorphic to the concept's. This
   path is hit hardest by cycle-heavy digits (8, 0, 6, 9), explaining the DLQ
   distribution.

## 7. Path to >90%

Detailed proposal in `researches/run_2026-05-26_session/path_to_90_percent.md`.
The summary ladder (additive, ordered by expected gain × low effort):

| # | Lever | Expected gain | Risk |
|---|---|---:|---|
| 1 | Range-width cost floor (RANGE_PENALTY_FACTOR ≈ 0.5) | +2.0 to +3.5pp | low |
| 2 | Bump COMPLEXITY_PRIOR_LAMBDA 0.02 → 0.06 | +0.5 to +1.0pp | low |
| 3 | Cycle-aware soft preprocessor + max_iter 5→10 | +1.0 to +1.5pp | medium |
| 4 | Reactivate 8_2 subclass + retrain | +0.5 to +1.0pp | medium |
| 5 | Asymmetric MINOR per concept (penalise 7_1 deletions) | +0.3 to +0.8pp | medium |
| 6 | Soft complexity prefilter fallback | +0.2 to +0.5pp | low |

Worst-case sum of #1 + #2 alone = +2.5pp → 88.2%. Best-case = +4.5pp → 90.2%.
Layering #3 + #4 covers the remainder comfortably.

## 8. Artifacts

- `findings.md` — this file
- `metrics.csv`, `per_class_metrics.csv`, `confusion_matrix.png`
- `incorrect_results.csv` (1,244 wrong rows)
- `run_config.json`
- `concept_graphs.json` — current 13 trained concepts (deviations from baseline noted above)
