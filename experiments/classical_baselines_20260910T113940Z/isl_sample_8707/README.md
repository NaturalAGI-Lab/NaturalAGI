# Baselines scored on ISL's 8,707 test images

The parent run scored the baselines on the archive's 8,708 complete test images. ISL's `run_20260630_235356` saw 8,707. The missing image is `mnist_all/4/mnist_test_4_00059.png`: commit `f292d11` relabelled it `complete` → `incomplete`, and its manifest lists 8,707 complete images.

`rescore_8707.py` re-runs the parent's script (version `eea6e6b`, 805 training samples, seeds 0–4) and scores every model on both sets. On 8,708 every accuracy and per-class recall equals the parent's `metrics.csv` and `per_class_metrics.csv`. Every model predicts class 4 for the excluded image.

| Model | Budget | Accuracy on 8,707 (%) | Per-class recall (%) |
|---|---|---|---|
| ISL | single pass | 90.90 (7,915 / 8,707; 22 pipeline failures counted wrong) | 77.51–95.93 |
| SVM, RBF | single fit | 79.69 | 48.09–97.34 |
| MLP | converged | 75.70 ± 3.22 | 53.16–97.25 |
| CNN | converged | 75.32 ± 1.66 | 45.26–96.85 |
| Nearest centroid | single fit | 75.17 | 60.55–89.11 |
| k-NN, k = 1 | single fit | 73.08 | 48.97–93.94 |
| k-NN, k = 5 | single fit | 71.70 | 47.24–94.69 |
| k-NN, k = 3 | single fit | 71.17 | 45.70–92.59 |
| MLP | 1 epoch | 67.13 ± 5.44 | 29.91–97.43 |
| CNN | 1 epoch | 59.00 ± 6.47 | 18.27–89.85 |

ISL's recall counts each class's pipeline failures as wrong: correct images from `run_20260630_235356/per_class_metrics.csv` over the submitted count per class. For MLP and CNN, recall is the per-class mean over the five seeds.

`rescore_8707.json` holds every metric on both sets. `predictions.npz` holds the test paths, true labels and each model's predictions (one row per seed).

```bash
git show eea6e6b:src/training/classical_baselines.py > /tmp/classical_baselines_eea6e6b.py
.venv/bin/python -I experiments/classical_baselines_20260910T113940Z/isl_sample_8707/rescore_8707.py /tmp/classical_baselines_eea6e6b.py . /tmp/rescore_out
```
