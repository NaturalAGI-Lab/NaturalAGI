| Model | Budget | Accuracy (%)[^2] | Precision (%) | Recall (%) | F1 (%) |
|---|---|---|---|---|---|
| isl | single_fit | 91.13 (8,685 classified) / 90.90 (all 8,707)[^1] | 92.22[^3] | 91.22[^3] | 91.54[^3] |
| mlp | converged | 76.77 ± 4.14 | 77.27 ± 3.18 | 75.70 ± 3.98 | 75.30 ± 4.37 |
| svm | single_fit | 76.65 | 80.57 | 74.70 | 74.66 |
| cnn | converged | 74.20 ± 5.03 | 75.28 ± 3.90 | 72.84 ± 5.47 | 72.09 ± 5.99 |
| knn_k1 | single_fit | 73.46 | 73.77 | 72.04 | 72.19 |
| knn_k3 | single_fit | 70.20 | 72.14 | 68.14 | 68.16 |
| knn_k5 | single_fit | 69.96 | 72.87 | 67.59 | 67.76 |
| nearest_centroid | single_fit | 65.06 | 67.23 | 64.16 | 62.65 |
| mlp | 1epoch | 59.92 ± 3.50 | 65.26 ± 6.29 | 57.82 ± 3.81 | 54.70 ± 5.06 |
| cnn | 1epoch | 51.88 ± 3.47 | 59.12 ± 10.74 | 50.00 ± 3.21 | 45.55 ± 3.89 |

[^1]: 8,707 images submitted, 22 failed in the pipeline (skeletonization failures, recorded as DLQ) and were never scored; 8,685 were classified at 91.13% (7,915 correct), or 90.90% counting the 22 failures as wrong over all 8,707. Source: `experiments/run_20260630_235356/`.
[^2]: The four classical/MLP/CNN models above are scored on the archive's reproducible 8,708 complete-only test images — one more than ISL's 8,707 (`experiments/run_20260630_235356` read a manifest edited after commit f34b049 and its config records 8,707). One image out of 8,708 moves accuracy by 0.011pp.
[^3]: Every precision, recall and F1 in this table is a macro average over the ten digits. ISL's are recomputed from `run_20260630_235356/per_class_metrics.csv` over the 8,685 images it classified; that run's own `metrics.csv` reports weighted averages (91.92 / 91.13 / 91.34), which are not comparable with the rows above.
