# Run Analysis: run_20261026_005405 — matching-free projection model (not the manuscript's Section IV), final (benchmark: `complete`)

**Status (2026-11-03).** This is our own matching-free model, inspired by the hypotheses of the manuscript's Section IV; it is not an implementation of that section. The professor's review (29.10.2026) puts this line on hold: it uses f >= 0.8 instead of f = 1, the novelty map instead of hand subclasses, and a reaction on a partial match. Fixed-grid keys stand in for synapse addressing, and there is no connectivity or cycle structure. The main line is the ComAN final (run_20261024_113123).

**Date:** 2026-10-26 (official test run once on the frozen configuration)
**Branch:** `experiment/gap-aware-associative-emnist` (uncommitted working tree)

## TL;DR

- **Accuracy on `complete` (8 708 images): 90.74 %** — equal to Nikita's ComAN (90.89 %, McNemar p = 0.72), without
  graph matching and without hand-made subclasses; every image gets an answer.
- All 10 000 test images: **88.59 %** (his ComAN 82.24 %, +6.35 pp, p = 7e-51); `incomplete` (1 290): **74.11 %**
  (his 23.95 %).
- Same training data: his 76 originals. With the first 10 originals per digit instead (no selection): 88.75 % on
  `complete`, 86.36 % on all 10 000.

## Model

Projection of the stimulus onto a redundant hypergraph of the neuron (our model, inspired by the manuscript's Section IV hypotheses); local counters f(e) over
the neuron's originals, attractor = {f >= 0.8}; novelty map (Theorem 3) with consolidation — only neurons built from
>= 2 originals compete (15 neurons); his point 3 as an iterated pairwise competition on distinctive evidence (no
threshold); parametric layer (β 0.3) and centre-line shape anchors as synapses. Selection on dev:
lab_log.md sections N, P, R.

## Files

- `metrics.csv`, `per_class_metrics.csv`, `confusion_matrix.png` — `complete` (the benchmark)
- `metrics_all10000.csv`, `per_class_metrics_all10000.csv`, `confusion_matrix_all10000.png` — all 10 000 images
- `incorrect_results.csv` — every error on the 10 000 images
- `run_config.json` — configuration and the selection record
