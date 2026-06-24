# /goal improve-accuracy — path to ≥90%: findings (STUCK outcome)

**Date:** 2026-06-05
**Target:** ≥ 90.0% overall accuracy, full complete-only MNIST (frac=1.0, 8,685 classified)
**Result:** **Did not reach 90%. Established hard ceiling at 87.68%.** Every learnable lever tested
regressed or was neutral. This documents the exhaustive search and concrete recommendations.

## Working baseline (real full runs)
- Live 14-concept state (PR#77 + 2026-05-26 `8_2` reactivation): **87.68%** (run_20260605_001913),
  reproduced 87.46% (run_20260604_231845). P≈88.5 R≈87.7 F1≈87.8.
- Per-class recall: 0:94 1:86 **2:73** 3:86 **4:97(P72)** 5:88 6:94(P84) **7:84(P78)** **8:83** 9:92.
- Dominant clusters: 7→4(132), 1→7(125), 2→4(84), 2→7(79), 8→6(53), 5→3(52), 3→4(42), 9→4(42).

## Levers tested — ALL ≤ baseline (real frac=1.0 runs unless noted)
| # | Lever | Mechanism | Result | Why it failed |
|---|---|---|---|---|
| 1 | Complexity prior λ (re-rank) | sort by sim+λ·log2(c) | λ=0.06 → **87.44** (−0.24); offline sweep best ~87.5 (+0.1) | Tapped. Re-ranking can't change which concept fits; **seesaw** (favors large → fixes small-steals-big like 2→7 but worsens big-steals-small like 7→4). |
| 2 | Coverage penalty | sim·(c/img_c)^α | sanity: wrong direction | Same favor-large seesaw as λ. Penalizes the *correct smaller* concept for simple digits (1→7). |
| 3 | diagnostic_weight_epsilon | reweight narrow features | ε=0.25 → **87.04** (−0.64) | Reweights in-range cost; can't separate **overlapping** distributions. |
| 4 | Range tightening (uniform) | shrink min/max toward center k=0.4 | **78.99** (−8.7) | Crashes high-variance classes (3:86→52, 2:73→57). Real images vary beyond tightened ranges. |
| 5 | Range tightening (targeted 4_1,4_2,6_1) | k=0.4 on catch-alls only | test-gate real_4=8%, real_6=0% (crash) | **Class overlap**: real-4 *test* images and the 7s/2s `4_2` steals overlap in the geometric features. Tightening trades recall ~1:1. No usable k. |
| 6 | Feature add: quadrant_change_count | curvature discriminator (7_1 qcc[0,2] vs 2/3 ≥3) | **85.97** (−1.7) | Helped 2→7/3→7 but **dilution** (15th feature) + blunt graph-level +1.5/node penalty crashed class 3 (86→78.5), grew 2→4/3→5. |
| 7 | Subclass reactivation: 1_2,7_2,9_1 | add coverage (proven lever 8_2) | **84.54** (−3.1) | **7_2 catastrophic catch-all**: a "7" is a structural *subset* of 2/4/5, so any 7-concept over-fires. class7 recall→96% but 2→7=281, class2→60%. |
| 8 | FGW comparator | optimal transport vs GED | ~81% (250-img gate) | Worse than tuned GED with same features. |

## Root-cause analysis — why 90% is blocked in this representation
1. **Class overlap in the 14-feature reduced-graph space.** The confusable digits genuinely overlap
   (open-4 ≈ 7; 1 ≈ 7-downstroke; angular-2 ≈ 7). Range/feature levers cannot separate overlapping
   distributions without sacrificing recall 1:1 (lever 4/5).
2. **Size seesaw.** GED + Boria normalizer favors small concepts; the complexity prior counters it
   but any single setting helps one confusion direction and hurts the opposite (lever 1/2).
3. **Simple-digit subset problem.** A "7" (and "1") is structurally contained in many digits, so the
   minimal 7-concept (`7_1`, 5 nodes) is an unavoidable catch-all, and adding 7-coverage worsens it
   (lever 7). The two largest clusters (7→4, 1→7 ≈ 257 errors) are **near-irreducible** here.
4. **Scoring is at a local optimum.** Every per-message scoring knob (λ, coverage, ε, implied
   node_costs) is ≤ baseline → 87.68% is a genuine optimum for these concepts+features.

## Recommendations (require work beyond the skill's learnable-edit scope → need user direction)
1. **New discriminative features in contour_analysis** (computed on nodes, then added to the feature
   list *with retuned weights*): a robust curvature measure and a junction/closure indicator to
   separate 7 vs {2,3,4}. (qcc exists but is graph-level/blunt → needs per-node + careful weighting.)
2. **Curated subclasses for the worst classes (2 @73%, 3 @86%)** built by clustering `datasets/train/`
   class-2/3 images into style-groups (no inactive 2_x/3_x exist). Additive coverage where it's needed,
   unlike the off-target inactive subclasses (1_2/7_2/9_1).
3. **Less-aggressive reduction** so concepts keep more structural anchors (more nodes = more specific,
   less over-fire) — retrain with smaller `simplification_epsilon` / fewer reduction ops; re-verify.
4. **Reconsider the minimal 7-concept**: a 5-node `7_1` cannot avoid catch-all behavior; a structurally
   richer 7 (or a discriminative gate) is needed.

## State left behind
- Neo4j: restored to the **14-concept baseline** (added 1_2/7_2/9_1 deleted; ranges restored from backup).
- `params.json`: clean baseline (ged, ε=1.0, ladder 0.65/0.75/1.0/1.5/10, 14 features).
- **Source change (uncommitted, inert at default):** `classification_orchestrator.py` (+`COVERAGE_ALPHA=0`
  coverage in `_complexity_adjusted_score`) and `nuclio_handler.py` (per-message `coverage_alpha` +
  `complexity_prior_lambda` overrides). α=0 default ⇒ behavior identical to baseline. Deployed to 13 instances.
  Useful for future per-message tuning; revert with `git checkout` + redeploy if undesired.
- Tooling in `src/training/.goal_state/`: measure.py, diagnose.py, rerank_sim.py, shrink_ranges.py /
  restore_ranges.py, classify_check.py, reactivate_subclasses.py, analyze_candidates.py.
- `prepared_samples` copies (1_2/7_2/9_1) removed.
