# Run Analysis: run_20261024_113123 — ComAN final (benchmark: `complete`)

**Date:** 2026-10-24 (official test run once on the frozen configuration)
**Branch:** `experiment/gap-aware-associative-emnist`. How to reproduce: `REPRODUCE.md`

## TL;DR

- **Accuracy on `complete` (8 708 images): 92.90 %** — counting images without an answer as errors; **93.06 %** when the
  15 unanswered images are dropped from the denominator, as in Nikita's runs (his model: 91.13 % that way, 90.89 % ours).
- All 10 000 test images: **85.44 %** (his model 82.24 %); `incomplete` (1 290): 35.12 % (his 23.95 %).
- Paired vs his model on `complete`: +2.01 pp (95 % CI +1.36 … +2.66), McNemar p = 2e-9.
- No knob tuned on the test, no statistic over other classes (the complexity prior λ 0.10 and the 0.33 range gate were
  removed: −4.5 pp on dev; everything below recovered it and more).

## What changed vs his model (each step chosen on dev, lab_log.md sections M / N / Q)

| step | dev (1 996) |
|---|---|
| his model as is | 80.91 |
| observer knobs removed (λ 0, cliff out of band) | 76.40 |
| 28 node features (his point 1) | 78.01 |
| graded penalty outside the interval, 4 half-widths (his point 1) | 80.96 |
| filters 110 / 150 / 190, MAX per concept (his point 2) | 83.52 |
| attractor complexity in the reaction, λ 0.05 (manuscript Sec. II, item 15) | 83.82 |
| one detector at training and recognition | 84.72 |
| fine skeleton as a 4th filter, ε 1, stems rule, concepts from each filter | 84.97 |
| parametric layer (orientation descriptor, bands over the concept's own images, β 0.5) | **86.27** |

## Files

- `metrics.csv`, `per_class_metrics.csv`, `confusion_matrix.png` — `complete` (the benchmark)
- `metrics_all10000.csv`, `per_class_metrics_all10000.csv`, `confusion_matrix_all10000.png` — all 10 000 images
- `incorrect_results.csv` — every error on the 10 000 images (`subset` = complete / incomplete)
- `concept_graphs.json` — the 39 concepts (his 13 subclasses × detector thresholds 110 / 150 / 190)
- `run_config.json` — configuration, per-filter classification parameters, readout
