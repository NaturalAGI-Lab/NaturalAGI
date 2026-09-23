# Architecture Decision Records

New entries appended using the format in [ADR.template.md](ADR.template.md).

---

## ADR-001: Median Graph concept formation — experiment and revert

**Date**: 2026-03-11 to 2026-03-18 | **Status**: Reverted

**Context**: The pairwise concept formation (`CriticalPointConceptService`) was order-dependent and lossy. The Generalized Median Graph (Boria et al. 2019) was implemented as a replacement — it considers all training graphs simultaneously, minimizing total GED. Extended with GMG-BCU node deletion/insertion (Blumenthal et al. 2021). Tested across 6 classification runs.

**Result**: Best accuracy **55.75%** vs **73.0% baseline** (-17.25pp). Root causes: (1) low-complexity concepts act as GED attractors, (2) GED matchings on cyclic graphs are inconsistent — breaking edge voting for closed-structure digits

**Decision**: Revert to critical-point reduction. Full report: `experiments/median-graph-concept-formation/`.

---

## ADR-002: Fully-compliant Parzhyn energy model — write-time h_k, simplified h_c, scale-strength weighting

**Date**: 2026-04-17 | **Status**: Accepted

**Context**: The classifier previously scored ~65% on compliance against Parzhyn's energy theory (Parzhyn, "Architecture of Information", arxiv:2503.21794 §6.1–6.2; Parzhyn, Lapin, Bokhan, "A New Approach to Building Energy Models of Neural Networks", *Advanced Information Systems* 2025, formulas 36 and 39). Three critical violations: (1) CMA-ES Optuna tuned `PROPERTY_NORMALIZERS` — a "meta-Maxwell's Demon" that made comparison semantics dependent on MNIST statistics rather than each parameter's own definition; (2) Neo4j stored raw measurable parameters `k` instead of internal energy `u_k = h_k(k)`, so the classifier had to carry hidden per-feature divisors (`PROPERTY_NORMALIZERS`, `FEATURE_MAX_RANGES`); (3) uniform `1/N` feature weighting ignored Parzhyn's scale-strength hierarchy (ratio > interval > ordinal > nominal). A 200-trial CMA-ES study on the normalizer surface produced only 4.46pp total spread, so removing the knobs carried low accuracy risk relative to the compliance gain.

**Decision**: Apply `h_k` at extraction (not comparison), simplify `h_c` to `min(|a - b|, 1.0)`, introduce an explicit `SCALE_STRENGTH` multiplier in `_resolve_weight`, and make diagnostic weighting the sole weighting method. Concretely: new `common/common/feature_scales.py` holds per-feature transforms (angle → `v/180`, tortuosity → `1 - 1/v`, `cycle_count → v/(v+1)`, `node_degree → min(v,6)/6`, `neighbor_*_count → v/raw_node_degree`, `avg_neighbor_vector_length → min(v/(2√2), 1)`, eccentricity → `1 - 1/v`, identities elsewhere) plus a `SCALE_STRENGTH` dict (ratio=1.0, ordinal=0.6, nominal=0.4). Extractors (`structural_feature_analyzer`, `vector_angle_strategy`, `neighborhood_context_strategy`, `cycle_count_analyzer`) write `u_k ∈ [0, 1]` directly. `cost_functions.py` drops `PROPERTY_NORMALIZERS`, `FEATURE_MAX_RANGES`, `RANGE_PENALTY_FACTOR`. `_resolve_weight` becomes `strength / (width + epsilon)` for numerics, `strength` for categoricals. All CMA-ES/Optuna normalizer-tuning scaffolding is removed.

**Consequences**: +30pp on the compliance-audit score (65% → ~95%, the remaining gap is composition of `h_k ∘ h_c` vs. the paper's strict separation). Neo4j concepts are now canonical internal energy — one-time wipe + retrain required because old raw-value concepts are incompatible. Classifier has a single tuning knob (`DIAGNOSTIC_WEIGHT_EPSILON`, default **1.0** — see validation below) instead of 14 normalizers + epsilon + range_penalty_factor. Feature-weight semantics are defensible from Parzhyn Sec. 6.1: ratio features dominate ordinal/nominal by construction. Rollback is git revert plus Neo4j snapshot restore (`docker exec <neo4j> neo4j-admin dump/load`). Future features must declare h_k + scale type in `feature_scales.py` — a code-review gate enforced by the unit smoke test that checks every `FEATURE_TRANSFORMS` key has a matching `SCALE_STRENGTH` entry.

**Validation on 25% fold-1 (classes 0-9, ~2982 images)**:

| Config | Accuracy | Δ vs CMA-ES 79.85% | Notes |
|---|---|---|---|
| eps=0.1 (plan default) + hierarchy | 64.65% | −15.20pp | Over-weights ratio features (strength/0.1=10) |
| eps=1.055 (inherited CMA-ES value) + hierarchy | 73.08% | −6.77pp | Best accuracy, but `1.055` is from a 200-trial CMA-ES study — a small Maxwell's Demon |
| eps=1.055 + uniform SCALE_STRENGTH=1.0 | 72.40% | −7.45pp | Confirms hierarchy marginally helps |
| **eps=1.0 (scale-symmetric, chosen) + hierarchy** | **70.79%** | **−9.06pp** | No statistical dependence on any training corpus |

**Why `eps=1.0` was chosen over the higher-accuracy `1.055`**: when both feature widths and `u_k` values share the [0, 1] scale, `eps=1.0` is the unique value where the diagnostic-weight scale (`strength / (width + ε)`) matches the value scale — a zero-width concept gets at most 2× the weight of a maximum-width one. It is a scale-symmetry argument, not an empirical fit. The inherited `1.055` carried a residual (single-scalar) dependence on MNIST via the prior CMA-ES study, which is exactly the kind of statistical tuning Parzhyn Sec. 5 calls pseudo-energy. The 2.29pp cost is the price of theoretical cleanliness.

**On the `h_k` transforms and `SCALE_STRENGTH` hierarchy — are they also Maxwell's Demon?** No: each `h_k` is derivable from the parameter's definition alone (e.g. `angle/180` — 180 is the range of `acos`; `1 - 1/v` for tortuosity — saturating map because tortuosity ≥ 1 by definition). They do not change when the dataset changes. `SCALE_STRENGTH` values (1.0 / 0.6 / 0.4) encode Parzhyn's qualitative hierarchy from Sec. 6.1 and were set axiomatically, not fit to data. The accuracy cost versus CMA-ES is the genuine price of removing the demon — not an artefact of bad defaults.

---

## ADR-003: Streamlit concept-formation visualizer — fresh-subprocess runner with a plain-dict payload boundary

**Date**: 2026-06-12 | **Status**: Accepted

**Context**: Debugging concept formation (range explosions, mismatched merges) required re-running `probe_concept_formation.py` and reading JSONL events by hand. A UI was needed that re-runs formation on Neo4j debug sessions (uploaded via `train_mnist(..., with_concept_creation=False)`) and visualizes every merge step. Two design problems: (1) a long-lived Streamlit process caches imported modules, so edits to concept_creator source would silently not apply between runs (`importlib.reload` is unreliable across a package graph); (2) concept_creator objects (services, recorders) must not leak into the UI process.

**Decision**: The app (`src/concept_creator/visualization/formation_viz_app.py`, `make formation_viz`, port 8502) is UI-only and imports just `plotting.py`/`data.py`. Clicking "Run formation" spawns `formation_runner.py` in a fresh venv interpreter — the ONLY place concept-formation code is imported — which runs `create_concept_incrementally(debug_mode=True)` with the probe's `FormationRecorder`/`attach_instrumentation` and pickles a payload of plain dicts + nx node-link data only (enforced by a recursive plain-types test). Subprocess contract: `PROGRESS step=N` / `DONE steps=N verdict=X` on stdout, stderr to a log file (avoids pipe-buffer deadlock), payload via pickle (trusted local IPC only). Supporting fixes shipped with it: CC-16 (`debug_mode=True` no longer deletes sample data on merge failure, `critical_point_concept_service.py:129`) and a runner-side step advancer wrapping `find_max_common_minor` so Neo4j-mode events carry per-image step numbers like the offline path.

**Consequences**: Editing concept_creator code requires NO app restart (fresh subprocess per run picks it up); editing `plotting.py`/`data.py` does. The probe suite (`probes/instrumentation.py`, offline helpers, `seven_flipped` fixtures) became load-bearing test infrastructure for the viz suite (20 tests, incl. an end-to-end CLI contract test). The payload boundary means new visualizations can only use what the runner serializes — extending them means extending `build_payload`, not importing services. Known limits: `_sanitize` stringifies numpy arrays (e.g. `centroid`) and JSON round-trip turns int dict keys into strings; Plotly pair animation uses `redraw: False`, which may need `True` if Play appears inert in some browsers.

## ADR-004: Supervisor research program — user-run notebook over production code paths

**Date**: 2026-07-17 | **Status**: Accepted

**Context**: The supervisor requested, against the 91.13% baseline (`run_20260630_235356`): a visual post-mortem of the dominant 2→7 confusion (hypothesis: the "2" graph loses critical anchor points before reduction, so the more complex concept never wins WTA), plus six studies — other MNIST datasets (10k unfiltered, 60k train split filtered/unfiltered), sample-order dependence, sample-count dependence, augmentation, reduction-convergence steps, and concept parameter compression. Requirements: results must come from the production code paths (no re-implemented scoring), long/destructive runs must stay under user control, and retrains clear Neo4j (concept creation also deletes the training-session image graphs it consumed).

**Decision**: Ship the program as one user-run notebook `src/training/supervisor_experiments.ipynb` (kernel `natural-agi`) over a thin-cell/thick-module package `src/training/supervisor_experiments/` (`infra`, `postmortem`, `formation_lab`, `parameter_compression`, `convergence`, `order_dependence`, `sample_count`, `dataset_variants`, `tier_c`, `report`). Analyses run in three tiers: Tier A offline against Neo4j only (post-mortem via the production `ClassificationOrchestrator`; formation studies via the offline probe, extended with `--order-seed`, `--capture-failure`, per-merge `cpp_iterations` telemetry and a final `concept.json` dump); Tier B live-pipeline evaluations on untouched baseline concepts (`structure_filter`/`manifest_path`/path-template passthrough added to `run_experiment.py`; 60k train split built by `scripts/build_mnist_train_dataset.py` with the heuristic from `scripts/completeness_heuristic.py`); Tier C destructive retrains (`tier_c.py`) gated on a cold Neo4j volume backup and explicit `CONFIRM` variables, with subtractive augmentation conditions exploiting the discovery that `datasets/train/` is already augmented (~10 variants + original per source) and additive ones via `scripts/augment_train.py`. Production determinism fix: `_get_image_ids_for_session` gained `ORDER BY image_id` (the formation seed image was previously non-deterministic).

**Consequences**: The 2→7 mechanism is confirmed and quantified on all 111 misses: concept 2_2 (complexity 24) is excluded by the complexity pre-filter for 77.5% of them (median image complexity 21), and the surviving simplified 2_1 loses raw similarity to 7_1 by 0.14 on average — bucket C (λ-ranking) is empty, so the ranking prior is innocent; the root cause is loop destruction during binarization/thinning (visible in the construction-stage figures). Retrained concepts now depend on a deterministic sample order — any future retrain happens under `ORDER BY image_id`, which may change formed topologies versus historical arbitrary-order retrains (measured explicitly by the S2 study). Findings live in gitignored `researches/` (project convention); only code and the notebook are committed. `USE_ENERGY_MINIMIZATION` remains dead config; `src/samples_generator/` no longer exists and CLAUDE.md was corrected accordingly.
