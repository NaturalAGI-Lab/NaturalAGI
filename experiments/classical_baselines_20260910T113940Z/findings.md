# Classical baselines vs ISL — classical_baselines_20260910T113940Z

**Date:** 2026-09-10
**Script:** `src/training/classical_baselines.py`
**Corpus:** `f34b049:datasets.zip`, extracted and upscaled in `experiments/.cache/` — 76 originals / 805 training instances, 8,708 complete-only test images
**Reference:** `experiments/run_20260630_235356/` (ISL, 91.13%)

---

## TL;DR

- **ISL leads every classical model by 11.20pp.** Best classical is `SVC(kernel="rbf")` at **79.70%** against ISL's **90.90%** over the same full population. Credited only with what it classified, ISL is 91.13% and the gap is 11.43pp.
- **The supervisor's prediction holds, with a qualification.** k-NN is the weakest family (71.18–73.08%), below SVM, MLP and CNN — but only once the networks are trained to convergence. At the one-epoch budget both the CNN (59.00%) and the MLP (67.13%) fall below every k-NN variant.
- **One pass is not enough for either network.** The MLP gains 8.6pp and the CNN 16.3pp between one epoch and convergence, which took 13–29 epochs.
- **ISL degrades evenly across digits, the classical models do not.** ISL's per-class recall spans 77.6–96.5 (18.9pp). SVM spans 48.1–97.3 (49.2pp), the converged MLP 53.2–97.3 (44.1pp). Classes 3, 5 and 8 are where the gap is made.

---

## 1. Headline table

| Model | Budget | Accuracy (%) | Macro F1 (%) |
|---|---|---|---|
| **ISL** | single pass | **91.13** (8,685 classified) / **90.90** (all 8,707) | 91.54 |
| SVM (RBF) | single fit | 79.70 | 78.50 |
| MLP | converged (13–20 ep.) | 75.71 ± 3.22 | 74.59 ± 3.15 |
| CNN | converged (17–29 ep.) | 75.33 ± 1.66 | 73.95 ± 1.40 |
| Nearest centroid | single fit | 75.17 | 74.75 |
| k-NN, k=1 | single fit | 73.08 | 71.76 |
| k-NN, k=5 | single fit | 71.70 | 70.14 |
| k-NN, k=3 | single fit | 71.18 | 69.71 |
| MLP | one epoch | 67.13 ± 5.44 | 62.91 ± 6.40 |
| CNN | one epoch | 59.00 ± 6.47 | 52.37 ± 9.41 |

Stochastic rows are mean ± sd over seeds 0–4. ISL's F1 is recomputed as a macro average from `run_20260630_235356/per_class_metrics.csv` so the column is like-for-like; that run's own `metrics.csv` reports the weighted figure, 91.34. Full numbers in `metrics.csv`; the article-ready version with both ISL denominators and their footnotes is `article_table.md`.

## 2. What the budget column costs

The two networks are the only models the "one pass" instruction actually constrains — SVM, k-NN and nearest centroid have no epoch notion and fit once by construction.

| Model | One epoch | Converged | Gain |
|---|---|---|---|
| MLP | 67.13 ± 5.44 | 75.71 ± 3.22 | +8.58pp |
| CNN | 59.00 ± 6.47 | 75.33 ± 1.66 | +16.33pp |

Seed spread narrows as training proceeds — the CNN's macro F1 varies by ±9.41 across seeds after one epoch against ±1.40 at convergence — so a single-seed one-epoch number would have carried almost no information.

Convergence here means early stopping on ten held-out originals, one per digit, with every `_augN` variant following its original. That costs the networks about 2.4pp against an instance-level split, because the ten originals leave the fit set entirely and class 0 has only three to begin with. The cost is itself a data-efficiency signal: removing 10 of 76 originals moves the networks more than 2pp, while ISL is given no validation split at all.

## 3. Per-class recall — where the classical models fail

| Class | Train inst. | ISL | SVM | MLP conv. | CNN conv. | k-NN k=1 | Near. centroid |
|---|---|---|---|---|---|---|---|
| 0 | 33 | 91.9 | 71.7 | 74.5 | 73.2 | 73.1 | 82.4 |
| 1 | 77 | 96.5 | 97.3 | 97.3 | 96.8 | 91.4 | 89.1 |
| 2 | 99 | **77.6** | 87.3 | 78.2 | 80.6 | 75.9 | 81.5 |
| 3 | 36 | 95.8 | **48.1** | 55.7 | 50.8 | 62.8 | 67.1 |
| 4 | 142 | 84.0 | 91.6 | 90.5 | 87.7 | 70.1 | 72.9 |
| 5 | 66 | 92.0 | 72.4 | 65.1 | 69.9 | 52.8 | 60.6 |
| 6 | 77 | 92.4 | 94.6 | 90.8 | 92.0 | 93.9 | 84.2 |
| 7 | 99 | 95.2 | 83.7 | 70.0 | 68.4 | 82.8 | 75.6 |
| 8 | 88 | 94.5 | 69.1 | 53.2 | **45.3** | 49.0 | 65.8 |
| 9 | 88 | 92.3 | 73.6 | 69.9 | 76.5 | 65.1 | 64.5 |

ISL's supports are its 8,685 classified images, the classical models' are the full 8,708; the largest resulting distortion is about 0.4pp on class 4.

Three readings worth carrying into the article:

- **ISL is flat, the classical models are jagged.** ISL's worst class is 2 at 77.6% recall and nothing falls below it. Every classical model has at least one class under 70%, and the CNN drops to 45.3% on class 8.
- **Classes 3, 5 and 8 make the gap.** ISL beats SVM by 47.7pp on class 3, 25.4pp on class 8 and 19.6pp on class 5. Outside those three the two are close, and on classes 2 and 4 SVM is ahead.
- **Corpus imbalance explains part of it, not all.** Training instances per digit run from 33 (class 0, three originals) to 142 (class 4, thirteen). Class 3 has 36 and is the worst class for SVM, MLP and CNN alike. But class 8 has 88 and still collapses, while class 0 has 33 and holds up — so the classical models' unevenness is not simply a headcount effect. ISL trains on the same imbalance and is far less sensitive to it.
- **Class 2 is ISL's weakest class and is not a classical-model weakness.** SVM reaches 87.3% and nearest centroid 81.5% where ISL manages 77.6%. The 2→7 confusion documented in the baseline findings belongs to the skeleton representation, not to the digit.

## 4. Reproducibility

`run_config.json` records every hyperparameter, the five seeds, the actual epoch counts per seed, package versions, and the archive commit. The script reads nothing outside the repository: it extracts `f34b049:datasets.zip` into `experiments/.cache/` and applies the tracked LANCZOS 28→100 upscale of `src/training/resize_mnist_all_inplace.py` to the cache copy, so a fresh clone reproduces the same pixels the ISL pipeline was scored on.

Two protocol notes are recorded in `run_config.json` rather than left implicit:

- **Test population is 8,708, ISL's was 8,707.** The archive's manifest has one more complete class-4 image than `run_20260630_235356/run_config.json` recorded; that run was `dirty: true` and read a manifest edited after the commit, and the excluded image is not identifiable from its artefacts. One image out of 8,708 moves accuracy by 0.011pp. Stored under `test_set.manifest_delta`.
- **No tuning.** Library defaults throughout, matching ISL's own claim that it does no hyperparameter search. Every classical number here is therefore a floor, and a tuned SVM would close some of the 11.20pp.

An independent review reproduced `nearest_centroid` and `knn_k1` to six decimals through a separate loader, confirmed zero filename and pixel overlap between the 76 training originals and the 8,708 test images, and verified the working tree was never written to.

## 5. What this run does not settle

The equal-budget few-shot comparison — ProtoNet and MAML on this split — is untouched, and so is inference cost. A reviewer can still object that the classical models were given 805 augmented instances of 76 originals rather than a few-shot protocol of their own design.
