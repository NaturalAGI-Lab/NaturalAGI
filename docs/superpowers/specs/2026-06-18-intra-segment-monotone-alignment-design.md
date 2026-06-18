# Intra-segment monotone 1:1 alignment for concept formation

- **Date:** 2026-06-18
- **Status:** Draft (awaiting review)
- **Component:** `concept_creator` — `SyncedGraphMinorFinder._create_reduced_path_in_result`
- **Related:** `2026-06-12-formation-viz-streamlit-design.md` (the viz is the validation surface)

## 1. Problem

`find_max_common_minor` matches two graphs at two levels:

- **Level 1 — critical points (anchors):** `generate_synced_traversal` pairs `StartPoint`/`EndPoint`/`IntersectionPoint`/`CornerPoint` 1:1, type-constrained, in traversal order. This is correct and stays as-is.
- **Level 2 — intermediate nodes between two consecutive anchors:** `_create_reduced_path_in_result` takes the *shorter* sub-path as a "template", then for each template node calls `_find_best_matching_node`, a bare `argmax` over the similarity matrix with **no order constraint and no threshold** (`synced_graph_algorithm.py:454-464`).

The Level-2 matching is the defect. Because each template node independently picks its global best match:

- matches **cross** (concept's left arc can map to the image's right arc),
- matches are **many-to-one** (several template nodes collapse onto one node),
- there is **no notion of "no good match here"**.

This is the tangle of crossing correspondence lines visible in the formation viz Step viewer.

## 2. Verified facts (Neo4j, session `8_1`, 88 images)

The user's mental model — "match the apex, then align each half" — is already structurally enabled at Level 1:

- The **loop apex is always a Level-1 anchor**: top apex is a `CornerPoint` in 87/88 images and an `IntersectionPoint` in the 1 remainder; bottom apex is a `CornerPoint` in 88/88. So every apex is a matched critical point.
- Loops are therefore already subdivided by corner anchors (apex + shoulders) with the figure-8 crossing as intersection points. The sub-paths Level-2 runs over are short (a handful of `Vector`/`Point` nodes).

Conclusion: no new anchor detection is required. The fix is confined to the intra-segment matching.

## 3. Goal / non-goals

**Goal:** Replace the intra-segment `argmax` with an **order-preserving (monotone) 1:1 matching** over the existing feature-similarity matrix. Matched nodes merge; the result keeps `min(count_c, count_i)` intermediate nodes per segment — i.e. the shorter sub-path is fully matched and only the **longer** sub-path's surplus nodes are dropped.

**Non-goals:**
- Anchor-level (Level-1) pairing is unchanged. If validation later shows residual crossings originate at the corner-pairing level, that is a separate follow-up spec.
- No change to feature set, similarity calculation, start-point logic, or persistence.
- No MNIST accuracy retuning as part of this change (see §8).

## 4. Algorithm — constrained monotone 1:1 matching

Inputs: the similarity matrix `S` (already produced by `NodeSimilarityCalculator.calculate_similarity_matrix`) over the two intermediate sub-paths `A` (concept side, `m` nodes) and `B` (image side, `n` nodes), where `S[i][j] ∈ [0,1]`.

Saturate the **shorter** side. WLOG let `m ≤ n` (otherwise transpose). Find strictly increasing column indices `j_0 < j_1 < … < j_{m-1}` maximizing `Σ_i S[i][j_i]`:

```
dp[i][j] = S[i][j] + max( dp[i-1][j'] for j' < j )      # i > 0
dp[0][j] = S[0][j]
answer   = max_j dp[m-1][j]   ; traceback yields the j indices
```

`O(m·n)` (prefix-max keeps it linear per row). Properties:

- **Monotone** → "left half ↔ left half"; no crossings.
- **1:1** → no many-to-one collapse.
- **Saturates the shorter side** → result intermediate count = `min(m, n)`; only the longer path's extra nodes are dropped. Same cardinality as today, correct correspondence.
- **Type-safe.** `calculate_node_similarity` already returns `0.0` for type-incompatible nodes (`node_similarity_calculator.py:93-95`), so `Point`↔`Vector` cells are `0`. The DP additionally forbids cross-type matches defensively. Both sub-paths share the `Vector … Vector` alternation (the path between two critical `Point`s is `V P V … V`), so a valid same-type monotone full match always exists.

No match threshold (`τ`) is used: every shorter-side node is matched to its best monotone counterpart.

## 5. Components

### 5.1 New: `src/logic/sequence_aligner.py`
A pure, graph-free function — the hardest-to-test logic isolated as list-in/list-out:

```python
def align_monotone_one_to_one(
    similarity: list[list[float]],
    types_a: list[str],
    types_b: list[str],
) -> list[tuple[int, int]]:
    """Return monotone 1:1 (a_idx, b_idx) pairs saturating the shorter axis,
    maximizing total similarity; cross-type pairs are disallowed."""
```

Returns `len == min(len(A), len(B))` pairs, strictly increasing in both indices.

### 5.2 Rewrite: `_create_reduced_path_in_result`
- Drop the template/longer split and the `_find_best_matching_node` calls.
- Compute `S` over `sub_path1 = path1[1:-1]`, `sub_path2 = path2[1:-1]` (unchanged extraction).
- Call `align_monotone_one_to_one(S, types_c, types_i)`.
- Build the result path: `start_anchor → [merged matched pairs in order] → end_anchor`.
  - For each `(i, j)` pair: `node_props = prop_manager.process_properties({}, G_c.nodes[c_node], G_i.nodes[i_node])`; add a result node **keyed by the concept-side (`G_c`) node id** so concept identity is stable across incremental merges; connect to the previous kept node.
  - Anchors merge exactly as today (still keyed by `G_c` ids).
  - Empty match set (`min == 0`) → direct `start_anchor → end_anchor` edge (reuses existing `:422` behavior).
- **Delete** `_find_best_matching_node` and the template-selection branch.

### 5.3 Probe update: `src/concept_creator/probes/instrumentation.py`
`attach_instrumentation` currently wraps `finder._find_best_matching_node` (`:288`) to emit `segment_match` events. Repoint it to wrap `align_monotone_one_to_one`, emitting one event per aligned pair (with `crossing`/`many_to_one` now expected `False`). This keeps the probe from crashing and keeps the Events / Node-inspector tabs accurate.

## 6. Data flow & visualization (the validation surface)

```
similarity matrix ──► align_monotone_one_to_one ──► matched (c_node, i_node) pairs
                                                        │
                                                        ▼
                         process_properties(c, i)  ── emits "merge" event ──► formation viz line
                                                        │
                                                        ▼
                              result node (concept id) + edge in result graph
```

The formation viz draws correspondence lines from `merge` events (every `process_properties` call) plus `sync_pair` anchor events (`plotting.py:_correspondence_pairs`). Because the rewrite issues exactly one `process_properties` per matched pair, the new 1:1 monotone matches render automatically — as far fewer, non-crossing, distinct-colored lines (per the 2026-06-12 viz styling). **This is how the change is validated** (see §8).

## 7. Testing (TDD)

**Unit — `align_monotone_one_to_one` (table-driven):**
- equal length, identity-best → full diagonal match;
- unequal length → shorter saturated, longer surplus skipped, indices strictly increasing;
- a "crossing temptation" matrix (off-diagonal max) → monotone result still chosen over the higher-but-crossing cell;
- type-incompatible rows/cols → never matched cross-type;
- empty `A` or `B` → empty result.

**Integration — `_create_reduced_path_in_result`:** hand-built concept/image segment where the image arc has one extra node; assert the result keeps `min` intermediate nodes in order, surplus dropped, node keyed by concept id, props merged.

**Regression:** update existing `find_max_common_minor` / concept-formation tests to the new correspondence; keep the empty-minor guard test.

## 8. Validation

Primary validation is **manual, via the formation viz**, performed by the user:
- Run concept formation for a session (e.g. `8_1`) through the runner; open the Step viewer.
- Confirm the intra-segment correspondence lines are 1:1, monotone (no crossings within a loop half), and connect like-positioned nodes.

Optional, non-blocking sanity check before promoting to production concepts: retrain concepts, redeploy classification, run the complete-only MNIST eval and confirm no regression vs the **85.80%** baseline (`run_20260427_144233`).

## 9. Edge cases

- `min == 0` (adjacent anchors): direct anchor edge, no intermediate nodes.
- All-zero similarity row (isolated/incomparable node): still matched monotonically (count is fixed at `min`); the merged props simply reflect a poor match — surfaced as a far-apart (dashed) line in the viz, not silently hidden.
- Both sub-paths length 1: single forced 1:1 match.
- Parity mismatch (sub-paths not both `V…V`): the defensive same-type constraint prevents a `Point`↔`Vector` merge; if no feasible same-type full match exists for the shorter side, fall back to skipping that node (logged), so the algorithm never raises.

## 10. Risks / rollback

- **Behavioral shift in concepts.** Correspondence changes even though cardinality does not; merged property ranges will differ. Mitigation: viz inspection first; accuracy sanity check before production retrain. Per the revert-first policy, revert the rewrite if the viz shows worse correspondence than today.
- **Probe coupling.** The probe depends on a production method name; the rewrite updates both together in one change so the viz keeps working.
