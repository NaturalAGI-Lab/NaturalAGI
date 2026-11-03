# Lab log — transferring the few-shot findings into ISL (2026-10-12 …)

Plan: `~/.claude/plans/keen-exploring-snowflake.md` (approved 2026-10-12). Gates for every step, in priority order:
G2 no observer (local rules, positives only, no pool-wide analysis, no negatives, no test-tuned knobs) > G1 maps to a
section / equation of the manuscript > G3 not contradicting neurobiological experiments (or marked as a hypothesis) >
G4 non-inferior on dev. Official tests are run once per final configuration.

## P0 — protocol (2026-10-12)
- Knowledge snapshot before any change: `tests/_isl/knowledge_before_isl.json` (9 047 nodes, 143 concepts:
  91 EMNIST fold concepts + 52 leaf explainers). Restore: `notes/scripts_pipeline/concept_snapshot.py restore`.
- MNIST dev = official TRAIN, per-digit index 60..259, PIL LANCZOS 100×100 like the test PNGs (`tests/mnist_dev`,
  `notes/scripts_isl/make_dev.py`, manifest `tests/_isl/mnist_dev_manifest.json`): 1 996 images; 4 excluded because
  baseline originals sit at those indices. Byte check against the official test: no overlap.
- The baseline's 76 originals (`datasets/train`) are official-train images: file `mnist_<d>_<k>` = k-th train image of
  digit d (nearest-image correlation ≥ 0.977); they were resized with BILINEAR, the test with LANCZOS. Four of them
  have k < 60, i.e. are also candidates in `tests/mnist_cand60`. Regenerated with LANCZOS: `tests/mnist_base76`
  (subclass of each in `tests/_isl/base76_subclasses.json`).
- Dev is NOT curated for complete contours — compare deltas on dev, not with 91.13 % (curated test subset).

## B0 — primitive cache
`notes/scripts_isl/isl_cache.py`: production skeletonisation at a FIXED threshold 110 (no search for a connected graph)
+ contour-analysis junction merge; augmentation = rotation ±10° and shift ±3 px only (§12). Cached: cand60 (600
originals × 11), base76 (76 × 11), dev (1 996). No detector failures.

## B1–B5 — matching-free projection model, pre-registered grid (2026-10-12)
`notes/scripts_isl/isl_sim.py grid --train cand60:10 --orders 5` (10 originals per digit = official-train candidates
k 0..9, 10 rot/shift augmentations each; dev 1 996; mean ± sd over 5 presentation orders). Full table:
`results_B.csv`. Unit tests: `unit_tests/test_isl_sim.py`.

| configuration | top-1 | top-3 | neurons | note |
|---|---|---|---|---|
| τ 1.0, ρ 0.5, readout a (coverage) | 67.4 ± 2.2 | 89.5 | 45 | small attractors win elsewhere |
| τ 1.0, ρ 0.5, readout c (÷ total input) | 78.0 ± 0.6 | 93.8 | 61 | |
| τ 1.0, ρ 0.6, readout c | 81.3 ± 0.3 | 94.1 | 77 | reference for the controls |
| τ 1.0, ρ 0.7, readout c | **82.6 ± 0.1** | 94.0 | 93 | nearly one neuron per original |
| τ 0.8, ρ 0.7, readout a | 79.9 ± 0.7 | 95.0 | 85 | τ < 1 helps the un-normalised readout |
| control: shuffled labels | 9.1 | 27.2 | 95 | chance — no leak |
| control: τ = 0 (no reduction) | 82.3 ± 0.2 | 94.1 | 74 | as good as the best |
| control: coarsest level only | 34.0 ± 3.1 | 71.3 | 16 | the parametric hierarchy carries the information |
| control: no relations (no hyperedges) | 72.2 ± 0.4 | 94.4 | 67 | −9.1 vs reference: the structural layer matters |
| control: no augmentation | 81.5 ± 0.2 | 94.5 | 83 | ±0 |
| control: bbox frame instead of centre of mass | 78.7 ± 0.2 | 94.0 | 78 | −2.6 |

Reading (honest):
- Divisive normalisation by the stimulus' total drive (feedforward inhibition) is what removes the "small attractor
  fits everything" failure (+10 pp over plain coverage at ρ 0.5) — the professor's own 7_1 problem.
- Hyperedges (point–stroke–point relations) add 9 pp: the structural part of ISL is supported in the projection model.
- Structural reduction ACROSS different originals does not help here: accuracy rises as fewer originals are merged
  (ρ 0.5 → 0.7: 61 → 93 neurons, 78.0 → 82.6) and τ = 0 is as good as τ = 1. With 10 uncurated originals per digit the
  map keeps almost one detector per original. Reduction within an original's augmentation family (majority vote) also
  changes nothing measurable.
- `univ` (largest share of foreign wins of a single neuron with ≥ 20 wins) stays ~0.95 with readout c: one universal
  neuron remains — to inspect.

## A0 — the baseline (ComAN) on dev, noise floor, observer audit (2026-10-12)
- Active structural set switched to Nikita's 13 MNIST concepts restored from `experiments/run_20260630_235356/
  concept_graphs.json` (`notes/scripts_isl/a0_concepts.py`; the 91 EMNIST concepts tagged `concept_kind='isl_off'`,
  reversible with `on-emnist` / `remove-mnist`). Classification redeployed with the handler fix (per-message cost overrides
  now identical on the traced and untraced paths; new overrides `range_gate_rel_width`, `range_soften_span`).
- Config exactly as his run (`tests/_isl/nikita_cfg.json`: GED, timeout 5, no preprocess fallback, 13 features, his cost
  ladder, ε 0.1). Sanity on 1 000 images of the `complete` test subset: **91.60 %** (his 91.13 % on all of it).
- Dev (1 996, uncurated official-train images): **81.11 % / 80.91 %** top-1 in two identical runs, top-3 85.42 %;
  11 skeleton failures. Noise floor: 6 / 1 996 answers (0.30 %) differ between identical runs.
- A3a, cross-class statistics removed from the range cost (`range_gate_rel_width` 1.0): **79.01 %**, Δ −2.10 pp
  (95 % CI −3.11 … −1.10, McNemar p = 0.0001) — fails non-inferiority. The gate that consults all other classes' bands
  (and was validated on the full MNIST test) is buying ~2 pp.
- A8, observer-free readouts re-ranked offline from the same dump: λ = 0 (no test-tuned complexity prior) 77.66
  (−3.46); coverage^0.5 75.25 (−5.86); coverage^1 61.87; self-calibration on each concept's OWN training positives
  73.20 (−7.92). None replaces the test-tuned λ = 0.10. Together with A3a: ≈ 5 pp of the baseline's dev accuracy rests on
  knobs that need an observer (test-tuned constants, cross-class statistics).

## A0 — order invariance of the fold (Theorem 2, eq. 39–40)
`notes/scripts_isl/a0_order.py`: the subclasses' training images (originals + augmentations as in his run) ingested
with D = 110 / 4.55 (the classification detector), folded offline with the concept creator's own code in 5 random orders.

| subclass | folded | identical structure | note |
|---|---|---|---|
| 2_1 (66 images) | 5 / 5 | all identical | |
| 7_1 (99) | 5 / 5 | 5 nodes, 4 edges each (as his 7_1) | one order labels a vector `Vector` instead of `HorizontalVector` |
| 8_1 (88) | 4 / 5 | the 4 identical | one order fails: "Reached maximum reduction iterations" |
| 4_1 (77) | 0 / 5 | — | every order fails: "No path found for endpoint" |

The structure of the attractor is (almost) order-invariant, but whether the fold succeeds depends on the order, and with
the classification detector one subclass cannot be folded at all — consistent with his concepts having been built with
a different detector (deployed defaults 160 / 5 vs 110 / 4.55 at classification).

## B — who are the "universal" neurons? + post-hoc consolidation (2026-10-12)
`isl_sim.py inspect` (τ 1.0, ρ 0.6, readout c, order 0): the neurons that win most often on other classes are
single-original detectors of an atypical original, not small attractors — e.g. a "9" neuron with |A| 784 wins 26 of its
27 dev images on "5"s; a "7" neuron wins 23 "2"s. With one original there is no reduction to strip what is peculiar to
that example. Recall per digit: 0 94, 1 81, 2 79, 3 70, 4 91, 5 66, 6 84, 7 84, 8 76, 9 85; top confusions 3→5 39,
2→7 28, 5→9 25.
Post-hoc variant (added AFTER the grid, theory-motivated: an attractor needs a reduction over ≥ 2 examples; single-exposure
traces stay unconsolidated — synaptic tagging & capture): only neurons with ≥ 2 originals compete
(`results_B_posthoc.csv`). **Fails**: best 72.42 ± 1.23 (τ 0.8, ρ 0.5, readout c) vs 78.39 without it; at ρ 0.7 it
collapses to 36.7 (almost every neuron is a singleton). With 10 uncurated originals per digit most styles are seen once,
so the singletons carry the coverage. Next: 60 originals per digit (is the training set then a "sufficient covering set",
§11?) and his 76 originals with his hand subclasses.

## B — his 76 originals (hand subclasses vs novelty) and 60 originals per digit (2026-10-12)
`isl_sim.py base76 --train base76 --orders 3`, `isl_sim.py many --train cand60:60 --orders 3` (`results_B.csv`).

| training | map | τ | top-1 | top-3 | neurons |
|---|---|---|---|---|---|
| his 76 originals | his 13 hand subclasses | 1.0 | 55.91 (c) / 61.32 (a) | 82.1 / 89.3 | 13 (|A| ~97) |
| his 76 originals | his 13 hand subclasses | 0.8 | 72.85 (c) | 91.7 | 13 |
| his 76 originals | his 13 hand subclasses | 0 (union) | **84.32 (c)** | 94.8 | 13 (|A| ~1 217) |
| his 76 originals | novelty ρ 0.6 | 1.0 | 83.57 ± 0.07 | 94.3 | 60 |
| 60 candidates / digit | novelty ρ 0.7 | 1.0 | 90.70 ± 0.09 | 97.7 | 444 |
| 60 candidates / digit | novelty ρ 0.7 | 0.8 | 90.71 ± 0.05 | 97.7 | 442 |
| 60 candidates / digit | novelty ρ 0.7 | 0 | **90.93 ± 0.08** | 97.7 | 435 |
| 60 candidates / digit | novelty ρ 0.5 | 1.0 / 0.8 / 0 | 85.12 / 86.99 / 89.03 | 97.0–98.0 | 193–228 |
| 60 candidates / digit | ρ 0.5, τ 0.8, consolidation ≥ 2 | 0.8 | 87.81 ± 0.49 (+0.8) | 96.3 | 214 |

Paired on dev, same 76 originals and same 13 hand subclasses: projection model (τ 0, readout c) 84.32 vs ComAN 81.11,
Δ **+3.21 pp** (95 % CI +1.33 … +5.08, McNemar p = 0.001); ComAN-only correct 151, B-only correct 215, both wrong 162;
the two models give the same answer on 1 539 / 1 996 images.
Reading: strict structural reduction (f = 1 over a subclass's originals and augmentations) leaves only coarse synapses
(|A| ~97) and costs ~25 pp; every reduction level tested is at best neutral (τ 0 ≥ τ 0.8 ≥ τ 1.0 in every setting).
With 60 originals per digit the universal neurons disappear (univ 0.95 → 0.06 at ρ 0.7) and consolidation (≥ 2 originals)
starts to help slightly. The novelty map reaches the hand-made map's accuracy without any hand-made subclass.

## I — improvements, pre-registered 2026-10-20 (before running)
Each switch alone on the reference (detector t110, exact fields), then all together; τ ∈ {1.0, 0.8, 0}, ρ ∈ {0.6, 0.7},
readout c, 3 presentation orders; also his 76 originals with his 13 hand subclasses (τ ∈ {1.0, 0.8, 0}).
1. `rf=overlap` — overlapping receptive fields: a primitive activates its own position cell / direction or orientation
   sector / length class fully and the nearer neighbouring one at half strength (receptive fields overlap in cortex);
   presence for f(e) counts either. Primary question: does reduction (τ = 1) stop destroying the fine synapses?
2. `rules` — detector with the production skeleton rules (thick strokes binarised at 170; short junction-junction edge
   kept when a straight stem passes through).
3. `filters3` — three binarisation filters 110 / 150 / 190 (with the rules) as parallel channels; afferent = MAX over
   channels (his point 2; complex-cell MAX, Lampl et al. 2004).
4. `curves` — total turning along each stroke as a relation parameter (<60 | ≥60; <30 | 30–90 | 90–180 | ≥180°).
5. `gain=confirm` — a detector's strength grows with the originals that confirmed it, g = n / (n + 1) (LTP grows with
   repetition); single-example detectors compete at half strength.
Then EMNIST (dev = bank b100–b199, 100 per letter; candidates b000–b059 = `tests/emnist_cand60`; all 26 classes), then
official tests once (MNIST 10 000 with the complete subset reported separately, EMNIST 20 800) for the reference and the
best configuration. Regression check: reference reproduces 81.06 % (order 0) exactly; 9 unit tests pass.

## I — results of the improvements (2026-10-20) — `results_I*.csv`
MNIST, 10 originals per digit, dev, readout c, mean ± sd over 3 orders; best τ per variant in bold where it beats τ 0.

| variant | τ 1.0, ρ 0.6 | τ 1.0, ρ 0.7 | τ 0.8, ρ 0.7 | τ 0, ρ 0.6 | τ 0, ρ 0.7 | verdict |
|---|---|---|---|---|---|---|
| reference (t110, exact fields) | 81.34 | 82.62 | 82.62 | 82.18 | 82.75 | |
| 1 overlapping receptive fields | 83.22 | 84.07 | 84.15 | 83.49 | 84.50 | +1.5 … +1.9 — keep |
| 2 skeleton rules | 81.88 | 83.09 | 83.09 | 82.69 | 83.37 | +0.5 — keep |
| 3 three filters 110/150/190 (with rules), MAX | 85.15 | 85.92 | 85.94 | 86.07 | 85.95 | +3.2 … +3.9 — keep |
| 4 stroke curvature | 78.86 | 80.04 | 80.04 | 80.21 | 80.18 | −1.5 … −2.5 — drop |
| 5 gain n/(n+1) | 76.67 | 81.24 | 81.24 | 72.63 | 78.69 | −1.4 … −9.5 — drop (removes universal neurons, univ 0.96 → 0.64, but loses coverage) |
| all five (pre-registered) | 74.67 | 71.91 | 71.56 | 77.57 | 72.43 | dragged down by 4 and 5 |
| **best = 1 + 3 (post-hoc)** | 86.37 | 87.80 | **87.83** | 85.89 | 87.51 | +5.0 … +5.2 over the reference |


**Reduction now helps** (first time): with `best`, τ 0.8 > τ 0 by +0.95 (ρ 0.6) and +0.32 (ρ 0.7); τ 1.0 > τ 0 by +0.48 / +0.29.
On EMNIST the effect is clearer (below). Overlapping fields + several filters give the reduction stable fine synapses to keep.

His 76 originals with his 13 hand subclasses (fixed map, 1 order):

| | τ 1.0 | τ 0.8 | τ 0 |
|---|---|---|---|
| reference | 55.91 | 72.85 | 84.32 |
| best | **67.69** | **79.11** | 83.27 |

Overlap almost halves the cost of strict reduction on hand-made subclasses (−28 → −16 pp vs τ 0) but does not remove it:
hand subclasses group stylistically different originals; novelty-made neurons group similar ones, and there τ 0.8 wins.

EMNIST (26 classes, 10 originals per letter = bank b000–b009, dev = bank b100–b199, 2 600 images, ρ 0.7, 1 order):

| | τ 1.0 | τ 0.8 | τ 0 |
|---|---|---|---|
| reference | 61.88 (top-3 83.81) | 61.88 | 62.77 |
| best | 70.81 (88.31) | **71.62 (88.35)** | 69.69 (87.69) |

`best` +8.9 pp over the reference; reduction +1.1 (τ 1.0) / +1.9 (τ 0.8) over τ 0.
Final configurations chosen on dev by the pre-declared rule (highest dev top-1): `best`, τ 0.8, ρ 0.7 — for MNIST and
EMNIST; the reference at its own best dev point (τ 0, ρ 0.7). Official tests are run once for these.

His 76 originals, his 13 hand subclasses, every switch alone (`results_I_base76.csv`, 1 order):

| variant | τ 1.0 | τ 0.8 | τ 0 |
|---|---|---|---|
| reference | 55.91 | 72.85 | 84.32 |
| overlap | 65.13 | 77.40 | 82.36 |
| rules | 54.96 | 70.74 | 84.27 |
| three filters | 52.10 | 73.00 | **87.42** |
| curvature | 52.76 | 70.29 | 82.72 |
| all five | 72.55 | 76.85 | 82.16 |
| best (overlap + filters) | 67.69 | 79.11 | 83.27 |

On the hand-made subclasses reduction loses in every variant; the best is the union of the three filters, 87.42 % on dev
(ComAN with the same originals and subclasses: 81.11 %).

## Official tests, run once (2026-10-20/21) — `results_I_test.csv`, per-image dumps `tests/_isl/final_*_test.jsonl`
MNIST, official test (10 000; the `complete` subset as used in his paper reported separately):

| training | configuration | all 10 000 | top-3 | complete (8 708) | incomplete (1 290) |
|---|---|---|---|---|---|
| 10 candidates / digit | reference (τ 0, ρ 0.7) | 81.44 | 94.04 | 84.36 | 61.86 |
| 10 candidates / digit | **best** (τ 0.8, ρ 0.7) | **87.07** | 96.40 | **89.34** | 71.78 |
| 60 candidates / digit | reference | 89.93 | 97.66 | 91.81 | 77.29 |
| 60 candidates / digit | **best** | **93.04** | 98.94 | **94.74** | 81.63 |

best − reference: +5.63 pp (95 % CI +4.96 … +6.30, McNemar p = 5e-61) with 10 per digit; +3.11 pp (+2.58 … +3.64,
p = 2e-30) with 60. For orientation: ComAN (his 76 hand-picked originals, hand subclasses, test-tuned knobs) 91.13 % on
`complete`; the matching-free model with 60 uncurated train candidates per digit 94.74 %, with 10 per digit 89.34 %.

EMNIST-letters, official test (20 800, all 26 classes; evaluation parallelised over 4 forked workers — checked to give
identical results on dev, 71.62 % both ways):

| training | configuration | top-1 | top-3 | I + l as one class |
|---|---|---|---|---|
| 10 per letter | reference (τ 0, ρ 0.7) | 63.78 | 84.54 | 66.18 |
| 10 per letter | **best** (τ 0.8, ρ 0.7) | **71.59** | 88.84 | 74.00 |
| 60 per letter | reference | 71.91 | 91.68 | 74.19 |
| 60 per letter | **best** | **80.27** | 95.47 | 82.73 |

best − reference: +7.81 pp (95 % CI +7.18 … +8.44, p = 3e-130) with 10 per letter; +8.36 pp (+7.75 … +8.97, p = 2e-158)
with 60. Remaining confusions (best, 60 per letter): I↔L 511, G↔Q 245, U↔V 141, O↔Q 140, A↔Q 129, H↔N 113.
For orientation on the same test: fold concepts + graph matching 51 %; the band system with two rounds (needs an
observer) 84.6 %.

## E — error analysis in the terms of the theory (dev only; `notes/scripts_isl/isl_errors.py`, `best`, τ 0.8, ρ 0.7,
60 originals per class). Categories (first match): D detector — the image's topology (ends, junctions, cycles) occurs in
no training original of its class but in the predicted one; S separability (eq. 105) — the topology occurs in both
classes and the two attractors overlap at least as much as the pair's median; C coverage (§11) — the true class responds
clearly weaker (< 0.9 of the winner); M margin — lost by < 10 %.

| | dev top-1 | errors | true class 2nd | S | M | C | D | single open stroke | r_true / r_win (median) |
|---|---|---|---|---|---|---|---|---|---|
| EMNIST | 79.96 | 521 | 61 % | 43 % | 30 % | 22 % | 6 % | 30 % | 0.93 |
| MNIST | 94.54 | 109 | 60 % | 30 % | 28 % | 35 % | 7 % | 37 % | 0.91 |

EMNIST pairs (count, median attractor overlap): G↔Q 42 (0.40), I↔L 41 (0.51), U↔V 29 (0.42), O↔Q 18 (0.73), K↔X 17,
H↔N 15. MNIST: 3↔5 16, 2↔7 12, 4↔9 7 (all C — the 9 has no covering detector), 8↔9 7.
Reading: most errors are near misses between classes whose attractors share most synapses where the image's topology
is shared — positive-only learning does not enforce the separability eq. 105 assumes; per his own conclusion (Table 2)
separation has to come from the parametric layer. A third of the errors are single open strokes, where topology says
nothing and only the geometry along the stroke can decide.

## J — ideas from the error analysis, pre-registered 2026-10-21 (before running)
Each alone on top of `best` (τ 0.8, ρ 0.7; MNIST 10 per digit, 3 orders; EMNIST 10 per letter, 1 order; dev), then the
non-inferior ones together, then 60 per class, then official tests once.
1. `chains` — parametric relation arcs along the traversal of every stroke (his chat scheme; eq. 155–157): the stroke is
   resampled into 4 equal parts; at each of the 3 joints a synapse (joint position, tangent orientation, bend magnitude
   <15 | 15–45 | 45–90 | ≥90°, bend side toward / away from the centre of mass); plus junction branches: the direction in
   which each stroke leaves a junction (T vs Y vs X). Targets S / M errors and single open strokes.
2. `fine` — a 4th detector channel: fine-scale skeleton (60 GNG nodes instead of 35, simplification ε 2.5 instead of 4.55,
   threshold 150, rules) — spatial-frequency channels; targets lost short tails (O/Q, G/Q) and D errors.
3. `fovea` — finer segmentation only at the anchors (critical points): position 8×8 and direction 16 sectors added to the
   point synapses (attention operator F, §13; cortical magnification at fixation; bottom-up, no hypothesis about the class).
4. `wideaug` — augmentation family adds scale ±10 % and shear ±0.2 to rotation ±10° / shift ±3 px (§12 — explores
   parameters, keeps structure); targets C errors.
5. `rho8` — novelty threshold ρ 0.8 (more detectors for rare styles); targets C errors.
Not tried (need the professor's consent): anti-Hebbian depression on a foreign class (breaks Axiom 3); context / word
attractors for I↔L.

## J — results, each idea alone on top of `best` (dev; `results_J.csv`)

| idea | MNIST 10/digit (3 orders) | Δ | EMNIST 10/letter | Δ |
|---|---|---|---|---|
| best (reference) | 87.83 | | 71.62 | |
| 1 chains (arcs along strokes + junction branches) | 87.19 ± 0.52 | −0.64 | 72.31 | +0.69 |
| 2 fine-scale skeleton channel | **89.08** ± 0.15 | **+1.25** | 72.19 | +0.57 |
| 3 fovea at the anchors | 88.20 ± 0.10 | +0.37 | **72.69** | **+1.07** |
| 4 wider augmentation (scale, shear) | 88.65 ± 0.06 | +0.82 | 70.88 | −0.74 |
| 5 ρ 0.8 | 87.86 ± 0.06 | +0.03 | 71.88 | +0.26 |

All five non-inferior (> −1 pp) on both sets -> pre-registered combination `best2` (all five). Post-hoc `best2pos` =
only 2 + 3 (positive on both sets).

Combinations (dev, 10 per class): `best2pos` (fine + fovea, post-hoc) MNIST 89.68 ± 0.11 / EMNIST 73.12;
**`best2` (all five, pre-registered rule) MNIST 89.70 ± 0.12 (top-3 98.00) / EMNIST 74.88 (top-3 90.54)** — +1.9 / +3.3 pp
over `best`; universal neurons mostly gone on MNIST (univ 0.96 → 0.42). Final configuration: `best2` (τ 0.8, ρ 0.8).

## K — the same 76 originals as his concepts, official MNIST test (2026-10-21)
Dev (`results_K_base76.csv`): novelty map — best τ 0.8 85.37 / τ 0 84.50; **best2 τ 0.8 88.90** / τ 0 88.46; his 13 hand
subclasses — best2 τ 0.8 81.26 / τ 0 82.57. Selected by dev: best2, novelty map, τ 0.8, ρ 0.8.
ComAN on the full official test run through the live pipeline (pipeline recovered: Neo4j started, `recover_pipeline.sh 8`,
new host IP; 13 concepts loaded; his config). Control: the 1 000 `complete` images of the idle-machine run give the same
1 000 answers (91.60 %), so the parallel offline load did not change GED.

| official MNIST test | ComAN (his 76 originals, hand subclasses, test-tuned knobs, graph matching) | matching-free best2 (same 76 originals, novelty map) |
|---|---|---|
| all 10 000 | 82.24 (top-3 86.70; 58 skeleton failures) | **89.11** (top-3 96.67) |
| `complete` 8 708 | 90.89 | 91.39 (+0.49, p = 0.21) |
| `incomplete` 1 290 | 23.95 | **73.80** (+49.84) |

Paired over all 10 000: +6.87 pp (95 % CI +6.04 … +7.70, McNemar p = 2e-59). On the curated subset the two are equal;
the matching-free model does it without matching, hand subclasses or test-tuned knobs, and keeps working on broken strokes.

## J — final configuration `best2` (τ 0.8, ρ 0.8): dev with 60 per class and official tests (2026-10-21)
Dev, 60 per class: MNIST 94.89 (top-3 99.25; best 94.54); EMNIST 81.62 (top-3 96.42; best 79.96).
Official tests, once (`results_J_test.csv`, dumps `tests/_isl/final2_*_test.jsonl`):

| test | training | best | **best2** | top-3 | Δ (paired) |
|---|---|---|---|---|---|
| MNIST 10 000 | 10 per digit | 87.07 | **89.55** | 97.75 | +2.48 (+1.93 … +3.03), p = 1e-18 |
| MNIST 10 000 | 60 per digit | 93.04 | **94.50** | 99.15 | +1.46 (+1.02 … +1.90), p = 6e-11 |
| MNIST `complete` 8 708 | 10 / 60 per digit | 89.34 / 94.74 | **91.15 / 95.61** | | |
| MNIST `incomplete` 1 290 | 10 / 60 per digit | 71.78 / 81.63 | **78.84 / 86.98** | | |
| EMNIST 20 800 | 10 per letter | 71.59 | **73.49** | 90.21 | |
| EMNIST 20 800 | 60 per letter | 80.27 | **82.61** | 96.35 | |

## L — audit against the professor's letters, pre-registered 2026-10-22 (before running)
His first sentence: "an attractor is not formed per sample; it results from the reduction over a SET of examples (f = 1)".
1. L1 census (descriptive, no tuning): how many `best2` neurons (τ 0.8, ρ 0.8, order 0) rest on ONE original, and which
   share of the official-test answers they give (joined with the `final2_*` dumps by neuron index).
2. L2 `best2` at strict f = 1 (τ 1.0) on dev: MNIST 10 per digit (3 orders), EMNIST 10 per letter (1 order). Def. 1 of
   the manuscript allows f ≥ τ, his letter asks for f = 1 "for simplicity"; τ 1.0 was measured for `best`, never for
   `best2`. Reported whatever it gives; the final configuration is NOT re-selected from this run.

### L1 — census of `best2` neurons (order 0; `notes/scripts_isl/isl_census.py base76 cand60:10 …`, joined with `tests/_isl/final2_*_test.jsonl`)

| training | originals | neurons | built from ONE original | share of originals in such neurons | test answers given by them | their accuracy | accuracy of multi-original neurons |
|---|---|---|---|---|---|---|---|
| his 76 (MNIST) | 76 | 70 | 65 (93 %) | 86 % | 80.1 % | 87.4 % | 96.0 % |
| MNIST 10 / digit | 100 | 81 | 69 (85 %) | 69 % | 71.0 % | 87.7 % | 94.0 % |
| MNIST 60 / digit | 600 | 378 | 291 (77 %) | 48 % | 51.7 % | 91.5 % | 97.7 % |
| EMNIST 10 / letter | 260 | 242 | 230 (95 %) | 88 % | 86.8 % | 73.1 % | 75.9 % |
| EMNIST 60 / letter | 1 560 | 1 261 | 1 076 (85 %) | 69 % | 68.0 % | 81.3 % | 85.4 % |

Reading: in the final model most "attractors" are the stable part of ONE original's augmentation family — i.e. formed
per sample, which his letter rules out ("атрактор не формується на кожен зразок"). Only with 60 originals per digit
does about half of the test get answered by neurons that reduced over several originals; those are clearly more
accurate. With ρ 0.8 the novelty rule keeps almost every uncurated original as its own detector.

### L2 — `best2` at strict f = 1 (dev; `results_L.csv`)

| dev, 10 originals per class | τ 0.8 (final) | τ 1.0 (f = 1) |
|---|---|---|
| MNIST (3 orders) | 89.70 ± 0.12 | 89.78 ± 0.04 |
| EMNIST (1 order) | 74.88 | 74.62 |

Equal within noise: with overlapping fields and several channels, the strict f = 1 of his letter costs nothing. (Note:
with 85–95 % single-original neurons, f = 1 vs 0.8 only matters for the few multi-original ones — L1.)
Also on record (results_B.csv, 2026-10-12, never in a report): sigmoidal branch readout `b` (soma sums nonlinear
branches) is 5.3–13.4 pp below the divisive readout `c` at every τ / ρ of the grid.

## M — Nikita's ComAN (GED kept), observers removed, improved by compliant steps — pre-registered 2026-10-22 (before running)
Rules: repo-root `CLAUDE.md` (written 2026-10-22 from his letters). Data: his 76 originals, his 13 hand subclasses and his
augmentations (`tests/_isl_train`); dev `tests/mnist_dev` (1 996); knowledge snapshot `tests/_isl/knowledge_before_coman.json`.
Steps run in order, each on top of the accepted ones; paired McNemar + 95 % CI vs the previous accepted point.
Acceptance rule: lower 95 % CI bound of the paired difference > −1 pp. Step 1 is mandatory (it removes violations).
0. ComAN as is (his config `tests/_isl/nikita_cfg.json`, code defaults λ 0.10, gate 0.33) — drift control, expect ≈ 81.1.
1. ComAN-clean: λ = 0 (test-tuned prior removed), `range_gate_rel_width` = 0 (cross-class `FEATURE_GLOBAL_SPANS` gate
   removed → the original out-of-band cliff, as described in the manuscript). Profile `tests/_isl/coman_isl_cfg.json`.
2. One detector D at training and recognition: his 13 subclasses re-ingested at 110 / 4.55 (the recognition D), graphs
   exported, folded offline with his chain (pairwise max common minor, f = 1); an example the concept cannot absorb (no
   common minor) is skipped and counted, instead of aborting the concept. Files in sorted order; 3 orders reported
   (Theorem 2).
3. More parameters (his point 1): the code's 28 default node features instead of 13.
4. Stable interval by majority (his point 1, Def. 1 f ≥ τ): shortest interval covering ≥ τ of the merged values,
   centre = median; τ ∈ {0.8, 0.9} (both reported, better on dev kept).
5. Quantified deviation outside the interval (his point 1): soft ramp for every feature (`range_gate_rel_width` 1.0 —
   independent of other classes), `range_soften_span` ∈ {1, 2, 4} half-widths.
6. Several filters at recognition (his point 2): thresholds 110 / 150 / 190, per concept MAX of the similarity.
7. Attractor complexity in the reaction (§15): λ ∈ {0, 0.05, 0.10, 0.20} chosen on dev (offline from the dumps).
8. (if time allows) novelty map instead of hand subclasses, ≥ 2 originals per concept (Theorem 3 + rule 1).
Final configuration = all accepted steps; official MNIST test (10 000; `complete` / `incomplete` separately) run ONCE.

### M — addendum, written after the refold control and BEFORE seeing steps 4 (τ 0.8 / 0.9)
Control N160 (his detector 160 / 5, his files, our offline chain with the current concept-creator code, sorted order):
74.85 % on dev with the step-3 configuration vs 78.01 % with his stored concepts — the current fold code (or his
unknown order) does not reproduce his concepts (4_1: 3 nodes instead of 8; 37 of 77 examples not absorbed; 3_1, 2_2,
5_1 differ). So every refold-dependent step carries this −3.2 pp. Rule kept as declared (vs the accepted point), and in
addition each refold step's ISOLATED effect is reported against the matching refold control: step 4 vs N160, step 2
(D 110 / 4.55) vs N160 under the same configuration. A combined refold candidate (D110 + the better interval) enters
the final selection only if it beats the accepted no-refold configuration by the same rule.

### M — results on dev (`results_M.csv`; dumps `tests/_isl/coman/`; configs `notes/scripts_isl/coman_cfg/`)
Offline re-scoring (`coman_rerank.py`) reproduces the live answers exactly (80.91 from the step-0 dump; 82.24 / 90.89 /
23.95 from the K test dump).

| step | dev top-1 | top-3 | Δ vs accepted (95 % CI) | McNemar p | decision |
|---|---|---|---|---|---|
| 0 ComAN as is (his concepts, λ 0.10, gate 0.33) | 80.91 | 85.27 | — | — | reference (21.10: 81.11 / 80.91) |
| 1 ComAN-clean: λ 0, gate 0 (cliff) | 76.40 | 84.37 | −4.51 (−5.70 … −3.32) | 6e-14 | mandatory |
| 2 one detector: refold at 110 / 4.55 | 75.60 | 85.42 | −0.80 (−2.43 … +0.82) | 0.36 | rejected |
| 3 28 node features instead of 13 | 78.01 | 84.32 | +1.60 (+0.33 … +2.87) | 0.017 | **accepted** |
| 4 majority interval τ 0.8 / τ 0.9 (refold at 160 / 5) | 63.13 / 71.09 | 80.11 / 83.62 | −14.88 / −6.91 | ≤ 2e-15 | rejected |
| 5 soft ramp outside the interval, span 1 / 2 / 4 | 80.21 / 80.76 / **80.96** | 84.87 | +2.96 (+2.02 … +3.89) for span 4 | 4e-10 | **accepted (span 4)** |
| 6 three filters 110 / 150 / 190, MAX per concept | 83.52 | 88.18 | +2.56 (+1.60 … +3.51) | 1.5e-7 | **accepted** |
| 7 complexity term λ 0.05 / 0.10 / 0.20 | **83.82** / 82.01 / 74.15 | 88.28 | +0.30 (−0.34 … +0.94) for 0.05 | 0.44 | **accepted (λ 0.05)** |

Single filters at step 6: 150 → 80.71, 190 → 78.21 (110 → 80.96); MAX of the three 83.52.
Diagnostics (not decisions):
- Refold control N160 (his D, current fold code): 74.85 vs 78.01 with his stored concepts (−3.16, p 2.5e-5).
- Isolated detector effect (same fold code, step-3 config): D110 75.70 vs N160 74.85, +0.85 (−0.24 … +1.94), p 0.15.
- Isolated interval effect vs the refold control: τ 0.8 −11.72, τ 0.9 −3.76 (both p < 1e-7). POST-HOC with the soft ramp
  (span 4): N160 78.26, τ 0.9 75.45, τ 0.8 73.10 — narrower majority intervals hurt ComAN either way (his GED cost
  weights a feature by 1 / (width + ε), so a narrower band both raises the weight and widens the out-of-band region).
- Theorem 2 on the D110 refold (sorted vs 2 shuffled orders): attractor structure identical in all orders for 6 / 13
  subclasses (1_1, 1_3, 2_2, 4_1, 6_1, 8_1); 4_1 absorbs only 45 of 77 examples (4 of 7 originals) at 110 / 4.55.
Accepted so far: his concepts + 28 features + soft ramp span 4 + filters 110/150/190 MAX + λ 0.05 → dev 83.82
(ComAN as is 80.91; ComAN-clean 76.40).

### M — refold candidate and the final configuration (written BEFORE the official test)
Refold candidate per the addendum (D110 = his 13 subclasses refolded with the recognition detector 110 / 4.55; min/max
intervals, since the majority interval was rejected) with the accepted readout (28 features, soft ramp span 4, filters
110/150/190 MAX): λ grid 0 / 0.05 / 0.10 / 0.20 → 83.97 / **84.72** / 84.67 / 80.41. Against the accepted configuration
on his stored concepts (83.82): +0.90 (−0.32 … +2.13), p 0.17 — passes the rule and is higher, so it is the final
configuration (one detector at training and recognition, §2.1).
**Final configuration (frozen):** concepts `<d>_<sub>sD110` (his 76 originals, his 13 subclasses and augmentations, his
chain f = 1 with non-absorbable examples skipped, D 110 / 4.55); GED with his cost ladder, ε 0.1, timeout 5; 28 node
features; out-of-band soft ramp for every feature (`range_gate_rel_width` 1.0, span 4); detector filters 110 / 150 / 190
with MAX per concept; λ 0.05. Official MNIST test (10 000; `complete` / `incomplete` reported separately): ONE run.
Reference on the same test: his run of 21.10 (82.24 / 90.89 / 23.95) and ComAN-clean (one run, his concepts, λ 0, gate 0).

### M — official MNIST test, run ONCE (2026-10-22; dumps `tests/_isl/coman/final_test_t{110,150,190}.jsonl`, `clean_test.jsonl`)

| official test | ComAN as is (21.10 run) | ComAN-clean (λ 0, gate 0) | **final** |
|---|---|---|---|
| all 10 000 top-1 / top-3 | 82.24 / 86.41 | 76.56 / 85.75 | **82.84 / 88.80** |
| `complete` 8 708 | 90.89 | 84.68 | **91.01** |
| `incomplete` 1 290 | 23.95 | 21.86 | **27.75** |
| no answer | 108 | 106 | 57 |

Final − as is: all +0.60 (−0.05 … +1.25), p 0.077; complete +0.11 (−0.59 … +0.82), p 0.77; incomplete +3.80
(+2.13 … +5.47), p 1.2e-5. Final − clean: all +6.28 (+5.53 … +7.03), p 1e-60; complete +6.33; incomplete +5.89.
Single filters of the final model: 110 → 78.26, 150 → 77.38, 190 → 75.36 (λ 0, from pl_dump).
Per digit (as is → final): 0 81.6→81.1, 1 95.7→83.3, 2 72.9→75.9, 3 94.4→87.2, 4 83.2→93.7, 5 88.8→93.2,
6 74.2→79.1, 7 94.8→94.9, 8 62.1→62.9, 9 72.6→77.4. Top confusions final: 8→6 276, 9→5 161, 1→7 123.
Reading: without any test-tuned knob or other-class statistic the model equals his on the full test and on
`complete`, is better on broken strokes and in top-3; the dev gain over "as is" (+3.8) shrinks on the test (+0.6)
because his λ and gate were tuned on this very test. Neo4j left with his 13 concepts active (`coman_concepts.py
activate nikita`); the final set is `D110`.

## N — everything else the professor asked + compatible old results + ideas from the error analysis (pre-registered 2026-10-22, before running)
Parallel offline work (own files, merged later): `lab_N_projection.md` (Section IV projection with attractors over ≥ 2
originals + his point 3 vector reaction / local WTA), `lab_N_2L.md` (his two-level hypergraph scheme from letter 1).
ComAN part (live), each alone on top of the M final (dev 84.72), same acceptance rule; then all accepted together
(if the combination fails the rule, the best single one); a changed final gets ONE more official test run, disclosed
as the second use of the test.
Error analysis of the M final on dev (305 errors): 145 (48 %) the true class's attractors do not embed at all
(critical-point reduction fails → no match), 33 the true attractor is larger than the image (cc > ic, ineligible),
8 no match for any class, 119 the true class matched but lost (21 by < 0.02).
- N1 his point 2 at GRAPH FORMATION: concepts also folded from the 150 and 190 filters (D150, D190; 39 concepts active
  together), recognition 3 filters MAX, λ 0.05.
- N2 his point 1, the weight coefficient: ε 1.0 instead of 0.1 (weights depend less on band width); and the majority
  interval τ 0.9 (refold D110m9) with ε 1.0 — tests whether 1 / (width + ε) is what broke the majority interval.
- N3 ours (projection +1.25): fine skeleton (threshold 150, simplification ε 2.5) as a 4th filter at recognition.
- N4 ours (projection +0.5): skeleton rule "keep the short junction edge when a straight stem passes" at training and
  recognition (refold D110ps).
- N5 ours ("two-sided" normalisation against the small attractor): coverage^α, α ∈ {0.5, 1}, offline.
- N6 new, from the error analysis: when the critical-point reduction fails, compare the raw graphs instead of
  rejecting the concept (`preprocess_fallback` true) — recognition of an incomplete input (manuscript: incomplete
  patterns, Def. 1 f ≥ τ).

<!-- merged from lab_N_projection.md (written by the parallel offline track) -->
### N-projection — Section IV (projection, no matching) made compliant with rule 1, + his point 3 (vector reaction, local WTA) — pre-registered 2026-10-22 (before running)

Rule 1 (CLAUDE.md, his letter): an attractor is a reduction over a SET of originals, never one sample. The `best2`
projection model had 77–95 % single-original neurons (L1), so it is re-run here only in forms where EVERY competing
neuron rests on ≥ 2 originals. Data: his 76 originals with his augmentations (split `base76`), his 13 hand subclasses
(`tests/_isl/base76_subclasses.json`, ≥ 3 originals each); dev `dev` (1 996 official-train images). Detector, H0,
learning: `best2` (overlapping fields, channels t110r/t150r/t190r/t150rf with MAX, chains, fovea, wide-augmentation
training channels), readout c (divisive normalisation), WTA argmax unless stated.

- **P1** his 13 hand subclasses = 13 neurons (fixed map), τ ∈ {1.0, 0.8} (τ 0 excluded: it is no reduction).
- **P2** novelty map (Theorem 3) + consolidation: only neurons with ≥ 2 originals compete (`min_originals` 2);
  ρ ∈ {0.5, 0.6, 0.7, 0.8} × τ ∈ {1.0, 0.8}; 3 presentation orders (mean ± sd). Census per configuration: neurons,
  neurons with ≥ 2 originals, share of originals inside competing neurons.
- **P3** his point 3 (letter 1: the detector's output is a feature vector passed between all co-activated neurons;
  each decides by the same rule whether it is the winner, otherwise it is inhibited) and §15 (the reaction carries the
  structural and the parametric terms). Reaction vector of a neuron = (structural part: readout c restricted to the
  relational synapses — hyperedges `R` and arcs along strokes `K`; parametric part: readout c restricted to the point
  synapses `E`, `C`, `J`, `JB`). Two pre-declared rules, identical for every neuron:
  - (i) `distinct` — co-active set = neurons whose scalar response ≥ 0.9 × the strongest (k-WTA by lateral
    inhibition ⚠️); j inhibits i if j's activation on A_j \ A_i (normalised by the weight of A_j \ A_i) exceeds i's
    on A_i \ A_j; the winner is the neuron no one inhibits; if none or several, argmax of the scalar response.
  - (ii) `pareto` — a neuron is inhibited if another is ≥ on both parts and > on one; among the survivors the largest
    sum (structural + parametric). (Note: the largest-sum neuron is always Pareto-optimal, so (ii) = argmax of the sum.)
  P3 is applied on top of the best compliant configuration of P1 / P2 (dev).
- **Selection rule**: the highest dev top-1 among the P1 / P2 / P1+P3 / P2+P3 configurations in which every competing
  neuron has ≥ 2 originals. Official MNIST test (`mtest`, 10 000) run ONCE for it: all / `complete` / `incomplete`
  (manifest `datasets/mnist_all_manifest.csv`), top-3, paired McNemar vs ComAN as is (`tests/_isl/coman_mnist_all.jsonl`,
  82.24 %).

#### Results on dev (`results_N_projection.csv`; driver `notes/scripts_isl/isl_projection_n.py`, log `tests/_isl/N_projection.log`)

| configuration | dev top-1 (± sd, orders) | top-3 | neurons | competing (≥ 2 originals) | originals inside competing neurons |
|---|---|---|---|---|---|
| P1 hand subclasses, τ 1.0 | 69.99 (1) | 87.47 | 13 | 13 (min 3 originals) | 100 % |
| P1 hand subclasses, τ 0.8 | 81.26 (1) | 91.03 | 13 | 13 (min 3) | 100 % |
| P2 novelty + consolidation ρ 0.5, τ 1.0 | 74.75 ± 2.63 | 92.10 | 15.7 | 15.3 | 99.6 % |
| P2 ρ 0.5, τ 0.8 | 83.25 ± 2.11 | 93.60 | 14.7 | 14.3 | 99.6 % |
| P2 ρ 0.6, τ 1.0 | 78.61 ± 2.37 | 92.27 | 23.3 | 17.0 | 91.7 % |
| **P2 ρ 0.6, τ 0.8** (best P1/P2) | **83.27 ± 1.11** | 93.42 | 21.3 | 15.7 | 92.5 % |
| P2 ρ 0.7, τ 1.0 | 80.48 ± 0.23 | 90.71 | 38.7 | 20.7 | 76.3 % |
| P2 ρ 0.7, τ 0.8 | 80.31 ± 0.49 | 90.78 | 38.7 | 20.7 | 76.3 % |
| P2 ρ 0.8, τ 1.0 / 0.8 | 36.84 ± 0.05 | 39.43 | 70.0 | 5.0 | 14.5 % (almost every neuron is a singleton) |
| **P3 `distinct` on P2 ρ 0.6 τ 0.8** | **85.65 ± 0.96** | 93.97 | 21.3 | 15.7 | 92.5 % |
| P3 `pareto` on P2 ρ 0.6 τ 0.8 | 82.85 ± 1.02 | 93.74 | 21.3 | 15.7 | 92.5 % |

Reading:
- Strict f = 1 costs 4.7–11 pp at every map (τ 0.8 > τ 1.0); reduction over sets works only with the relaxed
  threshold of Def. 1.
- With consolidation the novelty map (no hand subclasses) beats his hand subclasses: 83.27 vs 81.26. ρ 0.5–0.6 merge
  originals into ~15 competing neurons; ρ ≥ 0.7 leaves too many singletons.
- His point 3 as the `distinct` rule (co-activated neurons compare their distinctive evidence, one rule for all) adds
  +2.4 pp (85.65); `pareto` (= argmax of structural + parametric) does not help.
- Selected by the pre-registered rule: **P3 `distinct` on P2 ρ 0.6 τ 0.8**. Every competing neuron rests on ≥ 2
  originals (test model, order 0: 16 competing neurons, originals per neuron min 2, median 4).

#### Official MNIST test, run ONCE (dump `tests/_isl/N_projection_test.jsonl`; paired with ComAN as is, `coman_mnist_all.jsonl`)

| official test | ComAN as is | **projection, rule-1 compliant + `distinct`** | Δ (95 % CI) | McNemar p |
|---|---|---|---|---|
| all 10 000 (top-3) | 82.24 | **83.64** (93.03) | +1.40 (+0.49 … +2.31) | 0.0027 |
| `complete` 8 708 | 90.89 | 85.77 (92.97) | −5.12 (−5.97 … −4.27) | 3.6e-32 |
| `incomplete` 1 290 | 23.95 | **69.30** (93.49) | +45.35 (+42.17 … +48.53) | 2.9e-125 |

Per digit: 0 91.1, 1 85.7, 2 74.5, 3 85.8, 4 95.5, 5 84.5, 6 89.2, **7 60.5**, 8 86.8, 9 84.0.
Reading: once every attractor is a reduction over ≥ 2 originals the projection model loses its lead on the curated
`complete` subset (−5.1 pp vs ComAN), still wins on the whole test (+1.4) thanks to broken strokes (+45 pp), and its
weak spot is 7 (60.5 %). For comparison, the non-compliant `best2` (65 of 70 neurons single-original) gave 89.11 % on
all and 91.39 % on `complete` — the gap is the price of rule 1 with 76 originals.

<!-- merged from lab_N_2L.md (written by the parallel offline track) -->
### N-2L — the professor's two-level scheme from his first letter, as a model (pre-registered 2026-10-22, before running)

Code: `notes/scripts_isl/isl_2l.py` (offline, on the cached skeletons `tests/_isl/skel/<channel>/<split>`; no live
pipeline). Rules: repo-root `CLAUDE.md`. Data: his 76 originals (`base76`) with his 13 hand subclasses
(`tests/_isl/base76_subclasses.json`, every subclass ≥ 3 originals) and their cached augmentation families (rotation
±10°, shift ±3 px, 10 per original — the ISL cache; his own augmentation PNGs are not cached for the skeleton channels).
Dev `dev` (1 996 official-train images); official test `mtest` (10 000) — ONE run for the selected variant.

#### Design (every rule local, class-agnostic, fixed before running)
1. Level 1 (primitives, his "відрізки і різні типи точок"): the simplified skeleton graph — points (end E, junction J,
   corner C = degree 2 with interior angle < 160°, smooth S) and the segments between consecutive points. Frame: centre
   of mass of the skeleton, field of view 80 px (as the ISL simulator).
2. Parametric fibration (modal group): every element carries quantised parameters on the segmentation hierarchy —
   segment: direction of traversal (sectors 2 / 4 / 8), length class (2 / 4), position cell (2×2 / 4×4); anchor: position
   cell (2×2 / 4×4), exit direction for E (4 / 8), degree for J.
3. Capture point (bottom-up, no class knowledge): the top-most end point; else the top-most junction; else the top-most
   node. Traversal: depth-first from it along the segments; at a node the unvisited continuations in order of signed
   turn (left-most first). Each traversal path = a maximal walk between E / J nodes (or a closed loop).
4. Parametric relation arcs: between consecutive segments of a path, the signed turn at the shared node
   (L > +20°, R < −20°, else 0; 20° = 180° − the production corner angle).
5. Parametric reduction → hyperedges. Variant `sign`: maximal runs of a path whose turns keep one sign (0 allowed
   inside) — monotone arcs; a sign flip (inflection) breaks the run. Variant `dir`: maximal runs whose segments stay in
   one direction sector (8) — straight pieces; any sector change breaks the run. Variant `both`: the union. A hyperedge
   = (run class, chord-direction sector 4 / 8, length class 2 / 4, total turning class, mid-point cell).
6. Anchor candidates = the start and end nodes of the hyperedges (E, J, break points) + the capture point. Type: E, J,
   B (a break inside a stroke), with traversal rank r ∈ [0, 1].
7. Alignment ONLY by anchor candidates: optimal assignment (Hungarian, scipy) between the anchors of two hypergraphs,
   cost = |Δpos| / 0.25 + |Δrank|, only same type, non-match cost 1.0 (a pair costing ≥ 1 stays unmatched).
   A hyperedge corresponds when both end anchors correspond (either order) and the run class agrees; a parametric
   vertex corresponds when its element corresponds and its segment value is equal at that level.
8. Learning, per hand subclass (label = top-down signal that opens plasticity): seed = first original (sorted names);
   every example of the subclass (originals + augmentations) aligned to the seed; counters f(e) for anchors,
   hyperedges and parametric vertices (accumulating hypergraph on the seed's elements, eq. 25); attractor = f ≥ τ,
   τ = 1.0 (his letter); variant τ 0.8 (Def. 1). Kept hyperedges need both anchors kept (glued by their anchors);
   kept parametric vertices need their element kept. Anchor positions of the attractor = mean over matched examples.
9. Inference: the test hypergraph aligned to every attractor by anchors; matched weight m = Σ weights of attractor
   elements matched (structural: anchors + hyperedges, weight 1; parametric vertices: 1 + log2(segments), as in the
   simulator). Reaction (scalar, ⚠️ two-sided): m / √(W_att · W_test), W_test = the test's own weight of the same element
   kinds. Control: one-sided coverage m / W_att. WTA = argmax. Variant (his point 3): vector reaction
   (structural part, parametric part), each two-sided; identical local rule for every neuron: inhibited if another
   neuron is ≥ on both parts and > on one (Pareto); survivors decided by the sum.
10. Filters (his point 2): channels t110r / t150r / t190r, attractor per channel, neuron reaction = MAX over channels.

#### Variants and selection (dev)
- A (single changes from V1 = t110, `sign`, τ 1.0, two-sided scalar, pos+rank alignment):
  V2 `dir`; V3 `both`; V4 τ 0.8; V5 one-sided coverage (control); V6 vector reaction + Pareto; V8 alignment by
  position only (no rank).
- B: combination of the best choice in each group (reduction, τ, readout, alignment cost) — declared now.
- C: B + three filters with MAX (V7).
- Selected = highest dev top-1 among everything evaluated; that one only goes to the official test (all / complete /
  incomplete, top-3, McNemar vs ComAN as is `tests/_isl/coman_mnist_all.jsonl`).
- Theorem 2: the selected variant folded in 3 orders (seed = first original of each order; the counters themselves
  are commutative), share of subclasses whose attractor signature is identical.

#### Results (2026-10-22) — `results_N_2L.csv`, dumps `tests/_isl/n2l_*.jsonl`
Implemented as pre-registered (`notes/scripts_isl/isl_2l.py`, tests `unit_tests/test_isl_2l.py`). Simplification: the
augmentation families are the ISL cache's (rotation ±10°, shift ±3 px), not his augmentation PNGs.

| variant (dev, 1 996; his 76 originals, his 13 hand subclasses) | top-1 | top-3 | attractor anchors / hyperedges (median) |
|---|---|---|---|
| V1 t110, `sign`, τ 1.0, two-sided, pos + rank | 24.85 | 43.14 | 0 / 0 (241 images: no attractor responds) |
| V2 `dir` | 31.81 | 65.63 | 1 / 0 |
| V3 `both` | 39.38 | 70.29 | 1 / 0 |
| **V4 τ 0.8** | **55.46** | 77.71 | 1 / 0 |
| V5 one-sided coverage (control) | 25.85 | 44.99 | 0 / 0 |
| V6 vector reaction + Pareto rule | 24.90 | 42.99 | 0 / 0 |
| V8 alignment by position only | 28.06 | 56.26 | 1 / 0 |
| B best of each group (`both`, τ 0.8, one-sided, position only) | 43.69 | 87.42 | 4 / 1 |
| C = B + filters t110r / t150r / t190r, MAX | 45.19 | 88.13 | 4 / 1 |
| *P1 post-hoc: B with the two-sided reaction* | 67.79 | 91.43 | 4 / 1 |
| *P2 post-hoc: P1 + anchor tolerance 0.5 (40 px)* | 70.69 | 91.63 | 5 / 2 |
| *P3 post-hoc: P2 + structure counted over the originals only (§12)* | **70.84** | 92.13 | 5 / 2 |
| *P4 post-hoc: P3 at τ 1.0* | 52.56 | 78.16 | 4 / 1 |

Why it collapses at f = 1: within his hand subclasses the seed's anchors are found (same type, within 20 px) in only
17–45 % of the examples for 2_1, 3_1, 4_1, 4_2, 7_1 — one miss among 33–99 examples (originals + augmentations) removes
the element, so at f = 1 most attractors keep no hyperedge and ≤ 1 anchor. With the tolerance at 40 px the anchors of
different originals correspond in 89 % of the seed-anchor × original pairs (6 % lose to another anchor of the same type
nearby, 3 % are farther, 1 % the type is missing). The group-wise rule picked the one-sided readout on degenerate τ 1.0
attractors; on real attractors one-sided coverage gives the small-attractor problem (top-1 43.7, top-3 87.4).
Pareto + sum is, by construction, the argmax of the sum of the two normalised parts (the sum-maximiser is never
dominated) — the vector rule did not change anything measurable (V6 ≈ V1).
P3 dev confusions: 7→3 106, 7→2 53, 4→1 40, 2→3 26, 8→6 25 (7_1's seed anchors match 29–45 % of its examples).
Theorem 2 (3 orders; counters are commutative, the seed = first original of each order): identical attractor signature
in 10 / 13 subclasses for V4 (attractors of ~1 anchor), 5 / 13 for P3 — the dependence is the choice of the seed.

**Official MNIST test, run once each** (V4 = the pre-registered selection; P3 = post-hoc, labelled, not re-selected):

| | V4 (selected) | P3 (post-hoc) | ComAN as is |
|---|---|---|---|
| all 10 000 top-1 / top-3 | 54.89 / 77.38 | 71.02 / 91.79 | 82.24 / 86.41 |
| `complete` 8 708 | 58.99 | 77.06 | 90.89 |
| `incomplete` 1 290 | 27.29 | 30.23 | 23.95 |
| Δ vs ComAN, all (95 % CI), McNemar | −27.35 (−28.36 … −26.34), p ≈ 0 | −11.22 (−12.11 … −10.33), p 2e-134 | |
| Δ vs ComAN, incomplete | +3.33 (+0.93 … +5.73), p 0.008 | +6.28 (+3.96 … +8.59), p 1.6e-7 | |

Reading: his scheme, implemented literally (alignment only by anchor candidates, f = 1 over his hand subclasses with
their augmentations), does not yet reach ComAN: the hand subclasses are too heterogeneous for f = 1 by anchor
alignment, and without a two-sided reaction the small attractors win. With τ 0.8, a 40 px anchor tolerance and the
structure counted over originals (§12) it reaches 71 % (−11 pp vs ComAN overall) while being better on broken strokes
(+6.3 pp) and in top-3 (+5.4 pp). Alignment by anchors is polynomial (Hungarian on ≤ 10 anchors; dev in ~2 s).

### N — ComAN results on dev (`results_N.csv`; dumps `tests/_isl/coman/n*`), each alone vs the M final (84.72, λ 0.05)

| check | dev top-1 | Δ (95 % CI) | McNemar p | decision |
|---|---|---|---|---|
| N1 his point 2 at graph formation: concepts also from filters 150 and 190 (38 concepts; 8_1 at 190 absorbed one original → excluded by rule 1) | 84.77 | +0.05 (−0.69 … +0.79) | 1.0 | accepted (non-inferior) |
| N2a weight coefficient ε 1.0 | 85.02 | +0.30 (−0.07 … +0.67) | 0.18 | accepted |
| N2b majority interval τ 0.9 with ε 1.0 | 83.62 | −1.10 (−1.87 … −0.33); vs ε 1.0 min/max −1.40 | 0.007 | rejected — the weight is not why the majority interval fails |
| N3 fine skeleton (150, ε 2.5) as a 4th filter | 85.67 | **+0.95 (+0.46 … +1.44)** | 1.6e-4 | accepted |
| N4 protect-stems skeleton rule, training and recognition | 84.87 | +0.15 (−0.14 … +0.44) | 0.51 | accepted (non-inferior) |
| N5 coverage^α, α 0.5 / 1 (offline) | 73.85 / 60.62 | −10.9 / −24.1 | < 1e-45 | rejected |
| N6 compare raw graphs when the critical-point reduction fails (200-image subset, filter 110) | 76.00 vs 76.00 | 0 answers changed | 1.0 | no effect; ~10× slower (a full dev run did not finish in 5 min per image batch) |
N6 reading: the concepts that fail the reduction still cannot win on raw graphs — inserting a concept node costs
IMPOSSIBLE, so an attractor that does not embed in the image stays out; the strict minor relation (f = 1 at
recognition) is the bottleneck of ComAN on incomplete images, not the reduction step.
Combination of the accepted ones (pre-declared): N1 + N2a + N3 + N4 — concepts D110ps / D150ps / D190ps (stems rule),
recognition filters 110 / 150 / 190 / fine 150 with the stems rule, ε 1.0, MAX, λ 0.05 — running.
Combination N1 + N2a + N3 + N4 (39 concepts D110ps / D150ps / D190ps — every one ≥ 2 originals; filters 110 / 150 /
190 / fine 150 with the stems rule; ε 1.0; MAX; λ 0.05): dev **84.97** (top-3 91.63), vs the M final +0.25
(−0.67 … +1.17), p 0.67 — passes the rule, so by the pre-declared rule it is the N final (the best single, N3 alone,
85.67, is higher but not significantly: combination − N3 −0.70 (−1.49 … +0.08), p 0.10 — reported, not selected).
**N final ComAN frozen before the test**: the combination. Official MNIST test: ONE run of this configuration — the
second use of the test for ComAN (the first was the M final), disclosed in the report.

### N — official MNIST test of the N final ComAN (ONE run; the second test use for ComAN; dumps `tests/_isl/coman/final2_test_*.jsonl`)

| official test | ComAN as is | M final (1st test) | **N final** | Section IV (rule-1 + `distinct`) |
|---|---|---|---|---|
| all 10 000 top-1 / top-3 | 82.24 / 86.41 | 82.84 / 88.80 | **84.44 / 91.45** | 83.64 / 93.03 |
| `complete` | 90.89 | 91.01 | **92.59** | 85.77 |
| `incomplete` | 23.95 | 27.75 | 29.46 | **69.30** |

N final − as is: all +2.20 (+1.60 … +2.80), p 5e-13; complete +1.70 (+1.06 … +2.34), p 2e-7; incomplete +5.50
(+3.82 … +7.19), p 2e-10. N final − M final: all +1.60, p 4e-12. Section IV − N final: all −0.80 (−1.64 … +0.04),
p 0.065; complete −6.82, p 2e-68; incomplete +39.84, p 2e-105.
Per digit (as is / N final / Section IV): 0 81.6/81.3/91.1, 1 95.7/83.3/85.7, 2 72.9/85.2/74.5, 3 94.4/95.1/85.8,
4 83.2/89.8/95.5, 5 88.8/93.2/84.5, 6 74.2/81.1/89.2, 7 94.8/95.2/60.5, 8 62.1/65.6/86.8, 9 72.6/74.7/84.0.
Reading: without any observer the improved ComAN beats his model on every subset; the Section IV model is equal on the
whole test, far better on broken strokes and worse on complete contours — the two are complementary (digits 2/3/5/7
vs 0/4/6/8/9). Report for the professor: `report_letters.md` / `.docx` (supersedes `report_ComAN.*`).

## O — EMNIST-letters with the compliant models (pre-registered 2026-10-23, before running)
No hand subclasses or augmentations of Nikita exist for EMNIST, so the training originals are the first k bank images
per letter (`ecand60`, k = 10 and 60; 26 classes), dev `edev` (bank b100–b199, 2 600), official test `etest` (20 800) —
ONE run per final configuration. Old numbers for orientation only: `best2` 73.49 / 82.61 (10 / 60 per letter) — it
violates rule 1 (85–95 % single-original neurons); fold concepts + GED (band era) 51 %.
- O1 Section IV, compliant: `best2` detector and H0, novelty map + consolidation (only neurons with ≥ 2 originals
  compete), τ 0.8; grid on edev with 10 per letter, 1 order: ρ ∈ {0.5, 0.6, 0.7} × competition ∈ {argmax, distinct}.
  Selection: highest edev top-1. Then the selected configuration with 60 per letter (no new grid): edev + test.
  Census for every configuration.
- O2 ComAN, compliant (the M/N final readout: 4 filters 110 / 150 / 190 / fine 150 with the stems rule, ε 1, soft
  ramp span 4, 28 features, MAX, λ from {0, 0.05, 0.10} on edev). Subclasses = the competing neurons of the O1
  selected map with 10 per letter (Theorem 3 instead of hand subclasses; every group ≥ 2 originals); each group =
  its originals + 10 augmentations (rotation ±10°, shift ±3 px, §12); concepts folded with his chain at each filter
  (rule 1 enforced). edev, then the official test once.
- O2 amendment (2026-10-23, before any EMNIST ComAN result beyond the first edev filter): 162 concepts (58 groups × 3
  filters) make a filter pass ≈ 25 min on edev and ≈ 3.3 h on the test. N1 (concepts from every filter) added only
  +0.05 pp on MNIST, so O2 uses the concepts of the 110 filter only (E110ps, 55 concepts; 3 groups excluded by rule 1);
  recognition unchanged (4 filters, stems rule, ε 1, MAX, λ from edev). First pass with 162 concepts, filter 110 alone:
  edev 46.46 % (λ 0) — kept for the record.

### O — results (2026-10-23; `results_O.csv`, dumps `tests/_isl/O_*_etest.jsonl`, `tests/_isl/coman/o2b_*`)
O1 edev grid (10 per letter, τ 0.8, consolidation): ρ 0.5 61.19 / 68.92 (argmax / distinct), ρ 0.6 66.31 / **70.58**,
ρ 0.7 60.38 / 60.50 → selected ρ 0.6 + distinct (58 of 111 neurons compete, 79.6 % of the originals).
Official test, ONE run, 10 per letter: **70.04** (top-3 86.18; I + L as one class 72.74); per letter G 35, I 29, R 44,
H 55, Y 56, L 59 the weakest; confusions I→L 415, G→Q 234, L→I 146, Q→A 138, H→N 130. 60 per letter, same
configuration: edev 80.15 (top-3 94.27; 194 of 291 neurons compete, 93.8 % of the originals); official test, ONE run: **79.91** (top-3 93.75; I + L 82.27); confusions I→L 255, L→I 236, Q→G 189.
O2 ComAN on EMNIST, subclasses = the 58 consolidated groups (3 not written by rule 1 → 55 concepts, filter 110 only
after the amendment): edev filters 110 / 150 / 190 alone 48.15 / 47.81 / 46.42; MAX of the three with λ 0 / 0.05 /
0.10: 51.27 / **53.35** / 53.27. Stopped before the official test at the user's request (≈ 5 h; dev already shows
ComAN far below Section IV on EMNIST).

## P — further compliant ideas, pre-registered 2026-10-23 (before running)
Base points: ComAN = the N final (dev 84.97, test 84.44); Section IV = the N-projection selection (novelty map +
consolidation ρ 0.6 τ 0.8 + `distinct`, his 76 originals; dev 85.65, test 83.64). Acceptance: lower 95 % CI bound of the
paired dev difference > −1 pp against the base point; ideas accepted alone are then combined (if the combination fails
the rule, the best single one). Each changed final gets ONE official test run (disclosed as a further use of the test).
- P1 two maps, one competition: the ComAN winner and the Section IV winner compete by their reaction normalised by the
  neuron's own mean reaction on its OWN training positives (intrinsic plasticity, Desai 1999; Axiom 3 kept); the larger
  normalised reaction wins. No other-class statistics, no tuning.
- P2 ComAN, recognition of an incomplete input (Def. 1 f ≥ τ; associative recognition): a missing attractor node costs
  NO_MATCH instead of IMPOSSIBLE (P2a); P2a + attractor allowed up to 1/τ = 1.25× the image complexity (P2b); P2b +
  raw-graph comparison when the critical-point reduction fails (P2c, run only if P2b is accepted).
- P3 Section IV, his two-level scheme inside H0: (a) parametric hyperedges = runs of constant turn sign along strokes
  (+ their end anchors); (b) ComAN-like parameters as synapses (junction angles, stroke tortuosity, normalised length).
- P4 Section IV with 60 originals per digit (MNIST; Theorem 1, convergence) — the selected configuration, measurement.
- P5 ComAN, his accumulating hypergraph instead of the chain: counters f over the examples aligned to the seed (first
  original), attractor = seed elements with f ≥ τ (τ 1.0 and 0.8), order-free by construction except the seed.
- P6 Section IV, competition as dynamics: the pairwise `distinct` rule iterated until one survivor, without the fixed
  0.9 × max co-activity threshold.
- P7 Section IV, attention as a sequence of fixations (§13): the fovea only at the first F anchors in a bottom-up order,
  F ∈ {1, 2, 3}.
- P8 word / scene context for I↔L — not run (next theory level; asked to the professor).

### P — ComAN and combination results on dev (`results_P.csv`; dumps `tests/_isl/coman/p*`)
Redeployed classification (new per-message flags `concept_node_insert_cost`, `eligibility_slack`; defaults
unchanged): regression check, filter 110 with the N final config 77.81 vs 77.91 before (noise).
| check | dev | Δ vs base (95 % CI) | p | decision |
|---|---|---|---|---|
| P2a missing attractor node costs NO_MATCH (not IMPOSSIBLE) | 84.82 | −0.15 (−0.71 … +0.41) vs N final 84.97 | 0.73 | no effect |
| P2b + attractor up to 1.25 × the image complexity | 84.82 | −0.15 (−0.71 … +0.41) | 0.73 | no effect |
| P2c + raw-graph comparison when the reduction fails (200-image screen, filter 110) | 73.50 vs 73.00 | +1 image | — | no effect → not run in full |
| P1 two maps, one competition (winners compete by reaction / own-positive mean) | 85.32 | vs Section IV final (86.02): −0.70 (−2.44 … +1.04); vs ComAN +0.35 (+0.09 … +0.61) | 0.46 / 0.016 | rejected (below the better single map) |
P1 reading: the two maps are right on 93.5 % of dev between them, but the self-normalised reaction does not pick the
right map; an arbiter that does would have to be fitted on other classes' images (observer) — not done.
P2 reading: even when the attractor may be partially present, the GED similarity of a partial embedding stays below
the fully embedded competitors; the incomplete-input problem of ComAN is not solved at the cost level.
| P5 accumulating hypergraph (seed = first original, counters f, glue by the seed's structure — the gluing rule changed post-hoc, see the merged lab_P_coman_fold notes), τ 1.0 | 76.10 | −8.87 (−10.25 … −7.48) | 3e-38 | rejected |
| P5 the same, τ 0.8 | 76.95 | −8.02 (−9.40 … −6.64) | 2e-31 | rejected |
P5 reading: counted against one seed, the attractor is order-free for a fixed seed (39 / 39 identical over 3 orders)
but depends on the seed (10–13 / 39 identical with the second original); at τ 1.0 several attractors shrink to 1–3
nodes (4_1: the start point only) and fit everything, at τ 0.8 they are richer but stop embedding in most images
(top-3 drops to 84.4). His chain, for all its order dependence, gives the better ComAN concepts.

<!-- merged from lab_P_coman_fold.md (parallel offline track, P5) -->
#### P5 — ComAN concepts by his accumulating hypergraph instead of the chain (pre-registered 2026-10-23, before running)
Variants (written before any fold): `coman_concepts.py fold --mode accumulate --tau {1.0, 0.8}` on the exported graphs of
his 13 subclasses (stems rule) at the filters 110 / 150 / 190 → sets A110ps1 / A150ps1 / A190ps1 (τ 1.0) and
A110ps8 / A150ps8 / A190ps8 (τ 0.8), written to Neo4j INACTIVE. Design:
- seed = the first original of the subclass (sorted names, files without `_aug`); start point as in the chain
  (probe._determine_start_point over all graphs; graphs without it dropped); graphs analysed as in the chain;
- for every other example k: M_k = find_max_common_minor(seed, G_k) (result nodes keyed by the seed's node ids);
  a failure or an empty minor = not absorbed (counted);
- counters over the absorbed examples: f(n) for seed nodes, f(e) for node pairs that are edges of M_k (seed-id space;
  a pair may be a contracted seed path — the glue); properties of a kept node = the concept creator's merge_values over
  all M_k that contain it (min / max as default); labels = intersection over those M_k;
- attractor = nodes with f ≥ τ, edges with f ≥ τ between kept nodes, the connected component of the StartPoint;
  rule 1: fewer than 2 originals absorbed → not written;
- Theorem 2: identical attractor for 3 presentation orders of the non-seed examples (fixed seed) — expected by
  construction; separately the second original as seed.
Comparison per subclass with the chain sets D110ps / D150ps / D190ps. The live dev evaluation is done by the main thread.

#### Results (2026-10-23) — sets written to Neo4j INACTIVE (`concept_kind='coman_off'`, `coman_set=<name>`), JSON in `tests/_isl/coman_sets/`
Code: `notes/scripts_isl/coman_concepts.py fold --mode accumulate --taus 1.0,0.8 --orders 3 --write` (functions
`align_to_seed`, `accumulate`, `fold_accumulate`); test `unit_tests/test_coman.py::test_accumulate_fold_is_order_free_and_connected`.
Verified in `synced_graph_algorithm.py`: every node of a minor M_k carries the concept-side (seed) id — the counters
need no matching step.

**Change after the first build (post-hoc, disclosed).** As pre-registered, the edges were counted over the minors'
edges. But a minor's edges are contracted paths that differ from example to example, so almost no edge reached f = 1.
The attractor fell apart, and the StartPoint component kept 1–2 nodes: 7_1, 3_1, 5_1, 2_1, 4_1 at the 110 filter,
τ 1.0 (column "first build" below; JSON `A*_edgef.json`, not written to Neo4j). The written sets glue the kept nodes
with the seed's own structure, contracted over the removed nodes (a removed node between two others becomes an edge
joining them — an edge contraction, so the attractor is a minor of the seed). Node counters and τ are unchanged.

Written: **A110ps1, A110ps8, A150ps1, A150ps8** (13 / 13 each), **A190ps1, A190ps8** (12 / 13; 8_1 at 190 absorbed
only 1 original → not written, rule 1).

| filter | subclass | chain nodes/edges | chain absorbed (originals) | accumulate τ 1.0 | accumulate τ 0.8 | accumulate absorbed (originals) | first build τ 1.0 (edge counter) | 2nd seed isomorphic τ 1.0 / 0.8 | 3 orders identical |
|---|---|---|---|---|---|---|---|---|---|
| 110 | 0_1 | 10/10 | 32 (3) | 5/5 | 10/10 | 32 (3) | 1/0 | False / False | True |
| 110 | 1_1 | 7/6 | 33 (3) | 7/6 | 7/6 | 33 (3) | 7/6 | True / True | True |
| 110 | 1_3 | 3/2 | 44 (4) | 3/2 | 3/2 | 44 (4) | 3/2 | True / True | True |
| 110 | 2_1 | 7/6 | 66 (6) | 6/5 | 9/8 | 66 (6) | 1/0 | False / False | True |
| 110 | 2_2 | 10/10 | 33 (3) | 10/10 | 14/14 | 33 (3) | 2/1 | False / False | True |
| 110 | 3_1 | 11/10 | 36 (6) | 7/6 | 14/13 | 36 (6) | 1/0 | False / False | True |
| 110 | 4_1 | 3/2 | 46 (4) | 1/0 | 7/6 | 44 (4) | 1/0 | False / False | True |
| 110 | 4_2 | 9/8 | 65 (6) | 9/8 | 9/8 | 65 (6) | 9/8 | True / True | True |
| 110 | 5_1 | 9/8 | 66 (6) | 3/2 | 9/8 | 66 (6) | 1/0 | False / False | True |
| 110 | 6_1 | 10/10 | 77 (7) | 10/10 | 11/11 | 77 (7) | 2/1 | True / False | True |
| 110 | 7_1 | 5/4 | 99 (9) | 5/4 | 5/4 | 99 (9) | 1/0 | False / True | True |
| 110 | 8_1 | 13/14 | 87 (8) | 12/13 | 15/16 | 87 (8) | 12/12 | True / True | True |
| 110 | 9_2 | 8/8 | 88 (8) | 4/3 | 10/10 | 88 (8) | 4/3 | False / False | True |
| 150 | 0_1 | 12/12 | 33 (3) | 12/12 | 12/12 | 33 (3) | 12/12 | False / False | True |
| 150 | 1_1 | 7/6 | 33 (3) | 7/6 | 7/6 | 33 (3) | 7/6 | True / True | True |
| 150 | 1_3 | 3/2 | 44 (4) | 3/2 | 3/2 | 44 (4) | 3/2 | True / True | True |
| 150 | 2_1 | 7/6 | 66 (6) | 7/6 | 9/8 | 66 (6) | 2/1 | False / False | True |
| 150 | 2_2 | 12/12 | 33 (3) | 12/12 | 14/14 | 33 (3) | 12/11 | False / False | True |
| 150 | 3_1 | 11/10 | 36 (6) | 6/5 | 13/12 | 36 (6) | 1/0 | False / False | True |
| 150 | 4_1 | 8/8 | 77 (7) | 5/5 | 8/8 | 77 (7) | 5/4 | False / True | True |
| 150 | 4_2 | 9/8 | 65 (6) | 9/8 | 9/8 | 65 (6) | 9/8 | False / False | True |
| 150 | 5_1 | 9/8 | 66 (6) | 3/2 | 13/12 | 66 (6) | 2/1 | False / True | True |
| 150 | 6_1 | 10/10 | 77 (7) | 10/10 | 12/12 | 77 (7) | 2/1 | False / True | True |
| 150 | 7_1 | 5/4 | 99 (9) | 5/4 | 5/4 | 99 (9) | 1/0 | False / False | True |
| 150 | 8_1 | 11/12 | 88 (8) | 9/8 | 15/14 | 88 (8) | 3/2 | False / False | True |
| 150 | 9_2 | 8/8 | 88 (8) | 5/5 | 11/11 | 88 (8) | 5/4 | False / False | True |
| 190 | 0_1 | 12/12 | 33 (3) | 12/12 | 12/12 | 33 (3) | 12/12 | False / False | True |
| 190 | 1_1 | 7/6 | 33 (3) | 7/6 | 7/6 | 33 (3) | 7/6 | True / True | True |
| 190 | 1_3 | 3/2 | 44 (4) | 3/2 | 3/2 | 44 (4) | 3/2 | True / True | True |
| 190 | 2_1 | 7/6 | 66 (6) | 7/6 | 7/6 | 66 (6) | 7/6 | False / False | True |
| 190 | 2_2 | 14/14 | 32 (3) | 14/14 | 14/14 | 32 (3) | 14/14 | False / False | True |
| 190 | 3_1 | 9/8 | 36 (6) | 8/7 | 15/14 | 36 (6) | 1/0 | False / True | True |
| 190 | 4_1 | 3/2 | 54 (4) | 3/2 | 8/8 | 77 (7) | 3/2 | False / False | True |
| 190 | 4_2 | 9/8 | 65 (6) | 9/8 | 9/8 | 65 (6) | 9/8 | False / False | True |
| 190 | 5_1 | 9/8 | 66 (6) | 3/2 | 8/7 | 66 (6) | 1/0 | False / False | True |
| 190 | 6_1 | 10/10 | 77 (7) | 10/10 | 11/11 | 77 (7) | 2/1 | True / False | True |
| 190 | 7_1 | 5/4 | 99 (9) | 3/2 | 5/4 | 99 (9) | 1/0 | False / False | True |
| 190 | 8_1 | 3/2 | 16 (2) | 18/18 | 18/18 | 3 (1) | 18/17 | False / False | True |
| 190 | 9_2 | 8/8 | 88 (8) | 4/3 | 11/11 | 88 (8) | 4/3 | False / False | True |

Summary: 3 orders identical in 39 / 39; second seed isomorphic τ 1.0 10 / 39, τ 0.8 13 / 39.

Reading:
- **Absorption** equals the chain or is larger: 4_1 at 190 absorbs 77 examples vs 54. Every example is compared with the
  seed, not with a shrinking concept. Exception: 8_1 at 190 absorbs 3 (chain 16, 2 originals); the seed's 190 skeleton
  is unusual.
- **τ 1.0** is often smaller than the chain: 5_1 3 / 2 vs 9 / 8, 9_2 4 / 3 vs 8 / 8, 4_1 at 110 **1 / 0** (StartPoint
  only, a degenerate attractor that would match any image). **τ 0.8** is equal to or richer than the chain (3_1 14 / 13,
  8_1 15 / 16).
- **Theorem 2.** With the seed fixed, all 39 attractors are identical in 3 presentation orders (by construction: each
  example meets the seed, not the running concept). With the second original as seed, the attractor is isomorphic in
  only 10 / 39 (τ 1.0) and 13 / 39 (τ 0.8). The order dependence of the chain is replaced by a dependence on the seed.
- **For the live evaluation (main thread)**: candidate sets {A110ps1, A150ps1, A190ps1} (τ 1.0) and {A110ps8,
  A150ps8, A190ps8} (τ 0.8), each as a drop-in replacement of {D110ps, D150ps, D190ps} with the N final readout. The
  1-node 4_1 in A110ps1 is a known risk.

<!-- merged from lab_P_projection.md (parallel offline track: P3 / P4 / P6 / P7 and the P1 dumps) -->
#### P-projection — Section IV ideas P3 / P4 / P6 / P7 and the P1 dumps — variants restated 2026-10-23 (before running)

Pre-registration in `lab_log.md` (section P); this file restates the exact variants before any run. Code:
`notes/scripts_isl/isl_sim.py` (new cfg keys, defaults unchanged), driver `notes/scripts_isl/isl_projection_p.py`,
CSV `results_P_projection.csv`, dumps `tests/_isl/P_*.jsonl`, `tests/_isl/P1_projection_*.jsonl`.

**Base** = the N-projection selection: `best2` detector and H0 (overlapping fields, channels t110r / t150r / t190r /
t150rf with MAX, chains, fovea, wide-augmentation training channels), novelty map + consolidation (`min_originals` 2),
ρ 0.6, τ 0.8, competition `distinct`; his 76 originals (`base76`); dev `dev` (1 996). Every variant: 3 presentation
orders on dev (mean ± sd); acceptance = paired dev Δ (order 0 vs the base's order 0) with the lower 95 % CI bound
> −1 pp. Variants accepted alone are combined; if the combination fails the rule, the best single one.

- **P3 his two-level scheme inside H0** (new synapse families):
  - **P3a `runs`**: maximal runs along each traversal path where the signed turn keeps one sign (threshold 20°,
    `isl_2l.build(…, "sign")`, capture point = top-most end point) → relational synapse `RN` (run class L / R / 0,
    chord orientation 1 / 4 / 8 sectors, length class 1 / 2 / 4, total-turning class 1 / 2 / 4, mid-point cell
    1 / 2×2 / 4×4) — counted as STRUCTURAL; the run-end anchors that are not end points / junctions (type B, breaks inside a
    stroke) as point synapses `B` (position 1 / 2×2 / 4×4) — PARAMETRIC (point) part.
  - **P3b `comanfeat`**: ComAN-like parameters as synapses, all PARAMETRIC: per stroke `RT` (stroke type) ×
    tortuosity = path length / chord (1 | <1.1, ≥1.1 | <1.05, 1.05–1.2, 1.2–1.5, ≥1.5) × normalised length = length /
    the image's longest stroke (1 / 2 / 4 equal bins); per junction `JA` × min / max / mean angle between consecutive
    branches (1 | <90, ≥90 | <45, 45–90, 90–135, ≥135) × position (1 / 2×2).
  - each alone, then P3a + P3b if both accepted.
- **P6 competition as dynamics, no fixed 0.9 × max threshold**:
  - (i) `distinct_iter` (as specified by the main thread): all neurons with a positive response start active; in each
    round an active neuron is inhibited if some active neuron beats it by the pairwise distinct-evidence rule AND has
    a larger scalar response; stop when one survives, else argmax. NOTE (before running): the strongest neuron can
    never be inhibited under this conjunction, so the rule returns the argmax by construction — run as a check.
  - (i') `distinct_iter_free`: the same iteration with the distinct-evidence rule only (no scalar condition); a
    cycle (everyone inhibited) or several survivors → argmax among the last survivors.
  - (ii) `distinct_pool`: co-active = response above the mean response of the whole competing pool (divisive pool,
    no constant) ⚠️, then the existing `distinct` rule.
- **P7 sequential fixations (§13)**: the fovea keys (position 8×8, direction 16) only at the points within 0.03 (unit
  frame) of the first F anchors of the bottom-up traversal (`isl_2l.build` order: capture point = top-most end point,
  then the depth-first traversal), F ∈ {1, 2, 3} (instead of at every critical point).
- **P4 measurement (Theorem 1)**: the base configuration trained on `cand60:60` (60 originals per digit) — dev 1 order,
  official test `mtest` ONCE, census.
- **Final** = base + accepted (rule above) → official MNIST test `mtest` ONCE (all / `complete` / `incomplete`, top-3,
  census, McNemar vs `tests/_isl/N_projection_test.jsonl` and vs ComAN as is `tests/_isl/coman_mnist_all.jsonl`);
  if the final differs from the base, also EMNIST 10 per letter (`ecand60:10`, ρ 0.6): edev 1 order + `etest` ONCE.
- **P1 dumps** (final configuration, order 0) `tests/_isl/P1_projection_dev.jsonl`, `tests/_isl/P1_projection_mtest.jsonl`,
  one row per image: `stem`, `true`, `pred`, `winner` (neuron index), `cls_win`, `r` (winner's scalar response,
  readout c), `mu` (the winner's own-positive mean response = mean over the families it absorbed of its readout-c
  response to that family's stimulus), `norm` = r / mu, `class_best` = {class: [r, mu, neuron]} of the best-responding
  neuron of every class.

#### Results on dev (`results_P_projection.csv`, log `tests/_isl/P_projection_dev.log`; 3 orders, paired test on order 0)

| variant | dev top-1 (± sd) | top-3 | competing neurons | Δ order 0 vs base (95 % CI) | McNemar p | decision |
|---|---|---|---|---|---|---|
| base (N selection) — reproduces the N run exactly | 85.65 ± 0.96 | 93.97 | 15.7 (92.5 % of originals) | — | — | base |
| P3a runs (parametric hyperedges + break anchors) | 85.00 ± 0.31 | 93.72 | 16.0 | +0.10 (−0.65 … +0.85) | 0.9 | accepted (non-inferior) |
| P3b comanfeat (tortuosity, normalised length, junction angles) | 85.67 ± 0.98 | 94.02 | 15.7 | −0.05 (−0.31 … +0.21) | 1.0 | accepted (non-inferior) |
| P6i distinct_iter (with the "larger response" condition) | 83.27 ± 1.11 | 93.42 | 15.7 | −2.71 (−3.90 … −1.51) | 1e-5 | rejected — it is the argmax, as stated before running |
| **P6i' distinct_iter_free** (iterated, no threshold) | **86.60 ± 0.32** | 95.26 | 15.7 | **+1.70 (+0.93 … +2.47)** | 2e-5 | **accepted** |
| P6ii distinct_pool (above the pool mean) | 86.35 ± 0.31 | 95.01 | 15.7 | +1.45 (+0.73 … +2.18) | 1e-4 | accepted |
| P7 fixations F = 1 | 85.70 ± 0.94 | 94.02 | 14.3 | +0.05 (−0.90 … +1.00) | 1.0 | accepted (non-inferior) |
| P7 fixations F = 2 | 85.69 ± 1.11 | 93.96 | 14.3 | −0.25 (−1.22 … +0.72) | 0.68 | rejected |
| P7 fixations F = 3 | 85.54 ± 1.10 | 93.97 | 14.3 | −0.45 (−1.40 … +0.50) | 0.41 | rejected |
| **combination** (rule: all accepted; one competition rule = the better accepted, `distinct_iter_free`; F = 1): runs + comanfeat + distinct_iter_free + fixations 1 | 86.19 ± 0.27 | 95.27 | 14.3 (93.0 %) | +1.55 (+0.46 … +2.65) | 0.007 | **accepted → FINAL** |

Reading: his point 3 as a dynamic competition without the fixed co-activity threshold is the gain (+1.7 alone; the
iteration with the "larger response" condition collapses to the argmax, as predicted). The two-level scheme inside H0
(runs, break anchors) and the ComAN-like parameters are neutral on dev; one sequential fixation equals fixating every
anchor, two or three are slightly worse. The combination passes the rule (+1.55) and is the final by the declared rule,
although `distinct_iter_free` alone is higher (86.60 vs 86.19, not tested against each other — reported, not selected).

#### Final configuration — official MNIST test, ONE run (dump `tests/_isl/P_final_test.jsonl`, log `tests/_isl/P_projection_final.log`)
Final = base + runs + comanfeat + `distinct_iter_free` + fixations 1 (order 0: 20 neurons, 15 compete, 93.4 % of the
originals inside them, every competing neuron ≥ 2 originals). P1 dumps written (`P1_projection_dev.jsonl` dev top-1
86.02; `P1_projection_mtest.jsonl`).

| official test | P final | N-projection (`N_projection_test.jsonl`) | Δ vs N (95 % CI), p | ComAN as is | Δ vs ComAN (95 % CI), p |
|---|---|---|---|---|---|
| all 10 000 (top-3) | **85.64** (94.89) | 83.64 | +2.00 (+1.55 … +2.45), 1.1e-18 | 82.24 | +3.40 (+2.54 … +4.26), 1.4e-14 |
| `complete` 8 708 | 88.15 (94.96) | 85.77 | +2.38 (+1.94 … +2.81), 3.1e-27 | 90.89 | −2.74 (−3.54 … −1.95), 1.5e-11 |
| `incomplete` 1 290 | 68.76 (94.42) | 69.30 | −0.54 (−2.33 … +1.25), 0.61 | 23.95 | +44.81 (+41.62 … +47.99), 6e-123 |

Per digit: 0 91.9, 1 87.4, 2 75.4, 3 85.7, 4 95.0, 5 89.6, 6 87.8, **7 74.3** (N: 60.5), 8 89.9, 9 80.7.

#### Final configuration on EMNIST, 10 per letter (ρ 0.6; dump `tests/_isl/P_final_etest.jsonl`, log `tests/_isl/P_projection_emnist.log`)
edev (1 order) **71.04** (top-3 86.69; O1 selected 70.58); official test, ONE run: **69.57** (top-3 86.38; I + L 72.30;
O1 70.04 / 86.18 / 72.74); 56 of 109 neurons compete (79.6 % of the originals, min 2). On EMNIST the P additions are
neutral (−0.47 pp on the test vs O1).

#### P4 — the base configuration with 60 originals per digit (Theorem 1; dump `tests/_isl/P_p4_test.jsonl`, log `tests/_isl/P_projection_p4.log`)
dev (1 order) **92.89** (top-3 98.25); 69 neurons, 55 compete (97.7 % of the originals inside them, min 2 originals).
Official MNIST test, ONE run: **92.77** (top-3 98.42) — `complete` **94.59**, `incomplete` **80.47**; vs ComAN as is
+10.53 (+9.74 … +11.32), p 1e-149 (complete +3.70, p 1e-25); vs N-projection (76 originals) +9.13. Per digit: 0 95.0,
1 94.1, 2 88.4, 3 93.7, 4 94.5, 5 95.0, 6 92.1, 7 93.2, 8 90.0, 9 92.0. With 60 uncurated originals per digit the
compliant model (every competing attractor a reduction over ≥ 2 originals) exceeds ComAN on every subset; the
non-compliant `best2` with 60 per digit had 94.50 / 95.61 — the price of rule 1 here is ≈ 1.7 pp.

### P9 — the Section IV final with the first 10 originals per digit (pre-registered 2026-10-24, before running)
The user asked for a strict few-shot point instead of 60 per digit: the P final configuration trained on `cand60:10`
(the first 10 official-train images of each digit, no selection, 10 augmentations each), dev 1 order, official test
`mtest` ONCE (all / complete / incomplete, census, McNemar vs ComAN as is).
P9 result: dev (1 order) **85.47** (top-3 93.99); census 29 neurons, 18 compete (89.0 % of the originals, min 2).
Official test, ONE run (`tests/_isl/P_p10_test.jsonl`): all **84.95** (top-3 93.85), complete 87.44, incomplete 68.14;
vs ComAN as is +2.71 (+1.81 … +3.61), p 4e-9 (complete −3.46, incomplete +44.19); vs N-projection +1.31, p 0.001.
Per digit: 0 96.2, 1 91.0, 2 79.4, 3 92.1, 4 95.0, 5 70.1, 6 89.0, 7 72.2, 8 72.7, 9 90.1. The report now shows 10 per
class only (the 60-per-class numbers stay in this log: P4 92.77, O1 EMNIST 79.91).

## Q — ComAN, final push (pre-registered 2026-10-24, before running)
Baseline: ComAN as is (82.24 test). Base point for acceptance: the N final (dev 84.97, test 84.44). Same rule (lower
95 % CI bound of the paired dev difference > −1 pp); accepted items combined; ONE official test per new final.
- Q1 subclasses from the novelty map (Theorem 3) instead of his 13 hand subclasses: the first 10 originals per digit
  (no selection), grouped by the Section IV map (P final config, order 0; only groups with ≥ 2 originals), each group =
  its originals + 10 augmentations (rotation ±10°, shift ±3 px), folded with his chain at 110 / 150 / 190 with the stems
  rule (rule 1 enforced); the N final readout.
- Q2 parametric layer read by the soma (his point 3 / Table 2; the core of our band system without its observer parts):
  a holistic shape descriptor of the image (orientation mass of the dense centre line, 2×2 and 3×3 grids × 4 bins);
  per concept, bands over its OWN training images only (shortest interval with ≥ 0.8 of the values, Def. 1); parametric
  reaction = mean over dimensions of 1 inside the band, falling linearly to 0 one band-width outside; reaction = ComAN
  reaction + β · parametric, β ∈ {0, 0.1, 0.2, 0.3, 0.5} chosen on dev. Structure still gates (a concept that does not
  embed cannot win).
- Q3 his point-3 competition inside ComAN (pairwise distinctive evidence on the GED correspondences, iterated, no
  threshold) — only if time allows (needs the edit paths from the classifier).
- Q4 topology as a hard structural condition: a concept competes only if the image's number of independent cycles
  (and, variant, of endpoints) lies within the range seen on the concept's own training images.

### Q — results (2026-10-24)
| check | dev | Δ vs N final (95 % CI) | p | decision |
|---|---|---|---|---|
| Q1 novelty-map subclasses (first 10 per digit; 18 groups → 17 concepts per filter, 2_1 excluded by rule 1) | 81.26 | −3.71 (−5.07 … −2.35) | 1e-7 | rejected |
| Q2 parametric layer, β 0.1 / 0.2 / 0.3 / **0.5** | 85.62 / 85.72 / 86.07 / **86.27** | +1.30 (+0.44 … +2.17) for β 0.5 | 0.004 | **accepted (β 0.5)** |
| Q4a / Q4b topology gate (cycles; cycles + endpoints) | 83.32 / 82.46 | −1.65 / −2.51 | < 1e-7 | rejected |
Q3 not run (time). Final ComAN = N final + Q2 (β 0.5). Official test, ONE run (offline from the N final test dumps;
`tests/_isl/Q_param_test.jsonl`): **85.44** (top-3 92.56), complete **92.90**, incomplete 35.12; vs ComAN as is +3.20
(+2.57 … +3.83), p 2e-23; vs N final +1.00 (+0.60 … +1.40), p 1e-6. Section IV final − this: +0.20 (−0.56 … +0.96),
p 0.62 (complete −4.75, incomplete +33.64). Third use of the test for ComAN (three pre-frozen configurations).

<!-- merged from lab_Q_param.md (parallel offline track, Q2 / Q4) -->
#### Q2 / Q4 — ComAN parametric layer and topology gate, offline (variants restated 2026-10-24, before running)

Base point: the N final ComAN (his 13 subclasses refolded as D110ps / D150ps / D190ps, 4 recognition filters, stems
rule, ε 1, soft ramp span 4, 28 features, MAX over filters, λ 0.05): dev 84.97, official test 84.44. Everything is
computed offline from the existing per-image dumps (dev `tests/_isl/coman/n_comb_*.jsonl`, test
`tests/_isl/coman/final2_test_*.jsonl`) — no live run. Concept reaction r(image, c) = MAX over the filters of the GED
similarity among `minor` entries + 0.05 · log2(cc) (as `coman_rerank.py`). A concept's own subclass = `cid.split('s')[0]`
(e.g. `2_1sD110ps` → `2_1`); its own training images = `tests/_isl_train/<subclass>/*.png` (originals + his
augmentations). Only own positives are used (Axiom 3); nothing uses other classes.

Descriptors (detector D as at recognition: production skeletonisation, binarisation 110, simplification 4.55, stems
rule, fixed threshold): the orientation mass of the dense centre line (`dense_features.dense_representation`, `orient`:
2×2 and 3×3 grids × 4 orientation bins = 52 dims); from the simplified skeleton graph after the junction merge: the
number of independent cycles (E − V + components) and of endpoints (degree 1). Cached in `tests/_isl/dense/<dir>.jsonl`.

- **Q2** per subclass and dimension, band = the shortest interval holding ≥ 0.8 of its own training images' values
  (Def. 1); width floored at 0.01. Parametric reaction p(image, c) = mean over dimensions of 1 inside the band, else
  max(0, 1 − distance past the edge / width). Reaction = r + β · p, only for concepts that matched as a minor
  (structure still gates). β ∈ {0, 0.1, 0.2, 0.3, 0.5}; the best on dev. An image without a descriptor gets p = 0 for
  every concept.
- **Q4a** a concept competes only if the image's cycle count lies in [min, max] of its own training images' cycle
  counts. **Q4b** also the endpoint count in [min, max]. If no concept survives, the ungated ranking is used.
- Acceptance (lab log rule): lower 95 % CI bound of the paired dev difference vs the N final > −1 pp (McNemar reported).
- Combination: Q2 at its best β with the better accepted Q4 variant (if only one kind is accepted, that one alone).
- The final: official test computed ONCE offline (all / `complete` / `incomplete`, top-3; McNemar vs ComAN as is and
  vs the N final test).

#### Results (2026-10-24; `notes/scripts_isl/coman_param_layer.py`, `results_Q_param.csv`, descriptors `tests/_isl/dense/`)
Descriptors: `_isl_train` 805, `mnist_dev` 1 996, `mnist_all` 10 000 images, all with a descriptor (≈ 1 min per 2 000
images with 6 processes). Dev (paired vs the N final, 84.97 / top-3 91.63):

| variant | dev top-1 | top-3 | Δ (95 % CI) | McNemar p | decision |
|---|---|---|---|---|---|
| Q2 β 0.1 | 85.62 | 91.98 | +0.65 (+0.18 … +1.12) | 0.011 | accepted |
| Q2 β 0.2 | 85.72 | 92.18 | +0.75 (+0.15 … +1.35) | 0.02 | accepted |
| Q2 β 0.3 | 86.07 | 92.28 | +1.10 (+0.40 … +1.81) | 0.003 | accepted |
| **Q2 β 0.5** | **86.27** | 92.99 | **+1.30 (+0.44 … +2.17)** | 0.004 | **accepted, best β** |
| Q4a cycles gate | 83.32 | 88.48 | −1.65 (−2.25 … −1.06) | 1e-8 | rejected |
| Q4b cycles + endpoints gate | 82.46 | 86.92 | −2.51 (−3.28 … −1.73) | 8e-11 | rejected |

Final = Q2 at β 0.5 (no Q4 accepted). β 0.5 is the edge of the pre-declared grid; the grid was not extended.
**Official MNIST test, computed ONCE offline** (`tests/_isl/Q_param_test.jsonl`):

| | top-1 | top-3 | vs ComAN as is (95 % CI), p | vs N final (95 % CI), p |
|---|---|---|---|---|
| all 10 000 | **85.44** | 92.56 | +3.20 (+2.57 … +3.83), 2e-23 | +1.00 (+0.60 … +1.40), 1e-6 |
| `complete` 8 708 | **92.90** | 98.09 | +2.01 (+1.36 … +2.66), 2e-9 | +0.31 (−0.08 … +0.70), 0.13 |
| `incomplete` 1 290 | 35.12 | 55.27 | +11.16 (+9.11 … +13.21), 9e-27 | +5.66 (+4.00 … +7.32), 2e-11 |

Reading: the parametric layer (a holistic orientation descriptor matched to each concept's own-positive bands, read by
the soma next to the GED structural reaction) adds +1.3 pp on dev and +1.0 pp on the test, mostly on broken strokes;
topology as a hard gate removes the true concept too often (training cycle ranges of a subclass are narrow).

## R — toward the band system's EMNIST level within the rules (pre-registered 2026-10-24, before running)
Reading of the band system's 84.6 % (memory / experiments/fewshot_band_concepts_2026-10): with 10 random originals per
letter its compliant core gave 69.2 %; the rest came from (a) a richer shape description (direction map, curvature,
end directions, dense centre-line orientation) ✅, (b) 32-anchor centre-line shape concepts ✅ as synapses, (c) the
skeleton committee ✅ (already in), (d) the round-2 re-rank ❌, (e) k-medoids selection of originals from 60 ❌, (f) one
leaf per original ❌, (g) deslant / moment normalisation ⚠️ (not run without the professor's consent).
Base: the Section IV P final (MNIST his 76 originals dev 86.19 / test 85.64; EMNIST first 10 per letter edev 71.04 /
test 69.57). Each alone on top of the base, on MNIST dev (3 orders) and EMNIST edev (1 order); acceptance = lower 95 %
CI of the paired difference > −1 pp on BOTH sets; accepted ones combined; ONE official test per set for the final
(MNIST mtest with his 76 originals and with the first 10 per digit; EMNIST etest with the first 10 per letter).
- R1 parametric layer read by the soma: dense centre-line orientation (2×2, 3×3 × 4 bins) + direction-map-like
  descriptors, bands over the neuron's OWN examples (originals + augmentations, shortest interval with ≥ 0.8),
  graded score; reaction = r + β·p, β ∈ {0.1, 0.2, 0.3, 0.5} on dev.
- R2 shape anchors as synapses: 32 centre-line points with their tangent orientation (cell × tangent bin, hierarchy).
- R4 sleep-like consolidation: after learning, neurons of a class whose attractors overlap (weighted Jaccard ≥ θ,
  θ ∈ {0.5, 0.7}) merge; the attractor is re-reduced over the joined originals (f ≥ τ).
- R5 homeostasis: each neuron's reaction divided by its mean reaction on its own positives (intrinsic plasticity).
- Side check (2026-10-24, dev only): the accepted Q2 parametric layer applied to ComAN on EMNIST (E110ps concepts, filters
  110 / 150 / 190): edev 53.35 → **56.69** with β 0.5 (+3.35, +2.12 … +4.58, p 1e-7); the Q4 gates are neutral there.
  No EMNIST test for ComAN (the dev level stays far below the Section IV model).

<!-- merged from lab_R.md (parallel offline track, section R) -->
#### R — Section IV toward the band system's EMNIST level within the rules — variants restated 2026-10-24 (before running)

Pre-registration: lab_log.md section R. Driver `notes/scripts_isl/isl_projection_r.py`; simulator hooks in
`notes/scripts_isl/isl_sim.py` behind new cfg keys only (`shape_anchors`, `param_beta`, `homeostasis`, `consolidate`
called by the driver), defaults unchanged.

**Base** = the Section IV P final (`tests/_isl/P_projection_state.json` changes on `isl_projection_p.BASE`: novelty map
+ consolidation ρ 0.6 τ 0.8, `distinct_iter_free` competition, runs + comanfeat, fixations 1, best2 channels).
Data: MNIST his 76 originals `base76`, dev `dev` (3 orders, paired test on order 0); EMNIST `ecand60:10`, `edev`
(1 order).

**Descriptors** (R1, R2): `dense_representation` of the dense centre line (orient 52 dims; 32 points + tangents), the
production skeletonization at a fixed threshold 110 / 4.55 with `bridge_protect_stems`, no thick-stroke rule. For the
training items the augmentation image is recomputed with `isl_cache.augment(img, crc32("<stem>:<j>"), wide=True)` —
the wide family of the best2 training channels — so the descriptor is taken from the same variant as the synapses.

**Variants** (each alone on top of the base):
- R1 parametric layer read by the soma, β ∈ {0.1, 0.2, 0.3, 0.5}: per neuron, bands over the orient vectors of its OWN
  absorbed families (originals + augmentations; shortest interval with ≥ 0.8 of the values, per dimension);
  p = mean over dims of 1 inside, falling linearly to 0 one band-width outside; reaction r' = r + β·p. The competition
  works on r': the pairwise distinctive-evidence comparison of `distinct_iter_free` adds β·p to each neuron's side
  (j inhibits i if ev(j, i) + β p_j > ev(i, j) + β p_i), the fallback order uses r'.
- R2 shape anchors as synapses: the 32 centre-line points → point synapses `SP` (position cell 1 / 2 / 4 × tangent
  orientation 1 / 2 / 4 / 8 at the hierarchy levels, overlapping fields as the base, multiplicity capped at 4 per cell);
  parametric part for the competition.
- R4 sleep-like consolidation after learning, θ ∈ {0.5, 0.7}: within a class, repeatedly merge the pair of neurons with
  the largest weighted Jaccard of attractors if ≥ θ; the merged attractor is re-reduced over the joined families
  (f ≥ τ).
- R5 homeostasis: each neuron's reaction multiplied by 1 / its mean reaction on its own positives (`own_mean`); the same
  gain scales its distinctive evidence in the competition.

**Acceptance**: paired lower 95 % CI > −1 pp vs the base on BOTH MNIST dev and EMNIST edev. **Combination**: one β and
one θ (the accepted one with the largest sum of Δ over both sets) + R2 / R5 if accepted; the combination must pass the
same rule on both sets, else the best single accepted variant. **Official tests ONCE** for the final: MNIST `mtest` with
`base76` and with `cand60:10`, EMNIST `etest` with `ecand60:10` (all / complete / incomplete, top-3, I+L, census,
McNemar vs the P final dumps and vs ComAN as is).

#### Results on dev (`results_R.csv`; logs `tests/_isl/R_dev_{mnist,emnist}.log`, `R_combine.log`)
Base reproduces the P final exactly: MNIST 86.19 ± 0.27 (3 orders; order 0 = 86.02), EMNIST 71.04. Δ = paired, order 0.
(Two runs show ~123 000 s: the laptop slept ~34 h in the middle; the numbers are unaffected.)

| variant | MNIST dev (± sd, 3 orders) | Δ MNIST (95 % CI) | EMNIST edev | Δ EMNIST (95 % CI) | decision |
|---|---|---|---|---|---|
| base (P final) | 86.19 ± 0.27 | — | 71.04 | — | base |
| R1 β 0.1 | 87.14 ± 0.25 | +1.15 (+0.61 … +1.70) | 71.04 | +0.00 (−0.51 … +0.51) | accepted |
| R1 β 0.2 | 87.44 ± 0.44 | +1.65 (+0.92 … +2.39) | 71.88 | +0.85 (+0.16 … +1.54) | accepted |
| **R1 β 0.3** | 88.13 ± 0.54 | +2.40 (+1.57 … +3.24) | 71.77 | +0.73 (−0.10 … +1.56) | accepted — chosen β (largest sum of Δ) |
| R1 β 0.5 | 88.66 ± 0.49 | +2.71 (+1.68 … +3.73) | 71.35 | +0.31 (−0.68 … +1.29) | accepted |
| **R2 shape anchors** | 87.96 ± 0.23 | +2.25 (+1.57 … +2.93) | 71.38 | +0.35 (−0.48 … +1.17) | accepted |
| R4 θ 0.5 | 86.07 ± 0.37 | −0.05 (−0.48 … +0.38) | 70.92 | −0.12 (−0.72 … +0.49) | accepted |
| **R4 θ 0.7** | 86.19 ± 0.27 | 0.00 | 71.04 | 0.00 | accepted — chosen θ (no pair reaches 0.7: a no-op here) |
| R5 homeostasis | 85.00 ± 0.41 | −0.95 (−1.85 … −0.06) | 68.73 | −2.31 (−3.27 … −1.35) | rejected |
| **combination R1 β 0.3 + R2 + R4 θ 0.7** | **89.11 ± 0.32** | **+3.41 (+2.43 … +4.39)**, p 5e-12 | **71.77** | +0.73 (−0.28 … +1.74), p 0.18 | **accepted → FINAL** |

Reading: the soma's parametric layer and the shape anchors carry on MNIST (+2.4 / +2.3 alone, +3.4 together); on EMNIST
both are small (+0.3 … +0.9). Homeostasis hurts on both. Sleep consolidation changes nothing measurable (θ 0.5 merges
a few neurons without effect; θ 0.7 merges none).

**Final frozen BEFORE the official tests**: P final + param_beta 0.3 + shape_anchors + sleep θ 0.7
(`tests/_isl/R_state.json`).

#### Official tests, ONE run each (dumps `tests/_isl/R_{mnist76,mnist10,emnist}_test.jsonl`, logs `tests/_isl/R_test_*.log`)
Census of the test models (order 0): MNIST his 76 — 21 neurons, 15 compete (92.1 % of the originals); MNIST first
10 per digit — 28 / 18 (90.0 %); EMNIST first 10 per letter — 102 / 55 (81.9 %); every competing neuron ≥ 2 originals.

| official test | R final | top-3 | vs P final (95 % CI), p | vs ComAN as is (95 % CI), p |
|---|---|---|---|---|
| MNIST, his 76 originals — all 10 000 | **88.59** | 96.12 | +2.95 (+2.53 … +3.37), 2e-44 | +6.35 (+5.52 … +7.18), 7e-51 |
| — `complete` 8 708 | 90.74 | 96.27 | +2.60 (+2.17 … +3.02), 3e-35 | −0.15 (−0.89 … +0.59), 0.72 |
| — `incomplete` 1 290 | 74.11 | 95.12 | +5.35 (+3.72 … +6.98), 1e-10 | +50.16 (+47.09 … +53.22), 8e-152 |
| MNIST, first 10 per digit — all 10 000 | **86.36** | 95.91 | +1.41 (+0.99 … +1.83), 6e-11 | +4.12 (+3.24 … +5.00), 4e-20 |
| — `complete` | 88.75 | 95.91 | +1.31 (+0.89 … +1.73), 1e-9 | −2.15 (−2.96 … −1.33), 3e-7 |
| — `incomplete` | 70.23 | 95.89 | +2.09 (+0.50 … +3.69), 0.013 | +46.28, 7e-134 |
| EMNIST, first 10 per letter — 20 800 | **71.33** | 87.52 | +1.76 (+1.39 … +2.13), 3e-20 | — |

EMNIST: I + L as one class 74.11; per letter weakest G 36, I 32, R 48, H 51, L 52, N 59; confusions I→L 400, G→Q 246,
L→I 178, Q→A 133, N→M 124, H→N 121, R→P 118, Y→X 116.

Reading: the soma's parametric layer (dense centre-line orientation with bands over the neuron's own examples) and the
32 shape anchors as synapses lift the Section IV model by +3 pp on MNIST (his 76 originals: 88.6 %, equal to ComAN as is
on `complete` and +6.4 on the whole test) but only +1.8 on EMNIST (71.3 %). The band system's 84.6 % on EMNIST is not
reached within the rules: what is left of the gap belongs to the parts excluded by the rules (the second round, the
selection of originals from 60, single-original leaves) and to the I↔L / G↔Q case collisions (≈ 4 pp).

Simplifications: descriptors from one detector channel (110, stems rule) instead of MAX over the filters; R2
multiplicity capped at 4 per cell; R4 θ 0.7 is a no-op on these data (kept by the rule).
R official tests, ONE run each (`tests/_isl/R_{mnist76,mnist10,emnist}_test.jsonl`): MNIST his 76 originals **88.59**
(top-3 96.12; complete 90.74, incomplete 74.11; vs ComAN as is +6.35, p 7e-51; vs the final ComAN 85.44 +3.15, p 2e-17);
MNIST first 10 per digit **86.36** (complete 88.75, incomplete 70.23; vs ComAN as is +4.12, p 4e-20); EMNIST first 10 per
letter **71.33** (top-3 87.52, I + L 74.11; macro precision 71.94, recall 71.33, F1 70.80; worst I, G, R).
Timing (EMNIST, one process, cached primitives): train 115.5 s for 260 originals × 11; recognition 266 ms / image;
detector (four skeletonisations) ≈ 139 ms / image; stored elements 256 587 (attractor synapses of 55 competing
neurons + band ends of the parametric layer).
