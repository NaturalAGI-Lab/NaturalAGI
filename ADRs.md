# Architecture Decision Records

New entries appended using the format in [ADR.template.md](ADR.template.md).

---

## ADR-001: Fully-compliant Parzhyn energy model — write-time h_k, simplified h_c, scale-strength weighting

**Date**: 2026-04-17 | **Status**: Accepted

**Context**: The compliance audit in `researches/parzhyn-energy-scales-features.md` §15 scored our classifier at 65% against Parzhyn's energy theory (arxiv:2503.21794 §6.1-6.2, and Parzhyn/Lapin/Bokhan "A New Approach to Building Energy Models of Neural Networks", *Advanced Information Systems* 2025 — formulas 36 and 39). Three critical violations: (1) CMA-ES Optuna tuned `PROPERTY_NORMALIZERS` — a "meta-Maxwell's Demon" that made comparison semantics dependent on MNIST statistics rather than each parameter's own definition; (2) Neo4j stored raw measurable parameters `k` instead of internal energy `u_k = h_k(k)`, so the classifier had to carry hidden per-feature divisors (`PROPERTY_NORMALIZERS`, `FEATURE_MAX_RANGES`); (3) uniform `1/N` feature weighting ignored Parzhyn's scale-strength hierarchy (ratio > interval > ordinal > nominal). The tuning surface was already flat (4.46pp total spread over 200 CMA-ES trials on the normalizer study — see `experiments/naturalagi-normalizer-tuning-cmaes-v2/findings.md`), so removing the knobs carried low accuracy risk relative to the compliance gain.

**Decision**: Apply `h_k` at extraction (not comparison), simplify `h_c` to `min(|a - b|, 1.0)`, introduce an explicit `SCALE_STRENGTH` multiplier in `_resolve_weight`, and make diagnostic weighting the sole weighting method. Concretely: new `common/common/feature_scales.py` holds per-feature transforms (angle → `v/180`, tortuosity → `1 - 1/v`, `cycle_count → v/(v+1)`, `node_degree → min(v,6)/6`, `neighbor_*_count → v/raw_node_degree`, `avg_neighbor_vector_length → min(v/(2√2), 1)`, eccentricity → `1 - 1/v`, identities elsewhere) plus a `SCALE_STRENGTH` dict (ratio=1.0, ordinal=0.6, nominal=0.4). Extractors (`structural_feature_analyzer`, `vector_angle_strategy`, `neighborhood_context_strategy`, `cycle_count_analyzer`) write `u_k ∈ [0, 1]` directly. `cost_functions.py` drops `PROPERTY_NORMALIZERS`, `FEATURE_MAX_RANGES`, `RANGE_PENALTY_FACTOR`. `_resolve_weight` becomes `strength / (width + epsilon)` for numerics, `strength` for categoricals. All CMA-ES/Optuna normalizer-tuning scaffolding is removed; study DBs are archived under `src/training/experiments/archive/`.

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
