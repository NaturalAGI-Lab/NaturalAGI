# Run Analysis: run_20260424_132908

**Date:** 2026-04-24
**Git commit:** `4dc794e`
**Branch:** `feat/graph-features-and-cleanup`

---

## TL;DR

- **Accuracy: 79.24% [FULL, 12,000 images, 10 classes]** — new project baseline
- **+4.21pp vs prior baseline** from a single-line change in `cost_functions.py`
- **Precision +5.69pp, F1 +4.39pp** — not just more correct predictions, also fewer false positives overall.
- **Class 5 F1 +21.3pp (65.2→86.5)** and **class 3 F1 +12.6pp (72.6→85.2)** — compression pathology resolved structurally.
- **Class 7 precision collapses 67→53%** (recall 97.4%) — `7_1`-attractor over-fires under uncapped costs. Top-1 open issue.

---

## 1. What was compared

Five families of fixes for GED similarity-compression, benchmarked on identical run params (14 features, `diagnostic_weight_epsilon=1.0`, tuned `node_costs`, `ged_timeout=15s`, `skeletonization_threshold=110`, `simplification_epsilon=4.55`), all with 16 classification instances. Only the compression-fix mechanism varied.

| Rank | Family | Mechanism | Run ID | Full Acc | Δ vs baseline |
|------|--------|-----------|--------|----------|---------------|
| **1** | **E** | **Remove per-feature cost cap** | **`run_20260424_132908`** | **79.24%** | **+4.21pp** ✅ |
| 2 | C | Drop log-prior (pure argmin) | `run_20260423_233030` | 72.00% | −3.03pp |
| 3 | D | Per-image z-score + log-prior | `run_20260423_234853` | 71.99% | −3.04pp |
| 4 | B | Per-image softmax + log-prior (T=0.02) | `run_20260423_231236` | 72.78% | −2.25pp |
| 5 | A | Pointwise exp(-c/T) + log-prior (T=1.5) | `run_20260423_225107` | 61.74% | −13.29pp |

**Conclusion:** Family E wins by a wide margin. The four scoring-transform families (A/B/C/D) all regressed. Compression pathology is a **cost-generation** problem at the per-feature level, not a scoring-function problem.

---

## 2. The change

`src/classification/graph_similarity/cost_functions.py`, `_calculate_properties_similarity_cost` (around line 169):

```python
# Before (capped):
total_cost += min(property_cost, normalized_w)

# After (Family E — uncapped):
total_cost += property_cost
```

The cap clamped per-feature contributions to their normalized weight (~0.07 for a 14-feature setup), squeezing all cost differences into a narrow band. Removing it lets out-of-range features contribute full `NO_MATCH` (1.0), widening the cost distribution at the source so Boria normalization produces wider similarity margins downstream.

---

## 3. Per-class F1 (vs prior baseline)

| Class | exp_052 F1 | exp_058 F1 | Δ |
|-------|-----------:|-----------:|---:|
| 0 | 90.1 | 87.5 | −2.6 |
| 1 | 87.8 | 89.4 | +1.6 |
| 2 | 64.2 | 65.8 | +1.6 |
| 3 | 72.6 | **85.2** | **+12.6** ✅ |
| 4 | 82.8 | 83.2 | +0.4 |
| 5 | 65.2 | **86.5** | **+21.3** ✅ |
| 6 | 76.2 | 76.4 | +0.2 |
| 7 | 76.5 | **68.6** | **−7.9** ⚠️ |
| 8 | 67.5 | 71.6 | +4.1 |
| 9 | 84.2 | 88.4 | +4.2 |

---

## 4. Open issues (tracked elsewhere)

- **Class 7 precision collapse**: 67%→53%. `7_1` attractor re-activated under uncapped costs. See [`researches/7_1_attractor_fix.md`](../../researches/7_1_attractor_fix.md). Candidate fixes: raise `node_ins_cost` for 7_1, retrain with tighter ranges, add a second `7_x` concept.
- **Family E one-liner not yet git-committed**: the change lives in the working tree on `feat/graph-features-and-cleanup`. Part of the current review/PR scope.

---

## 5. Artifacts (this folder)

- [`findings.md`](findings.md) — this summary (comparison + what changed)
- [`run_findings.md`](run_findings.md) — raw per-run analysis (error breakdown, DLQ causes, 7_1 attractor details)
- [`run_config.json`](run_config.json) — exact params used
- [`metrics.csv`](metrics.csv) — headline numbers (acc/precision/recall/F1)
- [`per_class_metrics.csv`](per_class_metrics.csv) — per-class precision/recall/F1 for all 10 classes
- [`confusion_matrix.png`](confusion_matrix.png) — visual confusion pattern
- [`incorrect_results.csv`](incorrect_results.csv) — every misclassified image: `image_id`, `image_path`, `expected`, `predicted`, timing.
- [`concept_graphs.json`](concept_graphs.json) — concept graphs active for this run (357 KB)
