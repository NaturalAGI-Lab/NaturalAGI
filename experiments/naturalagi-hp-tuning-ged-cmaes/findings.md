# Experiment Findings: naturalagi-hp-tuning-ged-cmaes

**Date:** 2026-03-08
**Status:** Complete (500/500 trials)

---

## 1. Study Configuration

| Field | Value |
|-------|-------|
| Study name | `naturalagi-hp-tuning-ged-cmaes` |
| DB | `study.db` (symlinked in this folder) |
| Sampler | `CmaEsSampler(seed=42, n_startup_trials=20, with_margin=True)` |
| Direction | maximize |
| Objective | `accuracy_score(y_true, y_pred)` on 25% stratified sample |
| Comparison method | GED only (`TUNE_COMPARISON_METHOD=False`) |
| Sample fraction | 0.25 (~1,949 images) |
| Classes evaluated | 10 (digits 0-9) |
| Concept set | 13 concepts across 10 classes (same as 73.0% baseline) |
| n_trials budgeted | 500 |
| n_trials completed | 500 |
| n_trials stuck (RUNNING) | 1 (trial 14, stale heartbeat from 2026-03-06 18:12) |
| CMA-ES generations | 40 (across 480 guided trials; 20 random startup trials) |
| Git commit | `ce29c54` (feature/fgw-and-optimizations branch) |
| Wall clock time | 45.6 hours (2026-03-06 16:33 to 2026-03-08 14:08) |
| Total compute time | 43.3 hours |
| Per-trial duration | median 3.2 min, mean 5.2 min, range [1.2 min, 67.8 min] |

### Search Space

**Continuous parameters:**

| Parameter | Type | Lower | Upper | Log-scale | Semantic role |
|-----------|------|-------|-------|-----------|---------------|
| `ged_timeout` | float | 0.1 | 15.0 | no | GED optimization deadline (seconds) |
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

Note: If all feature flags are 0, the objective falls back to `["normalized_x", "normalized_y"]`.

Delta parameterization for node costs guarantees the ordering `MINOR < GENERAL < SEVERE` across all trials. Derived costs: `GENERAL = cost_minor + gap_minor_general`, `SEVERE = GENERAL + gap_general_severe`.

---

## 2. Results Summary

### Objective Distribution (500 completed trials)

| Statistic | Value |
|-----------|-------|
| **Best** | **77.56%** `[QUICK, 25% sample, ~1,949 images, 10 classes]` |
| Worst | 26.75% |
| Median | 72.03% |
| Mean | 69.78% |
| Stdev | 7.72 pp |

### Best Trial

- **Trial 442** of 500, accuracy = **77.56%** `[QUICK]`
- Delta vs. 10-class baseline: **+4.56 pp** (baseline: 73.0% `[FULL]`)
- Delta vs. 7-class baseline: comparison not valid (different class set)

### Full-Set Validation (run_20260308_170858)

Trial 442 parameters validated on **100% of test set** (7,814 images, 23 DLQ, 7,791 classified).

| Metric | Value `[FULL]` | Quick proxy `[QUICK]` |
|--------|---------------|-----------------------|
| **Accuracy** | **75.96%** | 77.56% |
| Precision | 78.04% | — |
| Recall | 75.96% | — |
| F1 | 76.40% | — |

- **Quick-to-full gap: -1.60 pp** (77.56% → 75.96%), within expected 1-2 pp variance noted in §7.1

**Per-class metrics:**

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| 0 | 97.4% | 80.0% | 87.9% | 1,000 |
| 1 | 80.7% | 92.4% | 86.2% | 994 |
| 2 | 74.1% | 63.2% | 68.2% | 946 |
| 3 | 73.4% | 66.0% | 69.5% | 981 |
| 4 | 49.8% | 58.3% | 53.7% | 496 |
| 5 | 66.2% | 64.6% | 65.4% | 477 |
| 6 | 76.5% | 84.7% | 80.4% | 753 |
| 7 | 71.3% | 91.0% | 79.9% | 989 |
| 8 | 96.7% | 71.5% | 82.2% | 372 |
| 9 | 86.7% | 70.8% | 77.9% | 783 |

**Full best-trial parameters:**

| Parameter | Best value | Current default |
|-----------|-----------|-----------------|
| `ged_timeout` | 6.25 | 5.0 |
| `skel_threshold` | 110 | 180 |
| `simplification_epsilon` | 4.62 | 5.0 |
| `norm_x` | 3.38 | 3.0 |
| `norm_y` | 2.26 | 3.0 |
| `norm_hdir` | 2.70 | 2.0 |
| `norm_vdir` | 3.06 | 2.0 |
| `norm_cycle` | 2.66 | 1.0 |
| `norm_angle` | 252.33 | 180.0 |

**Derived node costs at best trial:**

| Level | Best value | Current default |
|-------|-----------|-----------------|
| NO_COST | 0.0 | 0.0 |
| MINOR | 0.230 | 0.25 |
| GENERAL | 0.468 | 0.40 |
| SEVERE | 0.754 | 0.65 |
| NO_MATCH | 1.181 | 1.00 |
| IMPOSSIBLE | 7.38 | 100.0 |

**Optimal feature set:** `normalized_x`, `normalized_y`, `horizontal_direction`, `cycle_count`, `angle_with_ox` (5 of 6 features; `vertical_direction` excluded).

### Top 10 Trials

| Rank | Trial | Accuracy `[QUICK]` | skel_threshold | epsilon | Notable |
|------|-------|-----------|----------------|---------|---------|
| 1 | 442 | 77.56% | 110 | 4.62 | Best overall |
| 2 | 423 | 77.26% | 130 | 4.25 | |
| 3 | 435 | 77.09% | 110 | 4.25 | |
| 4 | 485 | 77.02% | 110 | 4.27 | |
| 5 | 374 | 76.94% | 110 | 4.60 | |
| 6 | 275 | 76.92% | 100 | 4.67 | |
| 7 | 426 | 76.81% | 120 | 4.56 | |
| 8 | 413 | 76.60% | 130 | 4.92 | |
| 9 | 425 | 76.53% | 100 | 5.56 | |
| 10 | 364 | 76.49% | 110 | 4.39 | |

All top 15 trials share the **identical feature set**: `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}` with `use_vertical_direction=0`.

### Bottom 5 Trials

| Rank | Trial | Accuracy `[QUICK]` | Key failure mode |
|------|-------|-----------|-----------------|
| 496 | 20 | 26.75% | skel_threshold=220, only 1 feature (normalized_y) |
| 497 | 5 | 28.58% | skel_threshold=220, only 1 feature, ged_timeout=0.57 |
| 498 | 29 | 29.95% | skel_threshold=200, 2 features (hdir, normalized_x=0) |
| 499 | 23 | 30.15% | skel_threshold=160, 3 features (missing normalized_x/y) |
| 500 | 71 | 34.46% | Missing normalized_x/y, only 3 features |

---

## 3. Parameter Importances (fANOVA)

Computed with 500 completed trials (reliable threshold: 20+).

| Rank | Parameter | Importance | Bar |
|------|-----------|------------|-----|
| 1 | **`use_normalized_x`** | **0.5889** | ############################# |
| 2 | `use_cycle_count` | 0.0913 | #### |
| 3 | `gap_minor_general` | 0.0523 | ## |
| 4 | `skel_threshold` | 0.0518 | ## |
| 5 | `use_angle_with_ox` | 0.0437 | ## |
| 6 | `ged_timeout` | 0.0266 | # |
| 7 | `use_normalized_y` | 0.0229 | # |
| 8 | `cost_no_match` | 0.0213 | # |
| 9 | `cost_minor` | 0.0166 | |
| 10 | `norm_cycle` | 0.0130 | |
| 11 | `use_horizontal_direction` | 0.0121 | |
| 12 | `norm_angle` | 0.0103 | |
| 13 | `norm_x` | 0.0080 | |
| 14 | `gap_general_severe` | 0.0076 | |
| 15 | `norm_hdir` | 0.0072 | |
| 16 | `use_vertical_direction` | 0.0062 | |
| 17 | `simplification_epsilon` | 0.0056 | |
| 18 | `cost_impossible` | 0.0050 | |
| 19 | `norm_vdir` | 0.0049 | |
| 20 | `norm_y` | 0.0046 | |

**Key observations (facts):**
- `use_normalized_x` dominates at 58.9% -- more than all other parameters combined. Disabling it (42 trials) yields mean accuracy 51.2%, max 68.4%. Enabling it (458 trials) yields mean 71.7%, max 77.6%.
- Feature flags collectively account for ~77% of importance (`use_normalized_x` + `use_cycle_count` + `use_angle_with_ox` + `use_normalized_y` + `use_horizontal_direction` + `use_vertical_direction` = 0.765).
- Property normalizer values have low individual importance (all below 1.3%). **`[Inference]`**: Within reasonable ranges, the exact normalizer value matters far less than whether the feature is included at all.
- `cost_impossible` has the lowest importance among cost parameters (0.5%), despite a wide log-scale search range [1, 200]. **`[Inference]`**: As long as IMPOSSIBLE is sufficiently high to act as a penalty, its exact magnitude does not matter.

---

## 4. Convergence Analysis

### Improvement Trajectory

| Trial | Best accuracy `[QUICK]` | Phase |
|-------|-----------|-------|
| 0 | 60.26% | Random startup |
| 4 | 67.39% | Random startup |
| 7 | 72.07% | Random startup |
| 51 | 72.70% | CMA-ES |
| 70 | 73.05% | CMA-ES |
| 101 | 74.10% | CMA-ES |
| 183 | 74.58% | CMA-ES |
| 187 | 75.24% | CMA-ES |
| 225 | 75.51% | CMA-ES |
| 253 | 76.10% | CMA-ES |
| 275 | 76.92% | CMA-ES |
| 374 | 76.94% | CMA-ES |
| 423 | 77.26% | CMA-ES |
| **442** | **77.56%** | CMA-ES |

### Per-Quartile Statistics

| Quartile | Trials | Mean | Best | Stdev |
|----------|--------|------|------|-------|
| Q1 (0-125) | 126 | 62.21% | 74.10% | 10.78 pp |
| Q2 (126-250) | 125 | 70.05% | 75.51% | 4.49 pp |
| Q3 (251-375) | 125 | 72.86% | 76.94% | 3.33 pp |
| Q4 (376-500) | 125 | 73.98% | 77.56% | 2.69 pp |

### Convergence Indicators

- Best value (77.56%) first achieved at trial 442 (88.4% of budget).
- Best value **did improve** in the final 25% of trials (best in Q4: 77.56%, previous best entering Q4: 76.94%).
- Objective stdev decreased monotonically across quartiles: 10.78 -> 4.49 -> 3.33 -> 2.69 pp.
- Last 10 trials: mean 74.71%, stdev 1.45 pp. Range: [70.93%, 76.30%].
- 14 improvement milestones across 500 trials; 4 in the final 25%.

**`[Inference]`**: The study shows convergence behavior -- variance is decreasing and the landscape is being narrowed. However, the best value was achieved at trial 442 with continued improvement through the final quartile, suggesting additional trials beyond 500 could yield marginal gains. The diminishing-returns pattern (Q3->Q4 improvement: +1.12 pp mean, +0.62 pp best) indicates the benefit of additional trials is small.

---

## 5. Per-Parameter Effective Ranges

### Feature Flags (Binary)

| Feature | Top-Q ON | Top-Q OFF | Bot-Q ON | Bot-Q OFF | Verdict |
|---------|----------|-----------|----------|-----------|---------|
| `use_normalized_x` | **125** | 0 | 83 | **42** | Required |
| `use_normalized_y` | **125** | 0 | 38 | **87** | Required |
| `use_horizontal_direction` | **125** | 0 | 101 | 24 | Required |
| `use_vertical_direction` | 0 | **125** | 59 | 66 | **Harmful** |
| `use_cycle_count` | **125** | 0 | 91 | 34 | Required |
| `use_angle_with_ox` | **125** | 0 | 102 | 23 | Required |

**100% of top-quartile trials** use the exact feature set: `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}` with `vertical_direction` OFF.

**0% of top-quartile trials** enable `vertical_direction`. When enabled (163 trials), mean accuracy drops to 67.55% vs. 70.85% when disabled (337 trials); maximum with it enabled is 74.58% vs. 77.56% without.

**`[Inference]`**: `vertical_direction` consistently degrades accuracy. The feature likely introduces noise or dilutes more discriminative features for this concept set. This is the single most clear-cut finding of the study.

### Continuous Parameters

Format: `top-quartile [min, median, max]` vs. `bottom-quartile [min, median, max]`. Search space bounds in parentheses.

**skel_threshold** (100, 220, step=10):
- Top-Q: [100, 110, 140]
- Bot-Q: [100, 140, 220]
- Best: 110
- **Best at near-lower-boundary** (8.3% of range). Values >= 160 never appear in top quartile.

**simplification_epsilon** (0.5, 10.0):
- Top-Q: [2.34, 4.24, 5.73]
- Bot-Q: [0.57, 4.47, 9.51]
- Best: 4.62
- Top-Q concentrated in [3.3, 5.6]; extreme values (< 2.0 or >= 8.0) produce poor results.

**ged_timeout** (0.1, 15.0):
- Top-Q: [5.93, 10.09, 13.41]
- Bot-Q: [0.57, 9.57, 14.40]
- Best: 6.25
- Values below 3s consistently underperform (5 trials, mean 43.1%).

**norm_x** (0.1, 5.0):
- Top-Q: [1.04, 2.87, 4.18]
- Bot-Q: [0.73, 2.55, 4.83]
- Best: 3.38

**norm_y** (0.1, 5.0):
- Top-Q: [0.25, 2.01, 4.11]
- Bot-Q: [0.89, 2.73, 4.90]
- Best: 2.26
- **`[Inference]`**: Top-quartile prefers slightly lower norm_y (median 2.0 vs. 2.7), implying tighter Y-axis discrimination helps.

**norm_hdir** (0.1, 4.0):
- Top-Q: [0.39, 2.20, 3.62]
- Bot-Q: [0.45, 1.80, 3.75]
- Best: 2.70

**norm_vdir** (0.1, 4.0):
- Top-Q: [1.78, 2.99, 3.95]
- Bot-Q: [0.39, 2.27, 3.74]
- Best: 3.06
- Top-Q has higher floor (1.78 vs. 0.39). **`[Inference]`**: Even though `vertical_direction` is OFF in all top-Q trials, this normalizer still affects the cost function when the feature is present on matched nodes in other contexts.

**norm_cycle** (0.5, 8.0):
- Top-Q: [0.53, 2.73, 6.38]
- Bot-Q: [0.56, 3.24, 7.53]
- Best: 2.66
- Wide spread in both quartiles.

**norm_angle** (10.0, 360.0):
- Top-Q: [205.61, 286.35, 351.94]
- Bot-Q: [44.01, 221.61, 358.76]
- Best: 252.33
- Top-Q has much higher floor (205.6 vs. 44.0). **`[Inference]`**: Low norm_angle values (< 200) penalize angle differences too harshly; the feature works best as a soft discriminator with high normalizer.

### Node Costs (Derived)

| Cost Level | Top-Q Median | Bot-Q Median | Best | Default |
|------------|-------------|-------------|------|---------|
| MINOR | 0.232 | 0.238 | 0.230 | 0.25 |
| GENERAL | 0.470 | 0.418 | 0.468 | 0.40 |
| SEVERE | 0.693 | 0.609 | 0.754 | 0.65 |
| NO_MATCH | 1.303 | 1.347 | 1.181 | 1.00 |
| IMPOSSIBLE | 9.15 | 17.84 | 7.38 | 100.0 |

**`[Inference]`**: The study consistently prefers wider cost gaps between levels than the current defaults. Top-Q SEVERE/MINOR ratio is 2.94 (vs. default 2.60), and NO_MATCH/SEVERE ratio is 1.91 (vs. default 1.54). The graduated cost structure benefits from more separation between penalty levels.

**`[Inference]`**: IMPOSSIBLE cost is best kept low (median 9.15 in top-Q, best at 7.38 vs. default 100.0). A lower IMPOSSIBLE value reduces the penalty for label-incompatible node pairs, which may help when concept graphs have mixed node types that create spurious IMPOSSIBLE costs.

---

## 6. Dead Zones

### Feature Combinations to Avoid

| Dead zone | Evidence | Impact |
|-----------|----------|--------|
| `use_normalized_x=0` | 42 trials, mean 51.2%, max 68.4% | **-20.4 pp mean vs. enabled** |
| `use_normalized_y=0` | 196 trials, mean 66.1%, max 74.1% | **-5.6 pp mean vs. enabled** |
| `use_vertical_direction=1` | 163 trials, mean 67.6%, max 74.6% | **-3.3 pp mean vs. disabled**, ceiling -3.0 pp |
| `use_cycle_count=0` | 45 trials, mean 59.2%, max 72.7% | Present in 34/125 bot-Q trials |

### Skeletonization Threshold to Avoid

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| 100-130 | 357 | 71.9% | 77.6% | Safe zone |
| 140-150 | 89 | 67.3% | 75.2% | Marginal |
| **160-220** | **50** | **59.7%** | **72.2%** | **Dead zone** |

`skel_threshold >= 160` never produced a top-quartile result (top-Q ceiling: 140). Mean accuracy degrades monotonically: 160->63.1%, 170->62.0%, 180->61.3%, 200->48.2%, 220->39.4%.

### Simplification Epsilon to Avoid

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| [0.5, 2.0) | 17 | 67.4% | 73.3% | Moderate risk |
| [2.0, 6.0) | 437 | 70.6% | 77.6% | Safe zone |
| **[8.0, 10.0)** | **10** | **45.9%** | **59.4%** | **Dead zone** |

### GED Timeout to Avoid

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| **[0.1, 3.0)** | **5** | **43.1%** | **57.7%** | **Dead zone** |
| [3.0, 6.0) | 19 | 61.2% | 74.9% | Risky |
| [6.0, 15.0) | 476 | 70.2% | 77.6% | Safe zone |

### Cost Impossible to Avoid

| Range | Trials | Mean | Max |
|-------|--------|------|-----|
| [1, 20) | 323 | 70.5% | 77.6% |
| **[50, 200)** | **49** | **66.7%** | **75.5%** |

**`[Inference]`**: Very high IMPOSSIBLE costs (50+) tend to produce worse results. The penalty overwhelms the GED budget when concept-image node type mismatches occur, making all concepts look equally bad.

---

## 7. Open Questions

These are hypotheses, not conclusions. Each requires further experimentation.

1. ~~**Full-set validation required.**~~ **Done.** Full run: **75.96%** `[FULL]` vs. 77.56% `[QUICK]`. Gap: -1.60 pp. See §2 "Full-Set Validation".

2. **Why does `vertical_direction` hurt?** Zero top-quartile trials enable it. Possible explanations: (a) it correlates too highly with `horizontal_direction`, causing redundant cost dilution; (b) it has different semantic meaning on Point vs. Vector nodes, confusing the matcher; (c) the concept set does not have discriminative vertical direction patterns. An ablation study (best params + vertical_direction ON) would isolate this.

3. **Should `skel_threshold` search range be narrowed?** Best at 110, top-Q ceiling at 140. The current search space [100, 220] wastes many trials on values >= 150. A narrower range [90, 150] would allow finer exploration. However, threshold 110 vs. the deployed default of 180 is a significant change that may affect skeletonization quality in ways not captured by the 25% sample.

4. **Should `cost_impossible` be reduced from 100 to ~7-10?** The study strongly prefers low values. But this changes a fundamental safety mechanism -- IMPOSSIBLE costs prevent matching structurally incompatible nodes. Reducing it to ~7 means an impossible match costs only ~10x a SEVERE match. Impact on edge cases needs investigation.

5. **Is `norm_cycle` sensitive?** Top-Q range spans [0.53, 6.38] with fANOVA importance of only 1.3%. The current default (1.0) sits below the top-Q median (2.73). A focused sweep at [1.0, 4.0] with other params fixed would clarify whether raising it to ~2.7 helps.

6. **Are there per-class effects hidden by aggregate accuracy?** This study optimized aggregate accuracy. A configuration that sacrifices one class to boost others could appear optimal. Per-class recall at the best configuration is now available in the full-set validation (§2) — classes 2 and 5 have notably low recall (63.2%, 64.6%), while class 4 has the lowest precision (49.8%).

7. **Normalizer asymmetry: norm_y < norm_x.** The best trial has norm_y=2.26 vs. norm_x=3.38. Top-Q medians: norm_y=2.01 vs. norm_x=2.87. **`[Inference]`**: Y-axis position may be more discriminative than X-axis for these digit concepts, warranting tighter (lower normalizer) matching. This could relate to digit vertical structure (e.g., top-heavy vs. bottom-heavy digits).

---

## 8. Recommended Next Steps

Ordered by expected information value:

1. ~~**Run full-set validation**~~ **Done.** Result: 75.96% `[FULL]`. See §2.

2. **Update defaults to match findings that have zero ambiguity:**
   - `use_vertical_direction=0` (OFF) -- 100% consensus in top quartile
   - `skel_threshold=110` -- consistent top performer, current default 180 is in dead zone
   - Feature set: `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}`

3. **Investigate `cost_impossible` reduction** -- deploy with IMPOSSIBLE=7.38 alongside a control at IMPOSSIBLE=100.0 on the same test set. This is the largest default-vs-optimal gap in the study.

4. ~~**Narrow search space for follow-up study**~~ **Done.** See §10 below. Narrowed study ran 200 trials with TPE sampler on the reduced search space.

---

## 9. Artifacts (Broad Study)

All experiment artifacts are in `experiments/naturalagi-hp-tuning-ged-cmaes/`:

| Artifact | Path | Description |
|----------|------|-------------|
| This document | `findings.md` | Full analysis with findings and recommendations |
| Best trial params | `best_params.json` | Trial 442 parameters in pipeline-ready JSON format |
| Convergence data | `convergence.csv` | Per-trial accuracy + running best (for plotting) |
| Parameter importance | `param_importance.csv` | fANOVA importance scores for all 20 parameters |
| All trials | `all_trials.csv` | Complete 500-trial dataset with all parameters |
| Optuna DB | `study.db` | Symlink to source SQLite database |

---

# Follow-Up: Narrowed GED Study (`naturalagi-hp-tuning-ged-narrowed`)

This section documents the follow-up study that acted on recommendation §8.4 from the broad study: narrowing the search space and fixing the optimal feature set.

## 10. Narrowed Study Configuration

| Field | Value |
|-------|-------|
| Study name | `naturalagi-hp-tuning-ged-narrowed` |
| DB | `study_narrowed.db` (symlinked in this folder) |
| Sampler | `TPESampler` (switched from CMA-ES) |
| Direction | maximize |
| Objective | `accuracy_score(y_true, y_pred)` on 25% stratified sample |
| Comparison method | GED only |
| Sample fraction | 0.25 (~1,949 images) |
| Classes evaluated | 10 (digits 0-9) |
| Concept set | 13 concepts across 10 classes (same as broad study) |
| n_trials budgeted | 201 |
| n_trials completed | 200 |
| n_trials failed | 1 (trial 1) |
| Fixed feature set | `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}` |
| Git commit | `ce29c54` (same as broad study) |
| Wall clock time | 10.4 hours (2026-03-08 18:26 to 2026-03-09 04:48) |
| Per-trial duration | median 2.6 min, mean 3.1 min, range [1.6 min, 10.1 min] |

### Narrowed Search Space

Feature flags were **removed** — the feature set was fixed to the unanimous top-quartile winner from the broad study. `norm_vdir` was also removed since `vertical_direction` is no longer in the feature set.

**Compared to broad study — narrowed ranges:**

| Parameter | Broad range | Narrowed range | Rationale |
|-----------|-------------|----------------|-----------|
| `skel_threshold` | [100, 220] step=10 | **[90, 150]** step=10 | Values ≥ 160 were dead zone |
| `simplification_epsilon` | [0.5, 10.0] | **[2.0, 7.0]** | Values < 2.0 and ≥ 8.0 were dead zones |
| `ged_timeout` | [0.1, 15.0] | **[4.0, 15.0]** | Values < 3.0 were dead zone |
| `cost_impossible` | [1.0, 200.0] log | **[2.0, 50.0]** log | Values > 50 were dead zone |
| `norm_angle` | [10.0, 360.0] | **[150.0, 360.0]** | Values < 200 were poor in broad study |
| `norm_x` | [0.1, 5.0] | **[1.0, 5.0]** | Trimmed extreme low end |
| `norm_y` | [0.1, 5.0] | **[0.5, 4.5]** | Trimmed extreme low end |
| `norm_hdir` | [0.1, 4.0] | **[0.5, 4.0]** | Trimmed extreme low end |
| Feature flags | 6 binary (64 combos) | **Fixed** | Unanimous consensus from broad study |
| `norm_vdir` | [0.1, 4.0] | **Removed** | Feature disabled |

**Unchanged ranges:** `cost_minor` [0.05, 0.4], `gap_minor_general` [0.05, 0.3], `gap_general_severe` [0.05, 0.3], `cost_no_match` [0.8, 1.8], `norm_cycle` [0.5, 6.0].

---

## 11. Narrowed Study Results

### Objective Distribution (200 completed trials)

| Statistic | Value |
|-----------|-------|
| **Best** | **78.42%** `[QUICK, 25% sample]` |
| Worst | 50.26% |
| Median | 74.86% |
| Mean | 74.16% |
| Stdev | 3.48 pp |

Compared to the broad study: mean improved 69.78% → 74.16% (+4.38 pp), stdev dropped 7.72 → 3.48 pp. The narrowed search space eliminated most of the low-performing region.

### Full-Set Validation (run_20260309_044856)

Trial 167 parameters validated on **100% of test set** (7,814 images, 17 DLQ, 7,797 classified).

| Metric | Value `[FULL]` | Quick proxy `[QUICK]` |
|--------|---------------|-----------------------|
| **Accuracy** | **75.55%** | 78.42% |
| Precision | 77.62% | — |
| Recall | 75.55% | — |
| F1 | 76.05% | — |

- **Quick-to-full gap: -2.87 pp** (78.42% → 75.55%), larger than the broad study's gap (-1.60 pp).

**Per-class metrics:**

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| 0 | 95.6% | 78.2% | 86.0% | 1,000 |
| 1 | 84.4% | 90.5% | 87.3% | 997 |
| 2 | 71.8% | 62.1% | 66.6% | 945 |
| 3 | 69.6% | 71.1% | 70.4% | 983 |
| 4 | 50.8% | 60.7% | 55.3% | 496 |
| 5 | 60.9% | 60.9% | 60.9% | 478 |
| 6 | 75.5% | 87.1% | 80.9% | 753 |
| 7 | 73.3% | 87.8% | 79.9% | 989 |
| 8 | 96.1% | 72.3% | 82.5% | 372 |
| 9 | 89.0% | 68.4% | 77.3% | 784 |

**`[Inference]`**: The larger quick-to-full gap (-2.87 pp vs. -1.60 pp from the broad study) suggests the narrowed best trial may be slightly overfit to the 25% sample. The full-set accuracy (75.55%) is lower than the broad study's full-set result (75.96%), despite a higher quick proxy. This means the narrowed study improved quick-sample accuracy without improving generalization.

### Best Trial

- **Trial 167** of 200, accuracy = **78.42%** `[QUICK]`, **75.55%** `[FULL]`
- Best trial parameters:

| Parameter | Narrowed best | Broad best | Current default |
|-----------|--------------|-----------|-----------------|
| `ged_timeout` | 8.72 | 6.25 | 5.0 |
| `skel_threshold` | 140 | 110 | 180 |
| `simplification_epsilon` | 4.55 | 4.62 | 5.0 |
| `norm_x` | 3.75 | 3.38 | 3.0 |
| `norm_y` | 3.67 | 2.26 | 3.0 |
| `norm_hdir` | 3.11 | 2.70 | 2.0 |
| `norm_cycle` | 3.28 | 2.66 | 1.0 |
| `norm_angle` | 279.36 | 252.33 | 180.0 |

**Derived node costs at best trial:**

| Level | Narrowed best | Broad best | Current default |
|-------|--------------|-----------|-----------------|
| NO_COST | 0.0 | 0.0 | 0.0 |
| MINOR | 0.254 | 0.230 | 0.25 |
| GENERAL | 0.449 | 0.468 | 0.40 |
| SEVERE | 0.725 | 0.754 | 0.65 |
| NO_MATCH | 1.304 | 1.181 | 1.00 |
| IMPOSSIBLE | 6.68 | 7.38 | 100.0 |

### Top 10 Trials

| Rank | Trial | Accuracy `[QUICK]` | skel_threshold | epsilon | ged_timeout |
|------|-------|-----------|----------------|---------|-------------|
| 1 | 167 | 78.42% | 140 | 4.55 | 8.72 |
| 2 | 28 | 77.70% | 140 | 3.80 | 9.70 |
| 3 | 186 | 77.66% | 130 | 4.91 | 8.80 |
| 4 | 122 | 77.10% | 130 | 5.26 | 9.39 |
| 5 | 148 | 77.05% | 140 | 4.69 | 10.45 |
| 6 | 97 | 76.91% | 150 | 4.87 | 9.83 |
| 7 | 146 | 76.86% | 140 | 5.06 | 8.22 |
| 8 | 70 | 76.81% | 120 | 4.03 | 11.01 |
| 9 | 193 | 76.77% | 130 | 4.52 | 8.78 |
| 10 | 171 | 76.63% | 130 | 4.45 | 8.28 |

**Top-10 `skel_threshold` range: [120, 150].** All top-10 use `skel_threshold` ≥ 120. The broad study's best at 110 is absent from the narrowed top-10.

### Bottom 5 Trials

| Rank | Trial | Accuracy `[QUICK]` | Key failure factor |
|------|-------|-----------|-------------------|
| 196 | 3 | 68.76% | skel_threshold=100, low norm_x=1.56 |
| 197 | 20 | 60.60% | cost_impossible=26.7 |
| 198 | 4 | 51.21% | cost_impossible=42.4 |
| 199 | 7 | 50.46% | skel_threshold=90 |
| 200 | 5 | 50.26% | skel_threshold=90, cost_impossible=5.5 |

---

## 12. Narrowed Study — Parameter Importances (fANOVA)

With feature flags fixed, the importance landscape shifted dramatically.

| Rank | Parameter | Importance | Broad importance | Δ Rank |
|------|-----------|------------|-----------------|--------|
| 1 | **`cost_minor`** | **0.8752** | 0.0166 (rank 9) | +8 |
| 2 | `gap_minor_general` | 0.0594 | 0.0523 (rank 3) | +1 |
| 3 | `cost_impossible` | 0.0188 | 0.0050 (rank 18) | +15 |
| 4 | `skel_threshold` | 0.0163 | 0.0518 (rank 4) | 0 |
| 5 | `cost_no_match` | 0.0162 | 0.0213 (rank 8) | +3 |
| 6 | `simplification_epsilon` | 0.0038 | 0.0056 (rank 17) | +11 |
| 7 | `norm_x` | 0.0034 | 0.0080 (rank 13) | +6 |
| 8 | `gap_general_severe` | 0.0030 | 0.0076 (rank 14) | +6 |
| 9 | `norm_y` | 0.0016 | 0.0046 (rank 20) | +11 |
| 10 | `ged_timeout` | 0.0012 | 0.0266 (rank 6) | -4 |
| 11 | `norm_angle` | 0.0005 | 0.0103 (rank 12) | +1 |
| 12 | `norm_cycle` | 0.0004 | 0.0130 (rank 10) | -2 |
| 13 | `norm_hdir` | 0.0003 | 0.0072 (rank 15) | +2 |

**Key observations:**

- **`cost_minor` dominates at 87.5%** — far exceeding any single parameter in the broad study (where `use_normalized_x` was 58.9%). With feature selection settled, the MINOR cost level is the most critical tuning knob.
- **`[Inference]`**: `cost_minor` matters so much because it sets the baseline penalty for _any_ property mismatch. GENERAL and SEVERE are derived from it via gaps. A MINOR value below 0.15 produces catastrophic results (mean 53.1% for 4 trials), while the [0.15, 0.35] range is safe.
- All normalizer importances dropped below 0.4%, confirming the broad study's finding that exact normalizer values matter far less than feature inclusion.
- `ged_timeout` importance dropped from rank 6 to rank 10 — the narrowed floor of 4.0s (vs. 0.1s) eliminated the dead zone that inflated its importance.

---

## 13. Narrowed Study — Convergence Analysis

### Improvement Trajectory

| Trial | Best accuracy `[QUICK]` | Phase |
|-------|-----------|-------|
| 0 | 74.08% | TPE startup |
| 15 | 75.09% | TPE |
| 18 | 75.76% | TPE |
| 21 | 76.12% | TPE |
| 28 | 77.70% | TPE |
| **167** | **78.42%** | TPE |

### Per-Quartile Statistics

| Quartile | Trials | Mean | Best | Stdev |
|----------|--------|------|------|-------|
| Q1 (0-50) | 50 | 72.01% | 77.70% | 6.05 pp |
| Q2 (51-100) | 50 | 74.83% | 76.91% | 1.63 pp |
| Q3 (101-150) | 50 | 74.43% | 77.10% | 1.45 pp |
| Q4 (151-200) | 50 | 75.37% | 78.42% | 1.00 pp |

### Convergence Indicators

- Best value (78.42%) first achieved at trial 167 (83.5% of budget).
- Stdev decreased monotonically: 6.05 → 1.63 → 1.45 → 1.00 pp.
- Only 6 improvement milestones across 200 trials (vs. 14 across 500 in broad study), indicating the narrowed space starts closer to the optimum.
- Last 10 trials: mean 75.87%, stdev 0.57 pp, range [74.94%, 76.77%].
- The Q1 starting accuracy (74.08%) exceeds the broad study's Q1 best (74.10%), confirming the search space narrowing was effective.

**`[Inference]`**: The study has converged. Q4 stdev of 1.00 pp is very tight. The long gap between trial 28 (77.70%) and trial 167 (78.42%) — a +0.72 pp gain over 139 trials — suggests the remaining landscape is nearly flat. Additional trials are unlikely to yield gains beyond ~0.5 pp.

---

## 14. Narrowed Study — Per-Parameter Effective Ranges

Format: `top-quartile [min, median, max]` vs. `bottom-quartile [min, median, max]`.

**skel_threshold** (90, 150, step=10):
- Top-Q: [120, 140, 150]
- Bot-Q: [90, 140, 150]
- Best: 140
- Values 90-110 produced only 12 trials total (6%), all with mean accuracy < 72%. **`[Inference]`**: The narrowed study shifts the sweet spot upward from 110 (broad study) to 130-140. This may reflect interaction with other parameters — the TPE sampler explored a different region of the joint space.

**skel_threshold breakdown:**

| Value | Trials | Mean | Max |
|-------|--------|------|-----|
| 90 | 3 | 57.43% | 71.57% |
| 100 | 4 | 70.82% | 72.46% |
| 110 | 5 | 71.26% | 74.83% |
| 120 | 15 | 73.54% | 76.81% |
| 130 | 52 | 74.97% | 77.66% |
| 140 | 70 | 74.36% | 78.42% |
| 150 | 51 | 74.76% | 76.91% |

**cost_minor** (0.05, 0.40) — **dominant parameter**:
- Top-Q: [0.198, 0.248, 0.292]
- Bot-Q: [0.062, 0.266, 0.373]
- Best: 0.254
- **Dead zone: [0.05, 0.15)** — only 4 trials, mean 53.13%, max 60.60%.
- Top-Q is tightly concentrated around 0.20-0.29. The effective sweet spot is remarkably narrow.

**cost_impossible** (2.0, 50.0, log):
- Top-Q: [4.09, 11.34, 33.51]
- Bot-Q: [2.02, 9.39, 42.42]
- Best: 6.68
- Breakdown: [2-10) mean 74.11%, [10-20) mean 74.48%, [20-50) mean 73.45%.
- The range [2-20) is broadly safe; values ≥ 20 show slight degradation but not catastrophic (unlike the broad study's 50+ dead zone).

**simplification_epsilon** (2.0, 7.0):
- Top-Q: [2.72, 4.66, 5.60]
- Bot-Q: [2.18, 4.25, 6.32]
- Best: 4.55
- Consistent with broad study: sweet spot in [3.5, 5.5].

**ged_timeout** (4.0, 15.0):
- Top-Q: [5.82, 9.20, 13.21]
- Bot-Q: [6.05, 9.33, 14.81]
- Medians nearly identical — timeout is not a discriminator in this range, confirming the broad study's dead zone was below 3s.

**Normalizers:**

| Normalizer | Top-Q median | Bot-Q median | Best | Broad best |
|------------|-------------|-------------|------|-----------|
| `norm_x` | 3.92 | 3.73 | 3.75 | 3.38 |
| `norm_y` | 3.48 | 3.23 | 3.67 | 2.26 |
| `norm_hdir` | 2.49 | 2.38 | 3.11 | 2.70 |
| `norm_cycle` | 3.16 | 3.15 | 3.28 | 2.66 |
| `norm_angle` | 262.67 | 261.38 | 279.36 | 252.33 |

**`[Inference]`**: Normalizers shifted uniformly higher compared to the broad study. Most notable is `norm_y`: broad best was 2.26, narrowed best is 3.67 — a reversal of the broad study's finding that Y-axis should be stricter. This challenges hypothesis §7.7 from the broad study. With all other parameters changed simultaneously, the norm_y preference likely depends on the cost structure.

### Derived Node Costs

| Cost Level | Top-Q Median | Bot-Q Median | Narrowed Best | Broad Best | Default |
|------------|-------------|-------------|--------------|-----------|---------|
| MINOR | 0.248 | 0.266 | 0.254 | 0.230 | 0.25 |
| GENERAL | 0.431 | 0.433 | 0.449 | 0.468 | 0.40 |
| SEVERE | 0.635 | 0.604 | 0.725 | 0.754 | 0.65 |
| NO_MATCH | 1.210 | 1.234 | 1.304 | 1.181 | 1.00 |
| IMPOSSIBLE | 11.34 | 9.39 | 6.68 | 7.38 | 100.0 |

**`[Inference]`**: Both studies agree on the cost structure direction: wider gaps between levels and low IMPOSSIBLE (6-11 vs. default 100). The narrowed best and broad best are remarkably consistent for MINOR (0.254 vs. 0.230) and SEVERE (0.725 vs. 0.754). NO_MATCH is consistently above 1.0 (both studies), far from the default 1.0 — suggesting it could be raised to ~1.2-1.3.

---

## 15. Narrowed Study — Dead Zones

### cost_minor — Critical Dead Zone

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| **[0.05, 0.15)** | **4** | **53.13%** | **60.60%** | **Dead zone** |
| [0.15, 0.25) | 89 | 74.78% | 77.70% | Safe |
| [0.25, 0.35) | 106 | 74.45% | 78.42% | Safe |
| [0.35, 0.40] | 1 | 72.39% | 72.39% | Undersampled |

**`[Inference]`**: The [0.15, 0.35] range is safe and fairly flat. The dead zone below 0.15 is consistent with the cost_minor dominance in fANOVA (87.5%) — a few trials with very low cost_minor cause dramatic accuracy drops, inflating the parameter's importance score.

### skel_threshold — Marginal Zone

| Range | Trials | Mean | Max | Verdict |
|-------|--------|------|-----|---------|
| **[90, 110]** | **12** | **67.96%** | **74.83%** | **Marginal** |
| [120, 150] | 188 | 74.50% | 78.42% | Safe zone |

### cost_impossible — Soft Zone

| Range | Trials | Mean | Max |
|-------|--------|------|-----|
| [2, 10) | 96 | 74.11% | 78.42% |
| [10, 20) | 76 | 74.48% | 77.10% |
| [20, 50) | 28 | 73.45% | 76.81% |

No hard dead zone — the entire [2, 50) range produces viable results. The best trial used 6.68, and the [2, 20) range is slightly preferred.

---

## 16. Cross-Study Consensus

Parameters where both the broad and narrowed studies agree:

| Finding | Broad study | Narrowed study | Confidence |
|---------|------------|----------------|------------|
| Feature set | `{norm_x, norm_y, hdir, cycle, angle}`, no vdir | Fixed (same set) | **High** |
| IMPOSSIBLE cost | Best 7.38, top-Q median 9.15 | Best 6.68, top-Q median 11.34 | **High** — both prefer ~7-11 vs. default 100 |
| MINOR cost | Best 0.230, top-Q median 0.232 | Best 0.254, top-Q median 0.248 | **High** — converged to ~0.23-0.25 |
| SEVERE cost | Best 0.754, top-Q median 0.693 | Best 0.725, top-Q median 0.635 | **High** — converged to ~0.65-0.75 |
| NO_MATCH cost | Best 1.181, top-Q median 1.303 | Best 1.304, top-Q median 1.210 | **High** — both > 1.0 (default is 1.0) |
| epsilon | Best 4.62, top-Q [2.3, 5.7] | Best 4.55, top-Q [2.7, 5.6] | **High** — sweet spot ~4.3-4.7 |
| norm_angle | Top-Q floor 205.6, best 252.3 | Top-Q floor 203.1, best 279.4 | **Moderate** — floor consistent, best diverges |
| skel_threshold | Best 110, top-Q [100, 140] | Best 140, top-Q [120, 150] | **Low** — direction disagrees |
| norm_y | Top-Q median 2.01, best 2.26 | Top-Q median 3.48, best 3.67 | **Low** — direction disagrees |

**`[Inference]`**: `skel_threshold` and `norm_y` show the least cross-study stability. These parameters likely interact with other variables in ways that make their optima shift with the surrounding parameter landscape. For deployment, the middle ground (skel_threshold ~120-130, norm_y ~3.0) is the safest choice.

---

## 17. Updated Recommended Next Steps

Updated based on both the broad and narrowed studies:

1. ~~**Run full-set validation of narrowed best trial.**~~ **Done.** Full run: **75.55%** `[FULL]` vs. 78.42% `[QUICK]`. Gap: -2.87 pp — larger than broad study's -1.60 pp. Full-set accuracy is slightly below the broad study's 75.96% `[FULL]`, suggesting the narrowed best trial overfit the 25% sample. See §11 "Full-Set Validation".

2. **Adopt consensus defaults immediately** (high-confidence findings from both studies):
   - Feature set: `{normalized_x, normalized_y, horizontal_direction, cycle_count, angle_with_ox}` (no vertical_direction)
   - `cost_impossible`: 7.0 (both studies agree on ~7-11, down from 100)
   - `cost_minor`: 0.25, `GENERAL`: 0.45, `SEVERE`: 0.72
   - `cost_no_match`: 1.25 (both studies > 1.0)
   - `simplification_epsilon`: 4.5
   - `norm_angle`: 260 (both studies > 200)
   - `norm_cycle`: 3.0 (both studies > 2.5)

3. **Resolve skel_threshold disagreement.** Run a focused 1D sweep of skel_threshold [100, 110, 120, 130, 140, 150] with all other parameters fixed at consensus values. This isolates the variable without confounding from the rest of the search space.

4. **Resolve norm_y disagreement.** Same approach — 1D sweep of norm_y [1.5, 2.0, 2.5, 3.0, 3.5, 4.0] with other parameters fixed.

---

## 18. Artifacts (Narrowed Study)

| Artifact | Path | Description |
|----------|------|-------------|
| Best trial params | `best_params_narrowed.json` | Trial 167 parameters in pipeline-ready JSON format |
| Convergence data | `convergence_narrowed.csv` | Per-trial accuracy + running best (for plotting) |
| Parameter importance | `param_importance_narrowed.csv` | fANOVA importance scores for all 13 parameters |
| All trials | `all_trials_narrowed.csv` | Complete 200-trial dataset with all parameters |
| Optuna DB | `study_narrowed.db` | Symlink to source SQLite database |
