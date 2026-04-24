# Findings — run_20260424_132908 (exp_058 Family E full)

**Date**: 2026-04-24
**Branch**: `feat/graph-features-and-cleanup`
**Status**: NEW BASELINE (promoted from exp_052 Method 3)

## Summary

**79.24% accuracy** on 12,000 MNIST test images (+4.21pp vs the prior
exp_052 Method 3 baseline of 75.03%).

| Metric | Baseline (exp_052) | This run (exp_058) | Δ |
|---|---|---|---|
| Accuracy | 75.03% | **79.24%** | **+4.21pp** |
| Precision | 79.25% | 84.94% | +5.69pp |
| Recall | 75.03% | 79.24% | +4.21pp |
| F1 | 75.86% | 80.25% | +4.39pp |
| DLQ | 54 | 56 | +2 |

## Change vs baseline

Single-line change in `src/classification/graph_similarity/cost_functions.py`,
function `_calculate_properties_similarity_cost`, around line 169:

```python
# Before (capped):
total_cost += min(property_cost, normalized_w)

# After (uncapped — Family E):
total_cost += property_cost
```

The cap was collapsing the `NO_MATCH = 1.0` signal (feature outside the concept's
range) into `~0.07` (the feature's weight allocation with 14 features). That's a
14× compression of the mismatch signal at the per-feature level. Removing the cap
widens the raw GED cost distribution by 3–4×, which Boria's size-normalization
then turns into a correspondingly wider similarity distribution downstream.

Method 3's log-prior (+0.02·log₂(complexity) additive in the orchestrator) is
kept unchanged — it's load-bearing. Families A-D that modified only the scoring
transform (comparator formula, softmax, argmin, z-score) all regressed by
2-13pp in their own experiments.

## Per-class F1 breakdown

| Class | Baseline F1 | This run F1 | Δ |
|---|---|---|---|
| 0 | 87.69 | 87.47 | −0.22 |
| 1 | 89.54 | 89.37 | −0.17 |
| 2 | 60.38 | 65.78 | **+5.40** |
| 3 | 72.60 | 85.24 | **+12.64** |
| 4 | 79.62 | 83.22 | +3.60 |
| 5 | 65.18 | 86.48 | **+21.30** |
| 6 | 71.25 | 76.40 | +5.15 |
| 7 | 76.61 | 68.65 | **−7.96** ← regression |
| 8 | 70.64 | 71.61 | +0.97 |
| 9 | 85.02 | 88.40 | +3.38 |

**Big wins**: classes 5 (+21.3), 3 (+12.6), 2 (+5.4), 6 (+5.1). The compression
problem we investigated at the start (5→3 misclassifications via Boria's narrow
similarity band) is resolved structurally.

**Regression**: class 7 (−8.0) — recall climbed to 97.4% but precision dropped
from 67% to 53%. Concept 7_1 (complexity 9) over-fires because small concepts
have fewer features to fail on under the uncapped regime. This is the same
"7_1 attractor" pathology documented in `researches/7_1_attractor_fix.md`;
previously contained by Method 3's log-prior but re-emerging under the new
cost distribution.

## Open follow-up

Class 7 precision collapse. Three candidate fixes:

1. **Concept-level**: raise `node_ins_cost` specifically for concept 7_1, or
   retrain 7_1 with tighter property ranges (concept-creator level fix).
2. **Library-level**: add a second, more specific 7_x concept so class 7 has
   more coverage options.
3. **Orchestrator-level**: tune `COMPLEXITY_PRIOR_LAMBDA` upward (currently
   0.02) to push more weight back onto concept complexity — may help the
   prior outweigh 7_1's size advantage under uncapped costs.

## Related research

- `researches/ged_compression_five_families_findings.md` — this run's full
  5-family experiment breakdown (A/B/C/D/E quick tests then E at full scale)
- `researches/ged_similarity_compression_research.md` — original compression
  problem taxonomy, literature review, proposed experiment queue
- `src/training/training_results/run_20260423_203757/hypotheses/viz/` — visual
  analyses of the compression symptom (similarity_anatomy.html,
  classification_logic.html)
- `researches/ged_size_bias_mathematical_approaches.md` — 27-paper literature
  review covering the size-bias problem (which this experiment separated from
  the compression problem)
- `researches/ged_size_bias_four_methods_findings.md` — the earlier 4-method
  benchmark (exp_050–exp_053) that established Method 3 as the previous
  baseline — now superseded
