# Intra-segment Monotone 1:1 Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the order-free `argmax` intra-segment node matching in concept formation with an order-preserving (monotone) 1:1 alignment, so concept↔image correspondences within a segment stop crossing and stop collapsing many-to-one.

**Architecture:** Isolate the hard logic as a pure, graph-free function `align_monotone_one_to_one` (list-in / list-out, unit-tested in isolation). Rewrite `SyncedGraphMinorFinder._create_reduced_path_in_result` to call it over the existing feature-similarity matrix, keying every merged result node by the **concept-side** node id. Delete the obsolete `_find_best_matching_node`. Repoint the formation probe (which currently wraps that deleted method) to wrap the new aligner so the Streamlit formation viz — the validation surface — keeps working.

**Tech Stack:** Python 3.12, NetworkX, pytest. Pure-Python DP (weighted longest-common-subsequence style); no new dependencies.

## Global Constraints

- **Python 3.12**; type hints on all new/edited signatures.
- **No new dependencies**; the aligner is pure Python (stdlib `typing` only).
- **Level-1 (critical-point / anchor) pairing is unchanged.** Do not touch `SyncedTraversalGenerator`, start-point logic, the similarity calculation, or any persistence.
- **No feature-set or similarity-formula changes**; reuse `NodeSimilarityCalculator.calculate_similarity_matrix` as-is.
- **No MNIST accuracy retuning** as part of this change. The 85.80% complete-only baseline (`run_20260427_144233`) is only an optional, non-blocking sanity check (see Task 4).
- **Result nodes are keyed by the concept-side (`G_c`) node id** for stable concept identity across incremental merges.
- **Preserve the log message string** `"already exists in result graph"` verbatim — the probe's `_CollisionLogHandler` (`instrumentation.py:248`) matches on it.
- **Type compatibility = label-list set-intersection** (mirrors `calculate_node_similarity:93` and `process_properties:178`), NOT string equality. (See "Deviations from spec" below.)
- **Tests run from `src/concept_creator/`** with the venv interpreter: `../../natural-agi/bin/python -m pytest …`. `natural-agi-common` is pip-installed in that venv, so `import common` resolves.
- **Conventional Commits**; never add a `Co-Authored-By` trailer.

## Deviations from spec (flagged for reviewer)

The design spec (`docs/superpowers/specs/2026-06-18-intra-segment-monotone-alignment-design.md`) is followed except for three points that the live code forced:

1. **New file path.** Spec writes `src/logic/sequence_aligner.py`; the real logic package is `src/concept_creator/src/logic/`, imported as `src.logic.*`. The file goes there: `src/concept_creator/src/logic/sequence_aligner.py`.
2. **Type-guard signature.** Spec signature is `types_a: list[str]`. Real nodes carry a `labels` **list** (e.g. `["HorizontalVector", "Vector"]`) and every type check in the codebase is a **set-intersection**, not equality — a `HorizontalVector` and a `VerticalVector` must be allowed to match because they share `"Vector"`. A single "primary label" string would wrongly forbid that. So the function takes `types_a: list[list[str]]` (the label lists) and compares by intersection. Semantically identical to the spec's intent (cross-type pairs disallowed), faithful to `node_similarity_calculator.py:93-95`.
3. **Algorithm shape.** Spec gives a "saturate the shorter side, pick strictly-increasing columns" DP. That DP raises when type/parity constraints prevent a full assignment, but spec §9 requires "never raises." We implement the equivalent **weighted-LCS DP** (lexicographic `(match_count, total_similarity)`, cardinality first), which produces the *identical* result in the common (full-saturation) case and degrades gracefully (skips the un-matchable shorter-side node, returns the maximal feasible set) in the rare parity-mismatch case. This satisfies both §4 (monotone, 1:1, saturating, type-safe, `O(m·n)`) and §9 (graceful, never raises).

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/concept_creator/src/logic/sequence_aligner.py` | **Create** | Pure function `align_monotone_one_to_one(similarity, types_a, types_b) -> list[tuple[int,int]]`. The isolated hard logic. |
| `src/concept_creator/src/logic/test_sequence_aligner.py` | **Create** | Table-driven unit tests for the pure function. |
| `src/concept_creator/src/synced_graph_algorithm.py` | **Modify** | Rewrite `_create_reduced_path_in_result` (252-426) to call the aligner and key by concept id; **delete** `_find_best_matching_node` (428-464); add a module-level import of the aligner. `_reduce_subpath`, `_find_best_matching_paths`, `_calculate_path_similarity_score` are untouched. |
| `src/concept_creator/src/test/test_synced_graph_minor_finder.py` | **Create** | Integration test of the rewritten `_create_reduced_path_in_result` (cardinality, order, concept-id keying, property merge, empty segment). |
| `src/concept_creator/probes/instrumentation.py` | **Modify** | Repoint `attach_instrumentation` (286-291) + replace `_make_best_match_wrapper` (211-238) to wrap the module-level `align_monotone_one_to_one`, emitting one `segment_match` event per aligned pair (`crossing=False`, `many_to_one=False`). |
| `src/concept_creator/probes/repro/repro_bug_c.py` | **Modify** | Was a repro of the argmax bug calling the now-deleted method; rewrite to call the aligner and assert the **fixed** behaviour (monotone, 1:1). |
| `src/concept_creator/probes/repro/repro_bug_a.py` | **Modify (docstring/prints only)** | Update narrative: the cross-graph id-collision it demonstrated is fixed by concept-id keying. No assertions in this script. |
| `src/concept_creator/src/test/test_concept_creator.py` | **Modify** | Currently broken-on-import (imports a missing `graph_minor_finder` module). Repoint to `SyncedGraphMinorFinder` and update assertions to the new correspondence — restoring it as a live `find_max_common_minor` regression gate (spec §7). |
| `src/concept_creator/probes/README.md` | **Modify** | Update the `segment_match` doc section (≈131-148) to describe the aligner source. |

---

## Task 1: Pure monotone 1:1 aligner

**Files:**
- Create: `src/concept_creator/src/logic/sequence_aligner.py`
- Test: `src/concept_creator/src/logic/test_sequence_aligner.py`

**Interfaces:**
- Consumes: nothing (pure stdlib).
- Produces: `align_monotone_one_to_one(similarity: list[list[float]], types_a: list[list[str]], types_b: list[list[str]]) -> list[tuple[int, int]]`. Returns `(a_idx, b_idx)` pairs, strictly increasing in both indices, saturating the shorter axis when a same-type monotone full match exists (`len(pairs) == min(len(A), len(B))`), maximizing total similarity; cross-type pairs (no shared label) never produced; never raises (returns the maximal feasible set, possibly `[]`).

- [ ] **Step 1: Write the failing unit tests**

Create `src/concept_creator/src/logic/test_sequence_aligner.py`:

```python
from src.logic.sequence_aligner import align_monotone_one_to_one

V = ["Vector"]
P = ["Point"]
HV = ["HorizontalVector", "Vector"]
VV = ["VerticalVector", "Vector"]


def test_equal_length_identity_best_is_full_diagonal():
    sim = [[0.9, 0.1], [0.1, 0.9]]
    assert align_monotone_one_to_one(sim, [V, V], [V, V]) == [(0, 0), (1, 1)]


def test_unequal_length_saturates_shorter_indices_strictly_increasing():
    # A has 1 node, B has 3; A's node matches its best same-type column.
    sim = [[0.9, 0.0, 0.5]]
    pairs = align_monotone_one_to_one(sim, [HV], [HV, P, VV])
    assert pairs == [(0, 0)]
    assert len(pairs) == min(1, 3)


def test_longer_concept_drops_surplus_keeps_min():
    # A=[V,P,V,P] (4), B=[V,P,V] (3): only monotone same-type triple is (0,1,2).
    sim = [[0.8, 0.0, 0.4],
           [0.0, 0.8, 0.0],
           [0.4, 0.0, 0.8],
           [0.0, 0.5, 0.0]]
    pairs = align_monotone_one_to_one(sim, [V, P, V, P], [V, P, V])
    assert pairs == [(0, 0), (1, 1), (2, 2)]


def test_crossing_temptation_prefers_monotone_over_higher_crossing_cell():
    # Off-diagonal cells are larger, but the only count-2 monotone match is the diagonal.
    sim = [[0.1, 0.9], [0.8, 0.2]]
    assert align_monotone_one_to_one(sim, [V, V], [V, V]) == [(0, 0), (1, 1)]


def test_type_incompatible_never_matched_even_with_high_similarity():
    sim = [[0.99]]
    assert align_monotone_one_to_one(sim, [V], [P]) == []


def test_horizontal_and_vertical_vectors_match_via_shared_vector_label():
    sim = [[0.4]]
    assert align_monotone_one_to_one(sim, [HV], [VV]) == [(0, 0)]


def test_empty_a_or_b_returns_empty():
    assert align_monotone_one_to_one([], [], [V, V]) == []
    assert align_monotone_one_to_one([[], []], [V, V], []) == []


def test_all_zero_row_still_matched_when_cardinality_demands_it():
    # min == 1, so the single shorter-side node is matched despite zero similarity.
    sim = [[0.0, 0.0, 0.0]]
    assert align_monotone_one_to_one(sim, [V], [V, V, V]) == [(0, 0)]


def test_both_length_one_same_type_forced_match():
    assert align_monotone_one_to_one([[0.3]], [P], [P]) == [(0, 0)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd src/concept_creator && ../../natural-agi/bin/python -m pytest src/logic/test_sequence_aligner.py -v`
Expected: collection succeeds; every test FAILS with `ModuleNotFoundError: No module named 'src.logic.sequence_aligner'` (or `ImportError`).

- [ ] **Step 3: Implement the pure function**

Create `src/concept_creator/src/logic/sequence_aligner.py`:

```python
from typing import List, Tuple


def align_monotone_one_to_one(
    similarity: List[List[float]],
    types_a: List[List[str]],
    types_b: List[List[str]],
) -> List[Tuple[int, int]]:
    """Monotone, 1:1, type-safe alignment of two node sub-paths.

    Returns (a_idx, b_idx) pairs, strictly increasing in both indices, that
    saturate the shorter axis (len(pairs) == min(len(A), len(B)) when a
    same-type monotone full match exists) and maximize total similarity.
    Cross-type pairs (label lists with no shared element) are never produced;
    when type/parity constraints make full saturation impossible the maximal
    feasible set is returned. Never raises.
    """
    m = len(similarity)
    n = len(types_b)
    if m == 0 or n == 0:
        return []

    def compatible(i: int, j: int) -> bool:
        return bool(set(types_a[i]) & set(types_b[j]))

    # dp[i][j] = best (match_count, total_similarity) using A[:i] and B[:j].
    # Lexicographic max: cardinality first (saturates the shorter axis),
    # total similarity as the tie-break.
    dp = [[(0, 0.0)] * (n + 1) for _ in range(m + 1)]
    choice = [[""] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            best = dp[i - 1][j]
            move = "up"
            if dp[i][j - 1] > best:
                best = dp[i][j - 1]
                move = "left"
            if compatible(i - 1, j - 1):
                prev = dp[i - 1][j - 1]
                cand = (prev[0] + 1, prev[1] + similarity[i - 1][j - 1])
                if cand >= best:
                    best = cand
                    move = "diag"
            dp[i][j] = best
            choice[i][j] = move

    pairs: List[Tuple[int, int]] = []
    i, j = m, n
    while i > 0 and j > 0:
        move = choice[i][j]
        if move == "diag":
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif move == "up":
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd src/concept_creator && ../../natural-agi/bin/python -m pytest src/logic/test_sequence_aligner.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/concept_creator/src/logic/sequence_aligner.py src/concept_creator/src/logic/test_sequence_aligner.py
git commit -m "feat: pure monotone 1:1 sequence aligner for concept formation"
```

---

## Task 2: Rewrite intra-segment matching + repoint probe (coupled)

This task is atomic: the rewrite deletes `_find_best_matching_node`, which `instrumentation.py:288` references at attach time. Deleting it without repointing the probe makes `attach_instrumentation` raise `AttributeError`, turning the probe-driven gates (`test_run_offline_capture.py`, `test_service_debug_mode.py`, `test_plotting.py`, the `test_probe_selfcheck.py` script) red. A reviewer cannot accept one without the other, so they land together (spec §10).

**Files:**
- Create: `src/concept_creator/src/test/test_synced_graph_minor_finder.py`
- Modify: `src/concept_creator/src/synced_graph_algorithm.py` (add import near line 7; rewrite `_create_reduced_path_in_result` 252-426; delete `_find_best_matching_node` 428-464)
- Modify: `src/concept_creator/probes/instrumentation.py` (replace `_make_best_match_wrapper` 211-238; repoint block 286-291)

**Interfaces:**
- Consumes: `align_monotone_one_to_one` (Task 1); `NodeSimilarityCalculator.calculate_similarity_matrix(graph1, graph2, path1, path2) -> list[list[float]]` (rows=path1, cols=path2); `PropertyProcessor.process_properties(mcm_props, g_props, h_props) -> dict` (g=concept, h=image).
- Produces: unchanged 9-arg signature `_create_reduced_path_in_result(result_graph, graph1, graph2, start1, end1, path1, start2, end2, path2) -> None` (so `_reduce_subpath:163` and `repro_bug_a.py` keep calling it). Module-level name `synced_graph_algorithm.align_monotone_one_to_one` (the probe's patch target). New `segment_match` event still carries `row_idx, best_idx, best_score, row_scores, crossing, many_to_one`.

- [ ] **Step 1: Write the failing integration test**

Create `src/concept_creator/src/test/test_synced_graph_minor_finder.py`:

```python
import networkx as nx

from src.synced_graph_algorithm import SyncedGraphMinorFinder
from src.property_handlers.property_handlers import PropertyProcessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.critical_point_preprocessor import CriticalPointPreprocessor


def _finder():
    return SyncedGraphMinorFinder(
        prop_manager=PropertyProcessor(),
        similarity_calculator=NodeSimilarityCalculator(),
        critical_point_preprocessor=CriticalPointPreprocessor(),
    )


def _hv(x, y):
    return {"labels": ["HorizontalVector", "Vector"], "normalized_x": x, "normalized_y": y}


def _vv(x, y):
    return {"labels": ["VerticalVector", "Vector"], "normalized_x": x, "normalized_y": y}


def _pt(x, y):
    return {"labels": ["Point"], "normalized_x": x, "normalized_y": y}


def test_image_arc_has_extra_node_surplus_dropped_keeps_min_in_order():
    # Concept: Start - HV(1) - End.  Image: Start - HV(11) - P(12) - VV(13) - End.
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, **_hv(0.5, 0.0))
    G_c.add_node(2, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=0.0)
    G_c.add_edges_from([(0, 1), (1, 2)])

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, **_hv(0.5, 0.05))
    G_i.add_node(12, **_pt(0.6, 0.3))
    G_i.add_node(13, **_vv(0.6, 0.6))
    G_i.add_node(14, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=0.0)
    G_i.add_edges_from([(10, 11), (11, 12), (12, 13), (13, 14)])

    result = nx.Graph()
    finder = _finder()
    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=2, path1=[0, 1, 2],
        start2=10, end2=14, path2=[10, 11, 12, 13, 14],
    )

    # Exactly one intermediate (min(1,3)) kept, plus the two anchors.
    assert set(result.nodes) == {0, 1, 2}
    # Intermediate keyed by the CONCEPT node id (1), not any image id (11/12/13).
    assert 1 in result.nodes
    assert not ({11, 12, 13} & set(result.nodes))
    # Order preserved: start - intermediate - end.
    assert list(nx.all_simple_paths(result, 0, 2)) == [[0, 1, 2]]
    # Properties merged from concept node 1 and image node 11 (HV ↔ HV).
    assert "Vector" in result.nodes[1]["labels"]


def test_concept_longer_than_image_keeps_concept_ids_drops_concept_surplus():
    # Concept: Start - HV - P - VV - P(surplus) - End  (4 intermediates).
    # Image:   Start - HV - P - VV - End                (3 intermediates).
    # Only monotone same-type triple is the first three concept intermediates.
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, **_hv(0.2, 0.0))
    G_c.add_node(2, **_pt(0.4, 0.1))
    G_c.add_node(3, **_vv(0.5, 0.3))
    G_c.add_node(4, **_pt(0.55, 0.5))
    G_c.add_node(5, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_c.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, **_hv(0.2, 0.02))
    G_i.add_node(12, **_pt(0.4, 0.12))
    G_i.add_node(13, **_vv(0.5, 0.32))
    G_i.add_node(14, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_i.add_edges_from([(10, 11), (11, 12), (12, 13), (13, 14)])

    result = nx.Graph()
    finder = _finder()
    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=5, path1=[0, 1, 2, 3, 4, 5],
        start2=10, end2=14, path2=[10, 11, 12, 13, 14],
    )

    # min(4,3)=3 intermediates kept, all keyed by concept ids; surplus concept 4 dropped.
    assert set(result.nodes) == {0, 1, 2, 3, 5}
    assert 4 not in result.nodes
    assert not (set(range(10, 15)) & set(result.nodes))
    assert list(nx.all_simple_paths(result, 0, 5)) == [[0, 1, 2, 3, 5]]


def test_adjacent_anchors_no_intermediates_direct_edge():
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_c.add_edge(0, 1)

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_i.add_edge(10, 11)

    result = nx.Graph()
    finder = _finder()
    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=1, path1=[0, 1],
        start2=10, end2=11, path2=[10, 11],
    )

    assert set(result.nodes) == {0, 1}
    assert result.has_edge(0, 1)
```

- [ ] **Step 2: Run the integration test to verify it fails**

Run: `cd src/concept_creator && ../../natural-agi/bin/python -m pytest src/test/test_synced_graph_minor_finder.py -v`
Expected: `test_concept_longer_than_image_keeps_concept_ids_drops_concept_surplus` FAILS — the current code hard-keys result nodes by `template_node_id` (`synced_graph_algorithm.py:378`), so when the image side is the shorter "template" the result holds image ids and may collapse/cross. (The other two may pass incidentally on the current code; that is fine — the failing one pins the fix.)

- [ ] **Step 3: Add the aligner import to `synced_graph_algorithm.py`**

In `src/concept_creator/src/synced_graph_algorithm.py`, add after the existing `from src.logic.synced_traversal_generator import SyncedTraversalGenerator` line (currently line 7):

```python
from src.logic.sequence_aligner import align_monotone_one_to_one
```

Keep it a module-level `from … import` so the bound name `align_monotone_one_to_one` lives in this module's globals — that is the probe's monkeypatch target.

- [ ] **Step 4: Rewrite `_create_reduced_path_in_result`**

Replace the entire body of `_create_reduced_path_in_result` (currently lines 252-426, from the `def` through the final `elif not template_path:` branch) with this. Keep the 9-arg signature and docstring intent; only the body changes:

```python
    def _create_reduced_path_in_result(
        self,
        result_graph: nx.Graph,
        graph1: nx.Graph,
        graph2: nx.Graph,
        start1: Any,
        end1: Any,
        path1: List[Any],
        start2: Any,
        end2: Any,
        path2: List[Any],
    ) -> None:
        """Merge one segment between two matched critical points into the result.

        Intermediate nodes are aligned by an order-preserving (monotone) 1:1
        matching over the feature-similarity matrix. The shorter sub-path is
        saturated; only the longer sub-path's surplus nodes are dropped. Every
        result node — anchors and intermediates — is keyed by the concept-side
        (graph1) node id so concept identity is stable across incremental merges.
        """
        self.logger.debug(
            f"Creating reduced path in result between ({start1}, {start2}) and ({end1}, {end2})"
        )

        if start1 not in result_graph:
            merged_start_props = self.prop_manager.process_properties(
                {}, graph1.nodes[start1], graph2.nodes[start2]
            )
            result_graph.add_node(start1, **merged_start_props)

        sub_path1 = path1[1:-1]
        sub_path2 = path2[1:-1]

        pairs: List[Tuple[int, int]] = []
        if sub_path1 and sub_path2:
            similarity = self.similarity_calculator.calculate_similarity_matrix(
                graph1, graph2, sub_path1, sub_path2
            )
            types_c = [graph1.nodes[node].get("labels", []) for node in sub_path1]
            types_i = [graph2.nodes[node].get("labels", []) for node in sub_path2]
            pairs = align_monotone_one_to_one(similarity, types_c, types_i)
            self.logger.debug(
                f"Aligned {len(pairs)} intra-segment pairs over a "
                f"{len(sub_path1)}x{len(sub_path2)} matrix"
            )

        prev_node = start1
        for concept_idx, image_idx in pairs:
            concept_node = sub_path1[concept_idx]
            image_node = sub_path2[image_idx]
            node_props = self.prop_manager.process_properties(
                {}, graph1.nodes[concept_node], graph2.nodes[image_node]
            )
            if concept_node not in result_graph:
                result_graph.add_node(concept_node, **node_props)
                self.logger.debug(f"Added node {concept_node} to result graph")
            else:
                self.logger.warning(
                    f"Node {concept_node} already exists in result graph. Properties not updated."
                )
            if prev_node != concept_node:
                result_graph.add_edge(prev_node, concept_node)
                prev_node = concept_node

        if end1 not in result_graph:
            merged_end_props = self.prop_manager.process_properties(
                {}, graph1.nodes[end1], graph2.nodes[end2]
            )
            result_graph.add_node(end1, **merged_end_props)

        if prev_node != end1:
            result_graph.add_edge(prev_node, end1)
```

Notes:
- `Tuple` is already imported (`from typing import Tuple, List, Any, Optional`, line 3). `Optional` may become unused after Step 5 — leave the import line as-is; do not churn it.
- The empty-match case (`pairs == []`, including adjacent anchors) falls through to `if prev_node != end1: add_edge(start1, end1)` — the direct anchor edge, replacing the old `:422` `elif`.
- The `"already exists in result graph"` string is preserved verbatim for the probe's collision handler.

- [ ] **Step 5: Delete the obsolete `_find_best_matching_node`**

Delete the whole method `_find_best_matching_node` (currently lines 428-464, the last method in the class). It has no remaining production caller (`_create_reduced_path_in_result` was the only one, via the now-removed line 341).

- [ ] **Step 6: Run the integration test — expect PASS**

Run: `cd src/concept_creator && ../../natural-agi/bin/python -m pytest src/test/test_synced_graph_minor_finder.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 7: Repoint the probe wrapper**

In `src/concept_creator/probes/instrumentation.py`, replace `_make_best_match_wrapper` (lines 211-238) with an aligner wrapper:

```python
def _make_align_wrapper(recorder: FormationRecorder, original, step_ref: list[int]):
    # The monotone aligner returns all (concept_idx, image_idx) pairs for a
    # segment at once; emit one segment_match event per pair. By construction
    # the result is monotone and 1:1, so crossing/many_to_one are always False.
    def _wrapper(similarity, types_a, types_b):
        pairs = original(similarity, types_a, types_b)
        for row_idx, col_idx in pairs:
            row_scores = list(similarity[row_idx]) if similarity else []
            best_score = row_scores[col_idx] if row_scores else 0.0
            recorder.emit({
                "type": "segment_match",
                "step": step_ref[0],
                "row_idx": row_idx,
                "best_idx": col_idx,
                "best_score": round(best_score, 4),
                "row_scores": [round(sc, 4) for sc in row_scores],
                "crossing": False,
                "many_to_one": False,
            })
        return pairs
    return _wrapper
```

Then replace the attach block (lines 286-291) with a module-attribute patch:

```python
    # 3. Wrap the monotone aligner (one segment_match event per aligned pair)
    import src.synced_graph_algorithm as synced_graph_algorithm

    original_align = synced_graph_algorithm.align_monotone_one_to_one
    synced_graph_algorithm.align_monotone_one_to_one = _make_align_wrapper(
        recorder, original_align, step_ref
    )
```

(The patch targets the name in `synced_graph_algorithm`'s globals — exactly the binding that `_create_reduced_path_in_result` resolves at call time.)

- [ ] **Step 8: Run the full live suite + selfcheck — expect green**

Run the probe-driven pytest gates:
`cd src/concept_creator && ../../natural-agi/bin/python -m pytest src/logic/test_sequence_aligner.py src/test/test_synced_graph_minor_finder.py visualization/ probes/ -v`
Expected: PASS, including `test_service_debug_mode.py::test_empty_common_minor_raises` (the empty-minor guard) and `test_run_offline_capture.py`. No `AttributeError` from `attach_instrumentation`.

Run the selfcheck script (it asserts `merge`/`mismatch` behaviour, which is anchor-driven and unaffected — these segments are length-1):
`cd src/concept_creator && ../../natural-agi/bin/python probes/test_probe_selfcheck.py`
Expected: "All assertions passed." If the flipped-set assertions shift, stop and investigate before continuing — they should not, because the planted flip is at the endpoint (Level-1 anchor) level, which this change does not touch.

- [ ] **Step 9: Commit**

```bash
git add src/concept_creator/src/synced_graph_algorithm.py \
        src/concept_creator/src/test/test_synced_graph_minor_finder.py \
        src/concept_creator/probes/instrumentation.py
git commit -m "feat: monotone 1:1 intra-segment alignment in concept formation

Replace the order-free per-row argmax (_find_best_matching_node) with an
order-preserving 1:1 alignment over the feature-similarity matrix; key merged
result nodes by the concept-side node id. Repoint the formation probe to wrap
the new aligner."
```

---

## Task 3: Update repro scripts + probe docs

These artefacts describe or exercise the old behaviour. They are not pytest-collected (`repro_bug_*.py` are manual scripts; the README is docs), so the suite stayed green after Task 2 — but they are now stale and `repro_bug_c.py` would error if run (it calls the deleted method). Bring them current.

**Files:**
- Modify: `src/concept_creator/probes/repro/repro_bug_c.py`
- Modify: `src/concept_creator/probes/repro/repro_bug_a.py` (docstring/prints only)
- Modify: `src/concept_creator/probes/README.md` (`segment_match` section)

- [ ] **Step 1: Rewrite `repro_bug_c.py` to demonstrate the fix**

Replace the body below the imports (the `from src...` block stays; drop the `SyncedGraphMinorFinder` construction since the aligner is pure). Replace lines 23-69 with:

```python
from src.logic.sequence_aligner import align_monotone_one_to_one

V = ["Vector"]

print("=== Bug C (fixed): monotone 1:1 intra-segment alignment ===\n")

# Case 1: All-zero similarity row → still matched (cardinality fixed at min=1),
# but now exactly one monotone 1:1 pair, never a many-to-one collapse.
all_zero = [[0.0, 0.0, 0.0]]
pairs = align_monotone_one_to_one(all_zero, [V], [V, V, V])
print(f"All-zero row: pairs = {pairs}")
assert pairs == [(0, 0)], "fixed: single monotone match even at score 0"

# Case 2: Former many-to-one matrix → now 1:1 (distinct columns).
many = [[0.1, 0.2, 0.9],
        [0.1, 0.3, 0.8]]
pairs = align_monotone_one_to_one(many, [V, V], [V, V, V])
cols = [j for _, j in pairs]
print(f"Was many-to-one: pairs = {pairs}")
assert len(cols) == len(set(cols)), "fixed: no column reused"

# Case 3: Former non-monotone matrix → now monotone (strictly increasing).
non_monotone = [[0.1, 0.2, 0.9],
                [0.8, 0.1, 0.1]]
pairs = align_monotone_one_to_one(non_monotone, [V, V], [V, V, V])
rows = [i for i, _ in pairs]
cols = [j for _, j in pairs]
print(f"Was non-monotone: pairs = {pairs}")
assert rows == sorted(rows) and cols == sorted(cols), "fixed: monotone in both axes"

print("\nCONFIRMED (fixed behavior): intra-segment matching is monotone and 1:1; "
      "score-0 shorter-side nodes are matched exactly once, no crossings, no collapse.")
```

Also update the module docstring (lines 1-15) to state it now verifies the *fixed* monotone 1:1 aligner, not the old argmax bug.

- [ ] **Step 2: Run `repro_bug_c.py`**

Run: `cd src/concept_creator && ../../natural-agi/bin/python probes/repro/repro_bug_c.py`
Expected: prints the three cases and "CONFIRMED (fixed behavior)…"; exits 0.

- [ ] **Step 3: Update `repro_bug_a.py` narrative**

`repro_bug_a.py` still runs (it calls the unchanged 9-arg `_create_reduced_path_in_result` and has no assertions). Its docstring (lines 1-21) and the closing `VERDICT` prints (lines 144-148) describe a cross-graph id-collision caused by `template_node_id` keying (old line 378). That keying is gone — result nodes are always concept-keyed. Update the docstring opening line and the verdict print to reflect that the collision is **fixed**:

Replace the docstring's first paragraph with:

```python
"""
Bug A (FIXED): cross-graph node-ID collision in _create_reduced_path_in_result.

Previously, when the image sub-path was shorter it became the "template" and
result nodes were keyed by image-graph IDs (old line 378), colliding with
concept IDs. The rewrite keys every result node by the concept-side ID, so the
collision no longer occurs. This script now documents that fixed behavior.
"""
```

Replace the final two `print(...)` verdict lines (≈147-148) with:

```python
print("VERDICT (fixed): node 1 is keyed by the concept ID and merged with the image node;")
print("re-adding the same concept ID across segments is the only 'already exists' path now.")
```

- [ ] **Step 4: Run `repro_bug_a.py`**

Run: `cd src/concept_creator && ../../natural-agi/bin/python probes/repro/repro_bug_a.py`
Expected: runs to completion, exits 0 (no assertions; prints the fixed-behavior verdict).

- [ ] **Step 5: Update the `segment_match` doc in `probes/README.md`**

In the `### segment_match` section (≈131-148), change the description line and the two boolean field rows:

- Replace `Fired inside `_find_best_matching_node` for each row of the similarity matrix.` with:
  `Fired once per aligned pair returned by `align_monotone_one_to_one` (monotone 1:1).`
- `row_idx` description → `Concept-side (A) node index`.
- `best_idx` description → `Matched image-side (B) node index`.
- `crossing` description → `Always `False` (alignment is monotone by construction)`.
- `many_to_one` description → `Always `False` (alignment is 1:1 by construction)`.

- [ ] **Step 6: Commit**

```bash
git add src/concept_creator/probes/repro/repro_bug_c.py \
        src/concept_creator/probes/repro/repro_bug_a.py \
        src/concept_creator/probes/README.md
git commit -m "docs: update concept-formation probes/repros for monotone alignment"
```

---

## Task 4: Restore the `find_max_common_minor` regression gate

`src/concept_creator/src/test/test_concept_creator.py` is the spec's named regression target (§7), but it is currently **broken on import** — it imports `from graph_minor_finder import GraphMinorFinder`, a module that does not exist. Repoint it to `SyncedGraphMinorFinder` and update assertions to the new monotone correspondence, restoring it as a live end-to-end gate.

**Files:**
- Modify: `src/concept_creator/src/test/test_concept_creator.py` (imports lines 10-11; `setUp` lines 17-18)

- [ ] **Step 1: Repoint imports and construction**

Replace lines 10-11:

```python
from graph_minor_finder import GraphMinorFinder
from utils import load_graphs_from_file, find_start_point
```

with:

```python
from synced_graph_algorithm import SyncedGraphMinorFinder
from property_handlers.property_handlers import PropertyProcessor
from node_similarity_calculator import NodeSimilarityCalculator
from critical_point_preprocessor import CriticalPointPreprocessor
```

Replace the `setUp` body (lines 17-18 region):

```python
    def setUp(self):
        self.concept_creator = SyncedGraphMinorFinder(
            prop_manager=PropertyProcessor(),
            similarity_calculator=NodeSimilarityCalculator(),
            critical_point_preprocessor=CriticalPointPreprocessor(),
        )
```

(The three existing tests build graphs inline and call `self.concept_creator.find_max_common_minor(...)`; they never use the dropped `load_graphs_from_file` / `find_start_point` helpers. The `SCRIPT_DIR` sys.path shim at lines 7-8 already puts `src/concept_creator/src` on the path, so the bare module imports resolve.)

- [ ] **Step 2: Run the regression test**

Run: `cd src/concept_creator && ../../natural-agi/bin/python -m pytest src/test/test_concept_creator.py -v`
Expected: collection now succeeds. The three tests run. `test_find_max_common_minor_simple` and `test_intersection_point_handling` operate on length-1 segments (unchanged cardinality) and should PASS. `test_complex_graph_structure` has loose assertions and should PASS.

- [ ] **Step 3: Adjust any assertion the new correspondence changed**

If any assertion fails, it will be a node-count or specific-node-presence assertion whose correspondence changed (not a crash). Re-derive the expected count from the segment lengths (`min(len(sub_path_c), len(sub_path_i))` intermediates per segment, plus anchors) and update the literal — do **not** weaken an assertion to `assertGreaterEqual` to dodge a real mismatch. Re-run until green.

- [ ] **Step 4: Commit**

```bash
git add src/concept_creator/src/test/test_concept_creator.py
git commit -m "test: restore find_max_common_minor regression gate for monotone alignment"
```

- [ ] **Step 5 (optional, non-blocking): MNIST sanity check**

Per spec §8, before promoting to production concepts, optionally confirm no accuracy regression vs the 85.80% complete-only baseline (`run_20260427_144233`): retrain concepts, redeploy classification, run the complete-only eval. This is **not** a gate for merging the algorithm change; the primary validation is the formation viz (below). Skip unless explicitly requested.

---

## Validation (manual — the formation viz)

Primary validation is by the user, per spec §8, and is **not** an automated step in this plan:

1. `make formation_viz` (Streamlit on port 8502), run concept formation for a session (e.g. `8_1`) through the runner, open the Step viewer.
2. Confirm intra-segment correspondence lines are 1:1, monotone (no crossings within a loop half), and connect like-positioned nodes — far fewer, non-crossing, distinct-colored lines than before.

Per the revert-first policy: if the viz shows worse correspondence than today, revert the Task 2 rewrite rather than patching forward.

---

## Self-Review

**1. Spec coverage**

| Spec section | Covered by |
|---|---|
| §3 Goal: monotone 1:1, keep `min` intermediates, drop only longer surplus | Task 1 (aligner), Task 2 (rewrite) |
| §3 Non-goals: no Level-1 / feature / similarity / start-point / persistence change | Global Constraints; rewrite reuses `calculate_similarity_matrix` untouched |
| §4 Algorithm (monotone, 1:1, saturating, type-safe, O(m·n)) | Task 1 Step 3 (weighted-LCS DP) + Deviation note 3 |
| §5.1 New `sequence_aligner.py` pure function | Task 1 (relocated per Deviation note 1) |
| §5.2 Rewrite `_create_reduced_path_in_result`, concept-id keying, empty→direct edge, delete `_find_best_matching_node` | Task 2 Steps 3-5 |
| §5.3 Probe repoint to wrap the aligner | Task 2 Step 7 |
| §6 Viz renders from `merge`/`sync_pair` events automatically | Confirmed in research: `plotting.py:_correspondence_pairs` reads only `sync_pair`+`merge`; no viz change needed |
| §7 Unit tests (table-driven, incl. crossing temptation, type-incompat, empty) | Task 1 Step 1 |
| §7 Integration test (extra image node, min kept, concept-keyed, merged) | Task 2 Step 1 |
| §7 Regression: update existing tests; keep empty-minor guard | Task 4 (`test_concept_creator.py`); guard = `test_service_debug_mode::test_empty_common_minor_raises`, run in Task 2 Step 8 |
| §8 Validation via viz; optional MNIST sanity | Validation section; Task 4 Step 5 |
| §9 Edge cases (min==0, all-zero row, both len 1, parity mismatch) | Task 1 tests (all-zero, both-len-1, type-incompat) + DP graceful skip |
| §10 Probe coupling — rewrite + repoint in one change | Task 2 is atomic by construction |

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Every code step shows full code; every run step shows the command and expected output.

**3. Type consistency:** `align_monotone_one_to_one(similarity, types_a, types_b)` — same name and arg order in `sequence_aligner.py` (Task 1), the call in `_create_reduced_path_in_result` (Task 2 Step 4), the probe wrapper `_make_align_wrapper(similarity, types_a, types_b)` (Task 2 Step 7), and `repro_bug_c.py` (Task 3). Return type `list[tuple[int,int]]` consumed as `for concept_idx, image_idx in pairs` and `for row_idx, col_idx in pairs` consistently. `process_properties({}, concept_node_data, image_node_data)` ordering (g=concept, h=image) matches `property_handlers.py:169` and the probe's existing `merge`-event reader.
