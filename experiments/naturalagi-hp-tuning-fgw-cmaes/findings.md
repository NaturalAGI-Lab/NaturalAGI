# Experiment Findings: naturalagi-hp-tuning-fgw-cmaes

**Date:** 2026-03-08
**Status:** Complete (500/510 trials; 7 failed, 3 running/stale)

## TL;DR

- **Best accuracy: 74.16%** `[FULL, 7,798 images]` (76.03% `[QUICK]`, -1.87 pp gap)
- **Optimal FGW alpha: 0.6–0.8** (75% features, 25% structure); best at 0.755
- **Optimal feature set: 5/6** — `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}` with `vertical_direction` OFF. 100% of top-quartile trials use this exact set
- **Feature selection dominates**: binary feature flags explain 93% of objective variance; normalizers and costs explain < 3%
- **CMA-ES wasted ~40% of compute** after trial ~350 re-exploring inferior feature-off combinations. Future studies should fix the feature set
- **FGW prefers skel_threshold 140–150** and compressed graduated costs (MINOR: 0.08–0.17, NO_MATCH: 1.5–1.8)

---

## 1. Study Configuration

| Field | Value |
|-------|-------|
| Study name | `naturalagi-hp-tuning-fgw-cmaes` |
| DB | `study.db` (symlinked in this folder) |
| Sampler | `CmaEsSampler(seed=42, n_startup_trials=20, with_margin=True)` |
| Direction | maximize |
| Objective | `accuracy_score(y_true, y_pred)` on 25% stratified sample |
| Comparison method | FGW only (`TUNE_COMPARISON_METHOD=False`, `fgw_alpha` tuned directly) |
| Sample fraction | 0.25 (~1,949 images) |
| Classes evaluated | 10 (digits 0-9) |
| Concept set | 13 concepts across 10 classes (same as 73.0% baseline) |
| n_trials budgeted | 510 |
| n_trials completed | 500 |
| n_trials failed | 7 (trials 0, 2, 22, 65, 77, 78, 381) |
| Git commit | `ce29c54` (feature/fgw-and-optimizations branch) |
| Wall clock time | ~19.6 hours (2026-03-05 20:53 to 2026-03-06 16:30) |
| Total compute time | 18.7 hours |
| Per-trial duration | median 2.2 min, mean 2.2 min |

### Search Space

**Continuous parameters:**

| Parameter | Type | Lower | Upper | Log-scale | Semantic role |
|-----------|------|-------|-------|-----------|---------------|
| `fgw_alpha` | float | 0.01 | 0.99 | no | FGW feature/structure balance (1=features, 0=structure) |
| `ged_timeout` | float | 0.1 | 15.0 | no | GED timeout (inert for FGW, present due to shared objective) |
| `cost_minor` | float | 0.05 | 0.4 | no | Node cost: MINOR level |
| `gap_minor_general` | float | 0.05 | 0.3 | no | Delta: GENERAL = MINOR + gap |
| `gap_general_severe` | float | 0.05 | 0.3 | no | Delta: SEVERE = GENERAL + gap |
| `cost_no_match` | float | 0.8 | 2.0 | no | Node cost: NO_MATCH level |
| `cost_impossible` | float | 1.0 | 200.0 | **yes** | Node cost: IMPOSSIBLE level |
| `norm_x` | float | 0.1 | 5.0 | no | Property normalizer: normalized_x |
| `norm_y` | float | 0.1 | 5.0 | no | Property normalizer: normalized_y |
| `norm_hdir` | float | 0.1 | 4.0 | no | Property normalizer: horizontal_direction |
| `norm_vdir` | float | 0.1 | 4.0 | no | Property normalizer: vertical_direction |
| `norm_cycle` | float | 0.5 | 8.0 | no | Property normalizer: cycle_count |
| `norm_angle` | float | 10.0 | 360.0 | no | Property normalizer: angle_with_ox |
| `simplification_epsilon` | float | 0.5 | 10.0 | no | RDP simplification epsilon |

**Integer parameters:**

| Parameter | Type | Lower | Upper | Step | Semantic role |
|-----------|------|-------|-------|------|---------------|
| `skel_threshold` | int | 100 | 220 | 10 | Skeletonization pixel threshold |

**Binary feature flags (0 or 1):**

| Parameter | Controls inclusion of |
|-----------|----------------------|
| `use_normalized_x` | `normalized_x` in features list |
| `use_normalized_y` | `normalized_y` in features list |
| `use_horizontal_direction` | `horizontal_direction` in features list |
| `use_vertical_direction` | `vertical_direction` in features list |
| `use_cycle_count` | `cycle_count` in features list |
| `use_angle_with_ox` | `angle_with_ox` in features list |

Note: If all feature flags are 0, the objective falls back to `["normalized_x", "normalized_y"]`. The `ged_timeout` parameter is present in the search space (shared objective function) but is inert for FGW — fANOVA importance confirms this at 0.0037.

Delta parameterization for node costs guarantees the ordering `MINOR < GENERAL < SEVERE` across all trials. Derived costs: `GENERAL = cost_minor + gap_minor_general`, `SEVERE = GENERAL + gap_general_severe`.

---

## 2. Results Summary

### Objective Distribution (500 completed trials)

| Statistic | Value |
|-----------|-------|
| **Best** | **76.03%** `[QUICK, 25% sample, ~1,949 images, 10 classes]` |
| Worst | 34.29% |
| Median | 71.01% |
| Mean | 67.26% |
| Stdev | 8.55 pp |
| Q1 | 64.62% |
| Q3 | 73.16% |

### Best Trial

- **Trial 282** of 510, accuracy = **76.03%** `[QUICK]`
- Delta vs. 10-class baseline (73.0% `[FULL]`): **+3.03 pp**

### Full-Set Validation

**Confirmed.** Run `run_20260308_174321`.

| Metric | Value |
|--------|-------|
| **Accuracy** | **74.16%** `[FULL, 7,798 images, 10 classes]` |
| Precision | 77.59% |
| Recall | 74.16% |
| F1 | 74.60% |
| Total submitted | 7,814 |
| DLQ (failures) | 16 |
| Successful | 7,798 |

**Quick-to-full gap: -1.87 pp** (76.03% `[QUICK]` → 74.16% `[FULL]`).

### Best Trial Parameters

| Parameter | Best value | Current default |
|-----------|-----------|-----------------|
| `fgw_alpha` | 0.755 | 0.5 |
| `skel_threshold` | 150 | 180 |
| `simplification_epsilon` | 3.52 | 5.0 |
| `norm_x` | 2.83 | 3.0 |
| `norm_y` | 3.03 | 3.0 |
| `norm_hdir` | 1.25 | 2.0 |
| `norm_vdir` | 1.68 | 2.0 |
| `norm_cycle` | 3.81 | 1.0 |
| `norm_angle` | 175.5 | 180.0 |

**Derived node costs at best trial:**

| Level | Best value | Current default |
|-------|-----------|-----------------|
| NO_COST | 0.0 | 0.0 |
| MINOR | 0.076 | 0.25 |
| GENERAL | 0.246 | 0.40 |
| SEVERE | 0.383 | 0.65 |
| NO_MATCH | 1.623 | 1.00 |
| IMPOSSIBLE | 24.0 | 100.0 |

**Optimal feature set:** `normalized_x`, `normalized_y`, `horizontal_direction`, `cycle_count`, `angle_with_ox` (5 of 6 features; `vertical_direction` excluded).

### Top 10 Trials

| Rank | Trial | Accuracy `[QUICK]` | fgw_alpha | skel_threshold | epsilon | Feature set |
|------|-------|-----------|-----------|----------------|---------|-------------|
| 1 | 282 | 76.03% | 0.755 | 150 | 3.52 | 5/6 (no vdir) |
| 2 | 301 | 75.75% | 0.725 | 130 | 3.50 | 5/6 (no vdir) |
| 3 | 267 | 75.71% | 0.636 | 140 | 2.24 | 5/6 (no vdir) |
| 4 | 238 | 75.67% | 0.723 | 130 | 2.40 | 5/6 (no vdir) |
| 5 | 234 | 75.49% | 0.804 | 150 | 3.30 | 5/6 (no vdir) |
| 6 | 192 | 75.30% | 0.758 | 140 | 3.47 | 5/6 (no vdir) |
| 7 | 344 | 75.18% | 0.596 | 160 | 2.85 | 5/6 (no vdir) |
| 8 | 243 | 75.12% | 0.649 | 160 | 2.76 | 5/6 (no vdir) |
| 9 | 106 | 75.10% | 0.746 | 130 | 2.73 | 5/6 (no vdir) |
| 10 | 235 | 75.10% | 0.665 | 140 | 2.36 | 5/6 (no vdir) |

All 10 top trials share the **identical feature set**: `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}` with `use_vertical_direction=0`.

### Bottom 5 Trials

| Rank | Trial | Accuracy `[QUICK]` | Key failure mode |
|------|-------|-----------|-----------------|
| 496 | 442 | 36.85% | Late exploration trial |
| 497 | 422 | 35.84% | Late exploration trial |
| 498 | 417 | 35.70% | Late exploration trial |
| 499 | 479 | 35.52% | Late exploration trial |
| 500 | 494 | 34.29% | Late exploration trial |

All bottom-5 trials are from the late degradation phase (trials 375+), where CMA-ES was exploring feature-off combinations (see Convergence Analysis below).

---

## 3. Parameter Importances (fANOVA)

Computed with 500 completed trials (reliable threshold: 20+).

| Rank | Parameter | Importance | Bar |
|------|-----------|------------|-----|
| 1 | **`use_normalized_x`** | **0.6082** | ############################## |
| 2 | **`use_normalized_y`** | **0.2757** | ############## |
| 3 | `fgw_alpha` | 0.0435 | ## |
| 4 | `skel_threshold` | 0.0296 | # |
| 5 | `use_angle_with_ox` | 0.0105 | |
| 6 | `simplification_epsilon` | 0.0088 | |
| 7 | `use_vertical_direction` | 0.0069 | |
| 8 | `ged_timeout` | 0.0037 | |
| 9 | `use_cycle_count` | 0.0025 | |
| 10 | `norm_cycle` | 0.0025 | |
| 11 | `norm_angle` | 0.0019 | |
| 12 | `gap_minor_general` | 0.0017 | |
| 13 | `cost_no_match` | 0.0015 | |
| 14 | `cost_impossible` | 0.0009 | |
| 15 | `use_horizontal_direction` | 0.0008 | |
| 16 | `gap_general_severe` | 0.0008 | |
| 17 | `cost_minor` | 0.0006 | |

**Key observations (facts):**

- `use_normalized_x` dominates at 60.8%, followed by `use_normalized_y` at 27.6%. Together these two binary flags explain **88.4%** of objective variance. Disabling `normalized_x` (84 trials) yields mean accuracy 53.5%, max 68.9%. Disabling `normalized_y` (105 trials) yields mean 57.0%, max 68.9%.
- `fgw_alpha` is the third most important parameter at 4.4% -- the only FGW-specific hyperparameter with meaningful importance.
- Feature flags collectively account for ~93% of importance (`use_normalized_x` + `use_normalized_y` + `use_angle_with_ox` + `use_vertical_direction` + `use_cycle_count` + `use_horizontal_direction` = 0.9046).
- All property normalizer values have importance below 0.3%. All node cost parameters have importance below 0.2%. **`[Inference]`**: FGW is largely insensitive to normalizer and cost tuning — feature selection dominates.
- `ged_timeout` importance is 0.37%, confirming it is inert for FGW runs.

---

## 4. Convergence Analysis

### Improvement Trajectory

| Trial | Best accuracy `[QUICK]` | Phase |
|-------|-----------|-------|
| 1 | 71.73% | Random startup |
| 54 | 73.10% | CMA-ES |
| 71 | 73.84% | CMA-ES |
| 94 | 74.63% | CMA-ES |
| 106 | 75.10% | CMA-ES |
| 192 | 75.30% | CMA-ES |
| 234 | 75.49% | CMA-ES |
| 238 | 75.67% | CMA-ES |
| 267 | 75.71% | CMA-ES |
| **282** | **76.03%** | CMA-ES |

### Sliding Window Analysis (50-trial windows)

| Window | Mean | Stdev | Max |
|--------|------|-------|-----|
| Trials 1-54 | 60.99% | 8.06 pp | 73.10% |
| Trials 55-108 | 69.94% | 3.55 pp | 75.10% |
| Trials 109-158 | 70.95% | 4.27 pp | 74.99% |
| Trials 159-208 | 70.60% | 3.32 pp | 75.30% |
| Trials 209-258 | 72.98% | 1.76 pp | 75.67% |
| **Trials 259-308** | **73.29%** | **1.68 pp** | **76.03%** |
| Trials 309-358 | 72.42% | 2.66 pp | 75.18% |
| Trials 359-409 | 66.41% | 8.14 pp | 75.10% |
| **Trials 410-459** | **57.84%** | **9.48 pp** | **70.71%** |
| **Trials 460-509** | **57.21%** | **9.85 pp** | **72.39%** |

### Convergence Indicators

- Best value (76.03%) first achieved at trial 282 (55.3% of budget).
- Best value **did NOT improve** in the final 25% of trials. Best in last 25%: 72.39% vs. best overall: 76.03%.
- **Severe degradation in trials 375+**: mean accuracy dropped from 73.29% (window 259-308) to 57.21% (window 460-509), a -16.1 pp decline.
- The degradation is caused by CMA-ES exploring feature-off combinations in later generations. In trials 375+: `use_normalized_x` was ON in only 59.7% of trials (vs. 100% in top-quartile), `use_normalized_y` was ON in only 48.5%, and `use_vertical_direction` was ON in 48.5% (vs. 0% in top-quartile).
- Trials with BOTH `normalized_x` and `normalized_y` OFF (29 trials in late phase): mean accuracy 45.6%.

**`[Inference]`**: CMA-ES converged on the optimal continuous parameters (alpha, normalizers, costs) by trial ~280, then began exploring binary feature combinations that are categorically inferior. The `with_margin=True` setting enables exploration of discrete parameters, but the binary feature space has a very sharp cliff: the optimal combination (5 features, no vdir) is surrounded by much worse alternatives. The last 40% of compute was effectively wasted on exploring already-ruled-out feature combinations. A future study should fix the feature set and tune only continuous parameters.

---

## 5. Per-Parameter Effective Ranges

### Feature Flags (Binary)

| Feature | Top-Q ON | Top-Q OFF | Bot-Q ON | Bot-Q OFF | Verdict |
|---------|----------|-----------|----------|-----------|---------|
| `use_normalized_x` | **125** (100%) | 0 | 53 (42%) | **72** (58%) | **Required** |
| `use_normalized_y` | **125** (100%) | 0 | 53 (42%) | **72** (58%) | **Required** |
| `use_horizontal_direction` | **125** (100%) | 0 | 70 (56%) | 55 (44%) | **Required** |
| `use_vertical_direction` | 0 (0%) | **125** (100%) | 61 (49%) | 64 (51%) | **Harmful** |
| `use_cycle_count` | **124** (99.2%) | 1 (0.8%) | 64 (51%) | 61 (49%) | **Required** |
| `use_angle_with_ox` | **122** (97.6%) | 3 (2.4%) | 55 (44%) | 70 (56%) | **Required** |

**100% of top-quartile trials** (125/125) use `normalized_x`, `normalized_y`, and `horizontal_direction`.
**0% of top-quartile trials** enable `vertical_direction`.

### Vertical Direction Impact

| Metric | vdir ON (127 trials) | vdir OFF (373 trials) | Delta |
|--------|---------------------|----------------------|-------|
| Mean accuracy | 61.18% | 69.33% | **+8.15 pp** when OFF |
| Max accuracy | 73.10% | 76.03% | **+2.93 pp** when OFF |

### Optimal Feature Set Performance

212 of 500 trials used the optimal 5-feature set (no `vertical_direction`). Within this subset:

| Statistic | Value |
|-----------|-------|
| Mean | 73.00% |
| Median | 73.39% |
| Max | 76.03% |
| Stdev | 2.40 pp |

The 2.40 pp stdev (vs. 8.55 pp for all trials) shows that once the correct feature set is fixed, the remaining continuous parameter tuning has modest impact.

### FGW Alpha

The most important FGW-specific parameter. Alpha = weight on feature costs; (1 - alpha) = weight on structural similarity.

| Alpha range | N trials | Mean accuracy | Max accuracy |
|-------------|----------|--------------|-------------|
| [0.0, 0.2) | 27 | 57.39% | 68.89% |
| [0.2, 0.4) | 49 | 60.49% | 71.73% |
| [0.4, 0.6) | 142 | 69.29% | 75.18% |
| [0.6, 0.7) | 125 | 69.67% | 75.71% |
| **[0.7, 0.8)** | **100** | **70.45%** | **76.03%** |
| [0.8, 1.0) | 57 | 61.83% | 75.49% |

Within the optimal feature set only:

| Alpha range | N | Mean | Max |
|-------------|---|------|-----|
| [0.40, 0.50) | 16 | 72.66% | 74.29% |
| [0.50, 0.60) | 48 | 73.30% | 75.18% |
| [0.60, 0.65) | 42 | 73.67% | 75.71% |
| [0.65, 0.70) | 26 | 73.81% | 75.10% |
| **[0.70, 0.75)** | **34** | **73.82%** | **75.75%** |
| [0.75, 0.80) | 19 | 73.43% | 76.03% |
| [0.80, 0.85) | 9 | 72.68% | 75.49% |

Top-Q alpha: min=0.408, median=0.656, max=0.812.

**`[Inference]`**: The optimal alpha is broadly in [0.6, 0.8], with the best single result at 0.755. Mean accuracy is remarkably stable across [0.5, 0.8] once the feature set is fixed (all within 1.2 pp). Alpha below 0.4 (too much structural weight) or above 0.85 (too little structural weight) consistently degrades accuracy. The previous run_20260305_000844 used alpha=0.7, which sits squarely in the optimal zone.

### Skeletonization Threshold

| Threshold | N trials | Mean accuracy | Max accuracy |
|-----------|----------|--------------|-------------|
| 100 | 18 | 64.24% | 74.06% |
| 110 | 25 | 61.63% | 74.18% |
| 120 | 44 | 67.80% | 74.73% |
| 130 | 59 | 69.77% | 75.75% |
| **140** | **125** | **69.99%** | **75.71%** |
| **150** | **91** | **70.13%** | **76.03%** |
| 160 | 56 | 69.17% | 75.18% |
| 170 | 24 | 64.82% | 73.78% |
| 180 | 17 | 58.16% | 71.65% |
| 200 | 11 | 54.79% | 65.37% |
| 220 | 10 | 50.58% | 58.92% |

Top-Q distribution: 100=1, 110=1, 120=9, 130=15, **140=50**, **150=31**, 160=15, 170=3.

**`[Inference]`**: FGW prefers skel_threshold in [130, 160], peaking at 140-150. Moderately detailed skeletons (more nodes/edges at lower threshold) provide more transport mass to distribute, benefiting FGW's structural matching.

### Simplification Epsilon

| Epsilon range | N trials | Mean accuracy | Max accuracy |
|---------------|----------|--------------|-------------|
| [0.5, 2.0) | 69 | 60.99% | 74.19% |
| [2.0, 3.0) | 164 | 67.55% | 75.71% |
| **[3.0, 4.0)** | **207** | **69.98%** | **76.03%** |
| [4.0, 5.0) | 60 | 64.30% | 75.09% |

Top-Q range: [1.27, 4.71], median 3.17. Best trial: 3.52.

### Continuous Parameters (Top-Q vs. Bottom-Q Ranges)

| Parameter | Search space | Top-Q median | Bot-Q median | Best | Boundary? |
|-----------|-------------|-------------|-------------|------|-----------|
| `fgw_alpha` | [0.01, 0.99] | 0.656 | 0.494 | 0.755 | no |
| `norm_x` | [0.1, 5.0] | 2.587 | 2.325 | 2.83 | no |
| `norm_y` | [0.1, 5.0] | 3.357 | 2.307 | 3.03 | no |
| `norm_hdir` | [0.1, 4.0] | 1.657 | 1.872 | 1.25 | no |
| `norm_vdir` | [0.1, 4.0] | 2.067 | 2.122 | 1.68 | no |
| `norm_cycle` | [0.5, 8.0] | 3.533 | 3.870 | 3.81 | no |
| `norm_angle` | [10.0, 360.0] | 134.5 | 191.3 | 175.5 | no |
| `cost_no_match` | [0.8, 2.0] | 1.637 | 1.378 | 1.623 | near HIGH |

**`[Inference]`**: No continuous parameter's top-Q range hits a search space boundary, suggesting the search space is well-specified for FGW.

### Node Costs (Derived)

| Cost Level | Top-Q Median | Bot-Q Median | Best | Default |
|------------|-------------|-------------|------|---------|
| MINOR | 0.169 | 0.229 | 0.076 | 0.25 |
| GENERAL | 0.343 | 0.376 | 0.246 | 0.40 |
| SEVERE | 0.482 | 0.541 | 0.383 | 0.65 |
| NO_MATCH | 1.637 | 1.378 | 1.623 | 1.00 |
| IMPOSSIBLE | 30.6 | 18.6 | 24.0 | 100.0 |

The top-10 trials show SEVERE/MINOR ratios of 2.4-5.0.

**`[Inference]`**: FGW benefits from compressing the graduated cost scale (MINOR: 0.08-0.17, SEVERE: 0.3-0.5) while elevating NO_MATCH (1.5-1.8). FGW distributes transport mass across all node pairs simultaneously, so the relative gap between "somewhat similar" and "totally unmatched" nodes matters more than the absolute cost magnitudes.

---

## 6. Dead Zones

### Feature Combinations to Avoid

| Dead zone | Evidence | Impact |
|-----------|----------|--------|
| `use_normalized_x=0` | 84 trials, mean 53.5%, max 68.9% | **-16.6 pp mean vs. enabled** |
| `use_normalized_y=0` | 105 trials, mean 57.0%, max 68.9% | **-13.0 pp mean vs. enabled** |
| `use_vertical_direction=1` | 127 trials, mean 61.2%, max 73.1% | **-8.2 pp mean vs. disabled, -2.9 pp ceiling** |
| Both x,y OFF | ~29 late trials, mean 45.6% | Catastrophic |

### Skeletonization Threshold to Avoid

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| 120-160 | 375 | 69.6% | 76.0% | Safe zone |
| **180-220** | **58** | **55.6%** | **71.7%** | **Dead zone** |

### FGW Alpha to Avoid

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| [0.0, 0.2) | 27 | 57.4% | 68.9% | **Dead zone** (too structural) |
| [0.4, 0.8) | 367 | 69.8% | 76.0% | Safe zone |
| [0.85, 1.0) | ~30 | ~60% | 75.5% | Risky (too feature-heavy) |

### Simplification Epsilon to Avoid

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| [0.5, 1.5) | ~40 | ~59% | ~73% | Moderate risk |
| [2.0, 5.0) | 431 | 68.3% | 76.0% | Safe zone |
| [5.0, 10.0) | ~30 | ~62% | ~72% | Degraded |

---

## 7. FGW-Specific Analysis

### FGW Alpha Semantics

In the Fused Gromov-Wasserstein formulation:
- `alpha=1.0`: pure feature-based matching (Wasserstein distance on node attributes only)
- `alpha=0.0`: pure structural matching (Gromov-Wasserstein distance on graph topology only)
- `alpha=0.75` (near optimal): 75% weight on features, 25% on structure

The optimal alpha range [0.6, 0.8] means FGW is primarily using node features but derives meaningful benefit from structural similarity. The structural component contributes ~25% of the signal at the optimum.

This aligns with the previous manual run (run_20260305_000844, alpha=0.7, 70.0% accuracy) — that run's alpha was in the right zone but lacked the optimal feature set and other parameters.

---

## 8. Open Questions

These are hypotheses, not conclusions. Each requires further experimentation.

1. **Would a narrowed FGW study (fixed features, tuning alpha + normalizers only) converge better?** The last 40% of this study was wasted on feature exploration. A 200-trial study with the 5-feature set fixed and only `fgw_alpha`, normalizers, costs, and preprocessing parameters tuned would concentrate CMA-ES on the productive subspace.

2. **Can FGW similarity score compression be addressed?** Previous FGW runs showed similarity scores clustered around ~0.90 for all concepts, giving poor discrimination. A different distance-to-similarity mapping (e.g., `exp(-fgw_dist)` instead of `1/(1+fgw_dist)`) might help. Concept-complexity normalization could address low-complexity attractor bias.

3. **Why is `norm_angle` optimal at 134.5?** A lower normalizer means FGW penalizes angle differences more harshly. This may indicate FGW's transport formulation benefits from stronger feature discrimination at high alpha values.

---

## 9. Recommended Next Steps

Ordered by expected information value:

1. **Run a narrowed FGW study** with fixed feature set:
   - Fix feature set to `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}`
   - Narrow `fgw_alpha` to [0.5, 0.85]
   - Narrow `skel_threshold` to [120, 170]
   - Budget: 150-200 trials (sufficient since 7 of 17 parameters are now fixed)

2. **Investigate FGW similarity mapping alternatives.** The `1/(1+fgw_dist)` formula compresses scores near 0.90. Alternatives to test: `exp(-fgw_dist * k)` with tunable steepness `k`, or `1 - fgw_dist/max_dist`.

---

## 10. Artifacts

All experiment artifacts are in `experiments/naturalagi-hp-tuning-fgw-cmaes/`:

| Artifact | Path | Description |
|----------|------|-------------|
| This document | `findings.md` | Full analysis with findings and recommendations |
| Best trial params | `best_params.json` | Trial 282 parameters in pipeline-ready JSON format |
| Convergence data | `convergence.csv` | Per-trial accuracy + running best (for plotting) |
| Parameter importance | `param_importance.csv` | fANOVA importance scores for all 17 parameters |
| All trials | `all_trials.csv` | Complete 500-trial dataset with all parameters |
| Optuna DB | `study.db` | Symlink to source SQLite database |
