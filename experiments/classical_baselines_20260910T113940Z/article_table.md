| Model | Budget | Accuracy (%)[^2] | Precision (%) | Recall (%) | F1 (%) |
|---|---|---|---|---|---|
| isl | single_fit | 91.13 (8,685 classified) / 90.90 (all 8,707)[^1] | 92.22[^3] | 91.22[^3] | 91.54[^3] |
| svm | single_fit | 79.70 | 80.58 | 78.95 | 78.50 |
| mlp | converged | 75.71 ± 3.22 | 77.52 ± 2.07 | 74.51 ± 3.37 | 74.59 ± 3.15 |
| cnn | converged | 75.33 ± 1.66 | 77.10 ± 1.08 | 74.12 ± 1.53 | 73.95 ± 1.40 |
| nearest_centroid | single_fit | 75.17 | 75.84 | 74.37 | 74.75 |
| knn_k1 | single_fit | 73.08 | 73.14 | 71.70 | 71.76 |
| knn_k5 | single_fit | 71.70 | 72.02 | 69.85 | 70.14 |
| knn_k3 | single_fit | 71.18 | 71.24 | 69.56 | 69.71 |
| mlp | 1epoch | 67.13 ± 5.44 | 72.16 ± 3.83 | 64.78 ± 5.32 | 62.91 ± 6.40 |
| cnn | 1epoch | 59.00 ± 6.47 | 64.89 ± 5.73 | 57.14 ± 6.86 | 52.37 ± 9.41 |

[^1]: 8,707 images submitted, 22 failed in the pipeline (skeletonization failures, recorded as DLQ) and were never scored; 8,685 were classified at 91.13% (7,915 correct), or 90.90% counting the 22 failures as wrong over all 8,707. Source: `experiments/run_20260630_235356/`.
[^2]: The four classical/MLP/CNN models above are scored on the archive's reproducible 8,708 complete-only test images — one more than ISL's 8,707 (`experiments/run_20260630_235356` read a manifest edited after commit f34b049 and its config records 8,707). One image out of 8,708 moves accuracy by 0.011pp.
[^3]: Every precision, recall and F1 in this table is a macro average over the ten digits. ISL's are recomputed from `run_20260630_235356/per_class_metrics.csv` over the 8,685 images it classified; that run's own `metrics.csv` reports weighted averages (91.92 / 91.13 / 91.34), which are not comparable with the rows above.
