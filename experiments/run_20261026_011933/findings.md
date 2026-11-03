# Run Analysis: run_20261026_011933 — matching-free projection model (not the manuscript's Section IV), final, EMNIST-letters

**Status (2026-11-03).** This is our own matching-free model, inspired by the hypotheses of the manuscript's Section IV; it is not an implementation of that section. The professor's review (29.10.2026) puts this line on hold: it uses f >= 0.8 instead of f = 1, the novelty map instead of hand subclasses, and a reaction on a partial match. Fixed-grid keys stand in for synapse addressing, and there is no connectivity or cycle structure. The main line is the ComAN final (run_20261024_113123).

**Date:** 2026-10-26 (official test run once on the frozen configuration)
**Branch:** `experiment/gap-aware-associative-emnist` (uncommitted working tree)

## TL;DR

- **Accuracy on the official EMNIST-letters test (20 800 images, 26 classes): 71.33 %**, top-3 87.52 %; macro
  Precision 71.94 %, Recall 71.33 %, F1 70.80 %. Every image gets an answer.
- Trained on **10 originals per letter** (the first 10 of the official train, no selection) + rotation / shift
  augmentations; params = 0 (no trained weights; the map stores 256 587 attractor elements).
- Best letters: S 92.4 %, Z 89.0 %, X 86.9 %, P 85.6 %, C 85.3 %, F 85.1 %. Worst: I 31.9 %, G 35.9 %, R 48.0 %,
  H 51.4 %, L 51.8 %.
- The largest error is **I → L (400 of 800 I, 6.7 % of all errors)**, then G → Q (246), L → I (178): in EMNIST the
  classes merge upper and lower case, so lowercase l and uppercase I are the same stroke. I + L counted together: 74.11 %.
- vs the previous final (P, 69.57 %): +1.76 pp [+1.39, +2.13], McNemar p = 2.9e-20.

## Model

Same configuration as the MNIST final (run_20261026_005405): projection onto a redundant hypergraph of the neuron
(our model, inspired by the manuscript's Section IV hypotheses), local counters f(e) over the neuron's originals, attractor = {f >= 0.8}; novelty map
(ρ 0.6) with consolidation — only neurons built from >= 2 originals compete (55 of 102 neurons, 81.9 % of the
originals); his point 3 as an iterated pairwise competition on distinctive evidence; parametric layer
(β 0.3), sleep consolidation θ 0.7, centre-line shape anchors as synapses. Selection on dev: lab_log.md section R.

## Files

- `metrics.csv` — summary (macro Precision / Recall / F1, top-3)
- `per_class_metrics.csv` — per letter: precision, recall (= accuracy of the letter), F1, support, top-3 accuracy
- `confusion_matrix.csv` / `confusion_matrix.png` — rows expected, columns predicted (800 images per row)
- `top_confusions.csv` — the 40 most frequent expected → predicted errors
- `incorrect_results.csv` — every error (image path, expected, predicted, top-3)
- `run_config.json` — configuration and the selection record
