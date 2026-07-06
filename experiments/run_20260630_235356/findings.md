# Run Analysis: run_20260630_235356

**Date:** 2026-06-30
**Git commit:** `f34b049` (working tree dirty: retrained concepts + cost_functions.py + run config)
**Branch:** `feature/concept-creator-fixes`

---

## TL;DR

- **Accuracy: 91.13%** on **8,685 successfully classified** complete-only MNIST images (8,707 submitted, 22 DLQ) — **new project baseline**.
- **+5.33pp over the prior baseline** (`run_20260427_144233`, 85.80%).
- This is a **multi-factor branch advance**, not a single-knob change. The four changes below moved together vs the prior baseline, so the lift is not cleanly attributable to any one of them without ablation.
- The two long-standing pain points both improved sharply: **class 2 recall 60.0% → 77.6%** and **class 7 precision 66.2% → 82.0%**. Plus **class 8 recall 74.7% → 94.5%** and **class 3 recall 85.4% → 95.8%**.

---

## 1. Headline metrics

| Metric | Value |
|---|---|
| Total submitted | 8,707 |
| DLQ | 22 |
| Successfully classified | 8,685 |
| **Accuracy** | **91.13%** |
| Precision | 91.92% |
| Recall | 91.13% |
| F1 | 91.34% |

Full test, `sample_fraction = 1.0`, 10 classes, 13 concepts.

---

## 2. What changed vs the prior baseline (`run_20260427_144233`)

Four things moved together on the `feature/concept-creator-fixes` branch:

1. **Retrained concept topologies** (concept-creator fixes). Node counts:

   | Concept | Prior | This run | Δ |
   |---|---:|---:|---:|
   | 0_1 | 12 | 10 | −2 |
   | 2_2 | 10 | **12** | **+2** |
   | 3_1 | 11 | 9 | −2 |
   | 5_1 | 9 | 7 | −2 |
   | 8_1 | 15 | **11** | **−4** |

   (1_1, 1_3, 2_1, 4_1, 4_2, 6_1, 7_1, 9_2 unchanged.) `2_2` gaining coverage lines up with the class-2 recall jump; `8_1` shrinking lines up with class-8 recall jump.

2. **Skeletonization junction-bridge collapse** (commit `f34b049`) — collapses thinning-artifact junction bridges, producing cleaner skeleton graphs upstream of contour analysis.

3. **Lower, retuned cost ladder**:

   ```python
   NO_COST=0.0  MINOR=0.25  GENERAL=0.5  SEVERE=0.8  NO_MATCH=1.0  IMPOSSIBLE=6.0
   ```

   (prior baseline: `0 / 0.65 / 0.75 / 1.0 / 1.5 / 10`). Monotonic ordering preserved.

4. **Sharper diagnostic weighting + one fewer feature**: `diagnostic_weight_epsilon` 1.0 → **0.1** (narrow-range concept features dominate more strongly), and **`eccentricity` dropped** (14 → 13 features). `delete_image_nodes=false`.

Because all four changed at once, treat this as a branch-level baseline. Attributing the +5.33pp to any single factor would require ablation runs that were not done here.

---

## 3. Per-class metrics vs prior baseline

| Class | Prior F1 | New F1 | ΔF1 | Prior Recall | New Recall | ΔRecall | Prior Prec | New Prec | ΔPrec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 94.00 | **95.73** | +1.74 | 88.67 | 91.93 | +3.26 | 100.00 | 99.87 | −0.13 |
| 1 | 92.38 | **95.08** | +2.70 | 94.65 | 96.52 | +1.88 | 90.22 | 93.69 | +3.46 |
| 2 | 71.09 | **84.30** | **+13.21** | 60.00 | 77.59 | **+17.59** | 87.21 | 92.28 | +5.06 |
| 3 | 88.50 | **93.73** | +5.23 | 85.43 | 95.76 | +10.33 | 91.79 | 91.78 | −0.01 |
| 4 | 88.81 | 87.89 | −0.93 | 82.65 | 84.00 | +1.35 | 95.97 | 92.15 | −3.82 |
| 5 | 88.39 | **92.95** | +4.56 | 83.67 | 91.96 | +8.29 | 93.67 | 93.97 | +0.30 |
| 6 | 87.83 | 88.50 | +0.67 | 92.98 | 92.44 | −0.54 | 83.21 | 84.88 | +1.67 |
| 7 | 78.78 | **88.10** | +9.31 | 97.33 | 95.15 | −2.18 | 66.17 | 82.01 | **+15.84** |
| 8 | 85.40 | **96.57** | **+11.17** | 74.66 | 94.49 | **+19.84** | 99.77 | 98.74 | −1.03 |
| 9 | 93.43 | 92.59 | −0.84 | 95.22 | 92.34 | −2.88 | 91.71 | 92.85 | +1.14 |

Eight of ten classes improved on F1. The only regressions are class 4 (−0.93, driven by a precision drop as it now catches some true 9s) and class 9 (−0.84, recall slips as some 9s leak to 4).

---

## 4. Confusion structure (792 wrong = 770 misclassified + 22 DLQ)

Top confusion pairs (expected → predicted):

| Pair | Count | Notes |
|---|---:|---|
| 2 → 7 | 111 | `7_1` (5 nodes, smallest) still the dominant attractor for stylistic 2s |
| 4 → 7 | 62 | `7_1` over-fire continues into class 4 |
| 2 → 6 | 57 | open 2s pulled to `6_1` |
| 4 → 1 | 52 | thin/straight 4s collapse to `1_1` |
| 9 → 4 | 46 | **new** confusion; drives class-4 precision drop and class-9 recall drop |
| 5 → 3 | 43 | curved 5s vs `3_1` |
| 0 → 6 | 42 | drives class-6 precision (84.9%) |
| 1 → 7 | 26 | |
| 7 → 2 | 26 | reverse direction — 7s landing on `2_x` |
| 2 → 3 | 25 | |

Per-class error totals: **class 2 (215 wrong)** and **class 4 (155 wrong)** are now the two dominant error contributors; everything else is ≤67.

---

## 5. Open issues (carried forward into this baseline)

- **Class 2 recall (top-1 issue): 77.6%.** Still the lowest recall and largest error source (215 wrong). Mass goes to `7_1` (111) and `6_1` (57). Materially better than the prior 60.0%, but `7_1`/`6_1` remain catch-all attractors for open/stylistic 2s.
- **Class 4 (top-2): recall 84.0%, precision dropped to 92.2%.** Loses 62 to `7_1`, 52 to `1_1`, 22 to `5_1`; meanwhile gains false positives from 9→4 (46). The 4/9 boundary is the new front.
- **Class 7 precision: 82.0%** — much improved (+15.8pp) but still the lowest-precision concept. `7_1` (complexity 9, smallest) absorbs 111 (2), 62 (4), 26 (1). Tracked as a per-concept-property tightening candidate, never a `concept_id` literal.
- **Coverage gaps / "not classified" (41):** concentrated in class 6 (16) and class 8 (14) — images matching no concept above threshold.
- **DLQ (22, ~0.25%):** skeletonization failures, spread thin across classes (1:7, 9:5, 4:3, 7:3, others ≤1).

---

## 6. Artifacts (this folder)

- [`findings.md`](findings.md) — this summary
- [`run_config.json`](run_config.json) — exact params used (manifest + concept node counts included)
- [`metrics.csv`](metrics.csv) — headline numbers
- [`per_class_metrics.csv`](per_class_metrics.csv) — per-class precision/recall/F1
- [`confusion_matrix.png`](confusion_matrix.png) — visual confusion pattern
- [`incorrect_results.csv`](incorrect_results.csv) — every misclassified image (slimmed to `status`, `image_id`, `image_path`, `profiling`, `expected`, `predicted`, `correct`, `error`)
- [`concept_graphs.json`](concept_graphs.json) — concept graphs active for this run
