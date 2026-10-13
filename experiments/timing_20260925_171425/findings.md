# Training and inference time — ISL and the classical baselines

**Date:** 2026-09-25 · **Linear:** NIK-201
**Hardware:** Apple M1 Pro, 10 cores, 32 GB RAM, macOS 26.7, Docker Desktop
**Clock:** wall-clock (`time.perf_counter` / `time.time`)

**Data (same for both sides):**
- Training: `datasets/train/`, 869 images from 85 originals in 13 concept folders.
- Test: the 8,708 complete-only images of the frozen `f34b049` manifest.

**Sources:**
- Classical models: `experiments/classical_baselines_20260925T150211Z/`
- ISL training: `isl_training_times_run{1,2,3}.csv`
- ISL inference: `inference_run{1,2,3}/` (evaluation runs `run_20260925_144854`, `run_20260925_172932`, `run_20260925_182609`)

## Table

| Model | Training | Inference, 8,708 images | ms / image | Accuracy |
|---|---|---|---|---|
| ISL (13 concepts) | 528–966 s | 1,279–2,018 s | 147–232 | 90.70% (90.93% of 8,686 classified), run 3 |
| MLP, converged | 3.4 s ± 0.7 | 0.13 s | 0.015 | 76.77% |
| SVM (RBF) | 2.5 s | 34.5 s | 3.96 | 76.65% |
| CNN, converged | 73.5 s ± 8.4 | 7.1 s | 0.81 | 74.20% |
| k-NN, k = 1 | < 0.01 s | 0.64 s | 0.074 | 73.46% |
| Nearest centroid | 0.04 s | 0.26 s | 0.030 | 65.06% |
| MLP, 1 epoch | 0.44 s | 0.13 s | 0.015 | 59.92% |
| CNN, 1 epoch | 4.0 s | 6.6 s | 0.76 | 51.88% |

k = 3 and k = 5 time the same as k = 1, at 70.20% and 69.96% accuracy. MLP and CNN figures are means over 5 seeds (± sample SD). The converged models stopped early at 13–22 epochs (MLP) and 18–24 epochs (CNN).

## Conditions

| | Classical models | ISL |
|---|---|---|
| Execution | One Python process. Torch uses 10 threads; sklearn uses its defaults. | Nuclio + Kafka pipeline with 26 containers: connector, 4 skeletonization, 4 contour analysis, 16 classification, concept creator. |
| Timed span | `fit()` and `predict()` only | From the first HTTP submission to the last result, including skeletonization, contour analysis, Neo4j writes and Kafka hops |

The data matches, but the execution does not. Any comparison must say so.

ISL training time is the sum over the 13 concepts of two parts: the pipeline time up to the last contour-analysis message, and the `create_concept` call. ISL was retrained and evaluated three times, back to back, on the same data and code:

| Run | Training (pipeline + formation) | Inference | ms / image | Images / s | Accuracy, all images | Accuracy, classified |
|---|---|---|---|---|---|---|
| 1 | 528 s (88 + 440) | 1,279 s | 147 | 6.8 | 90.46% | 90.68% |
| 2 | 746 s (131 + 615) | 1,431 s | 164 | 6.1 | 89.70% | 89.93% |
| 3 | 966 s (152 + 814) | 2,018 s | 232 | 4.3 | 90.70% | 90.93% |

Run 1 used the current 8,704-image manifest; runs 2 and 3 used the frozen 8,708. 21–22 images went to the DLQ in each run.

Each run is slower than the last, in both training and inference. Every classification run leaves about 8,700 test-image graphs in Neo4j (`delete_image_nodes: false`), and the database held 514k nodes after run 3. This growth is the likely cause, but it was not isolated. Run 1 had the least accumulated data, so its figures are the cleanest.

## Accuracy

ISL accuracy over all test images ranges from 89.70% to 90.70% across the three retrains. Formation order is random on every retrain (NIK-318), so identical data yields different concepts. The table reports run 3, the best of the three. The spread across runs belongs next to it in any citation. Run 3 class recall ranges from 79.9% (class 2) to 96.4% (class 1).

Compared with the frozen `f34b049` train set, most classical models score lower on this corpus: SVM drops from 79.70% to 76.65%, nearest centroid from 75.17% to 65.06%, the converged CNN from 75.33% to 74.20%. The converged MLP (75.71% → 76.77%) and 1-NN (73.08% → 73.46%) gain slightly. In run 3, ISL leads the best classical model (converged MLP) by 13.9 pp.

`article_table.md` in the classical run folder still shows the fixed ISL reference of 91.13% (`run_20260630_235356`), not this run.

## Why not the frozen train set

ISL cannot form concept 4_1 from the `f34b049` train split with the current code. With all 77 files, formation fails with `No path found for endpoint`. After dropping the 11 `mnist_4_00004` files, it fails with `Reached maximum reduction iterations`. Both errors come from loop-count mismatches between samples. The classical script therefore now reads `datasets/train/`.

## Retrain hygiene

Neo4j held unconsumed training sessions for 7 concepts. The 4_1 session held 42 stale graphs, the size of the folder before the open-top "4" samples were removed on 13 Aug. Formation crashed on them. `retrain_all_concepts.py` now deletes each concept's session nodes before it submits new images.
