# Reproducing run_20261024_113123 (ComAN final)

This folder is **not the output of a single live pipeline run**. The final model is four live runs of the same
concepts through the pipeline, one per detector filter, combined offline:

```
reaction(image, concept) = max over the 4 filters of the GED similarity (minors only)
                         + 0.05 · log2(concept node count)
                         + 0.5 · parametric score
answer = class of the concept with the highest reaction
```

The four filters are binarisation thresholds 110, 150 and 190 (simplification ε 4.55) and a fine skeleton (threshold
150, ε 2.5), all with the "keep the stem" skeleton rule. The parametric score compares a 52-number orientation
descriptor of the image's centre line (2×2 and 3×3 grid cells × 4 direction bins) with intervals built from the
concept's own training images only.

The checked path below reproduces every file of this folder byte for byte from the four per-filter dumps.

## What you need

- The pipeline up as for your 91.13 % runs (Neo4j, Kafka, the nuclio functions deployed from this branch).
- `tests/mnist_all/<digit>/*.png` — the official MNIST test, the same layout and shared-storage path
  (`/opt/nuclio/shared_storage/mnist_all/...`) as in your runs.
- `tests/_isl_train/<subclass>/*.png` — your `datasets/train` (13 subclasses, 76 originals + augmentations); a copy
  or a symlink is enough. It is read only by the parametric layer (step 3).
- `datasets/mnist_all_manifest.csv` — the `complete` / `incomplete` split (you already have it).
- Neo4j credentials are hard-coded in `notes/scripts_isl/coman_concepts.py` (`driver()`):
  `bolt://localhost:7687`, `neo4j` / `111122223333`.

All commands run from the repo root with the project venv (`.venv/bin/python`).

## 1. Load the 39 concepts

```bash
python notes/scripts_isl/coman_concepts.py load experiments/run_20261024_113123/concept_graphs.json
python notes/scripts_isl/coman_concepts.py activate D110ps D150ps D190ps
python notes/scripts_isl/coman_concepts.py restart     # classification containers reload their concept cache
python notes/scripts_isl/coman_concepts.py status      # active: 39
```

`activate` marks every other concept in the database `concept_kind = 'coman_off'` (the classifier loads only concepts
with `concept_kind IS NULL`). Your own 13 concepts are switched off this way, not deleted. To switch them back on:

```cypher
MATCH (n) WHERE n.concept_kind = 'coman_off' AND n.coman_set IS NULL REMOVE n.concept_kind
```

## 2. Four live runs (one per filter)

```bash
for k in t110 t150 t190 fine150; do
  python notes/scripts_pipeline/pl_dump.py ged mnist_all 0 tests/_isl/coman/final2_test_$k.jsonl \
    "$(cat notes/scripts_isl/coman_cfg/n_comb_$k.json)"
done
```

Each config (`notes/scripts_isl/coman_cfg/n_comb_*.json`) differs from your run only in these per-message
parameters:

| parameter | yours | here | meaning |
|---|---|---|---|
| `features` | 13 | 28 (all the code computes) | node features in the GED cost |
| `diagnostic_weight_epsilon` | 0.1 | 1.0 | feature weight = 1 / (band width + ε) |
| `complexity_prior_lambda` | 0.10 (code default) | 0 | the complexity term is added offline (λ 0.05) |
| `range_gate_rel_width` | 0.33 (code default) | 1.0 | out-of-band cost ramps up for every feature; no comparison with other classes' bands |
| `range_soften_span` | 2.0 (code default) | 4.0 | the ramp reaches NO_MATCH 4 half-widths outside the band |
| `bridge_protect_stems` | — | true | skeleton rule: keep a short junction-junction edge when a straight stem passes through |
| `skeletonization_threshold` / `simplification_epsilon` | 110 / 4.55 | 110, 150, 190 / 4.55; fine: 150 / 2.5 | the four filters |

The GED cost ladder and the 5 s timeout are yours. New parameters are off by default in the code, so
your own configuration still gives your results.

## 3. Parametric descriptors and the offline combination

```bash
python notes/scripts_isl/coman_param_layer.py describe _isl_train     # -> tests/_isl/dense/_isl_train.jsonl
python notes/scripts_isl/coman_param_layer.py describe mnist_all      # -> tests/_isl/dense/mnist_all.jsonl (~5 min, 6 procs)
D=tests/_isl/coman
python notes/scripts_isl/coman_param_layer.py apply \
  --test-dumps $D/final2_test_t110.jsonl+$D/final2_test_t150.jsonl+$D/final2_test_t190.jsonl+$D/final2_test_fine150.jsonl \
  --test-dir mnist_all --out tests/_isl/Q_param_test.jsonl
```

Expected output:

```
all        n 10000  top-1  85.44  top-3  92.56
complete   n  8708  top-1  92.90  top-3  98.09
incomplete n  1290  top-1  35.12  top-3  55.27
```

## 4. The run folder

```bash
R=experiments/run_20261024_113123
python notes/scripts_isl/make_run_folder.py tests/_isl/Q_param_test.jsonl experiments/run_<new> \
  --config $R/run_config.json --findings $R/findings.md --concepts $R/concept_graphs.json
```

## Differences to expect

- **GED timeouts.** With the 5 s timeout about 0.3 % of answers change between identical runs (measured on dev:
  6 of 1 996), so a fresh live run lands within a few tenths of a point, not byte for byte. Steps 3–4 on the same
  dumps are exact.
- **Counting.** An image without an answer counts as an error here (15 such images in `complete`). Dropped from the
  denominator as in your runs, `complete` is 93.06 %.

## Graph examples for the paper

- A live result is one filter's answer. The final answer is the offline combination above, so the winning concept of
  an image may come from a different filter than the one you visualise.
- For a live example: keep the three sets active (step 1) and send one image with one filter's config, e.g.
  `n_comb_t110.json`. The image graph and the matched concept are in Neo4j as usual for your viz tooling.
- `incorrect_results.csv` lists every error with its subset. To compare with your model image by image:
  `tests/_isl/coman_mnist_all.jsonl` is your run re-scored, `tests/_isl/Q_param_test.jsonl` is this final.

## Rebuilding the concepts instead of loading them (optional)

The concepts were folded with your chain (pairwise max common minor, f = 1) from your 13 subclasses, by the
recognition detector at each threshold with the stems rule:

```bash
for t in 110 150 190; do
  python notes/scripts_isl/coman_concepts.py ingest --tag t${t}ps --thr $t --eps 4.55 --extra '{"bridge_protect_stems": true}'
  python notes/scripts_isl/coman_concepts.py export --tag t${t}ps
  python notes/scripts_isl/coman_concepts.py fold --tag t${t}ps --set D${t}ps --write
done
```

An example the concept cannot absorb (no common minor) is skipped and counted, instead of aborting the concept. For 36
of the 39 concepts that is 0 or 1 example. Three concepts were folded from a subset and collapsed to 3 nodes: 4_1 at
110 (46 of 77 examples, 4 of 7 originals), 4_1 at 190 (54 of 77, 4 of 7) and 8_1 at 190 (16 of 88, 2 of 8). This
is a known weak point: under a strict reading of f = 1 these three should not exist (without them dev drops from
86.27 to 85.37). The per-concept counts are in `tests/_isl/coman_sets/D*ps.json` (`stats`).

Folding your 13 subclasses again with your own detector (160 / 5) and the current fold code does not reproduce your
stored concepts (4_1: 3 nodes instead of 8; dev 74.85 vs 78.01). Your concepts were built by a different code
version or example order.

## Where each piece lives

| piece | file |
|---|---|
| per-message cost overrides, out-of-band ramp | `src/classification/nuclio_handler.py`, `src/classification/graph_similarity/cost_functions.py` |
| stems skeleton rule | `src/skeletonization/junction_merge.py`, `skeleton_gng_mapper.py` |
| orientation descriptor | `src/skeletonization/dense_features.py` |
| concept sets: ingest, fold, load, activate | `notes/scripts_isl/coman_concepts.py` |
| live runs | `notes/scripts_pipeline/pl_dump.py` |
| MAX over filters, complexity term, paired tests | `notes/scripts_isl/coman_rerank.py` |
| parametric layer, offline combination | `notes/scripts_isl/coman_param_layer.py` |
| run folder | `notes/scripts_isl/make_run_folder.py` |
