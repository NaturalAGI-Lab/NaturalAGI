# Classification Misclassification Drill-Down — Design

**Date:** 2026-06-19
**Status:** Approved (brainstorming), pending implementation plan
**Component:** `src/training/dashboard.py` (Classification Analysis Dashboard) + `src/concept_creator/visualization/plotting.py` + `src/classification/graph_similarity/graph_edit_distance_comparator.py`

## 1. Goal

In the dashboard's **Misclassifications** tab, expanding a row currently shows only a
table of per-concept similarity scores. This feature adds an expandable drill-down that,
for the clicked misclassified image, shows:

1. The **image graph** plotted in the formation-viz visual style.
2. The **expected concept graph** (the concept the image *should* have matched) plotted the same way.
3. The **GED algorithm breakdown** — the node pairs that found **no match** and therefore
   penalized the similarity, so it is visible *why the correct concept lost*.

The view compares **image → expected concept**, not image → matched (winning) concept.

## 2. Approved decisions

- **Layout: Option A** — twin panels (image | expected concept) side-by-side with one
  correspondence line per matched node pair, colored green→red by substitution cost,
  unmatched/deleted nodes drawn with a red dashed halo, and a compact edit-operations
  table below the figure.
- **Comparison target: the expected concept**, defaulting to the highest-similarity
  concept of the expected class (strongest near-miss), with a selector to switch among
  expected-class concepts.
- **Image-graph source: live from Neo4j** via prod `ImageRepository.get_image_graph(image_id)`.
  No persistence to artifacts, no `evaluation.py` change.
- **Absent graph → hide the breakdown.** If Neo4j no longer holds the image (run cleaned,
  or classified with `delete_image_nodes=True`), show a one-line note and render nothing else.
- **Recompute runs in-process** in the Streamlit app (no subprocess).
- **Reuse prod code wherever possible** — re-implement nothing that already exists.

## 3. Why these decisions (context)

- Classification deletes image nodes by default: `src/classification/nuclio_handler.py:153`
  reads `delete_image_nodes` defaulting to `True`, and removes nodes after classifying
  (lines 230, 312). So a normal completed run leaves **no** image graphs in Neo4j. The
  breakdown is therefore a "debug while fresh" tool: run with `delete_image_nodes=False`
  when you intend to inspect, then open the dashboard before the next run.
- The per-node-pair penalty detail must be **recomputed**: prod GED uses
  `nx.optimize_graph_edit_distance` (`graph_edit_distance_comparator.py:121`), which yields
  only costs, never the edit path. The alignment is discarded.
- `GraphEditDistanceComparator.log_edit_operations()` (`graph_edit_distance_comparator.py:21-103`)
  already knows how to turn an edit path into INSERT/DELETE/SUBSTITUTE/MATCH rows with
  costs — but it is currently dead code (nothing passes it `paths`). It is the natural
  single source of truth for the penalty breakdown.
- `plotting.py` is explicitly decoupled ("MUST NOT import from src/ or probes/",
  `plotting.py:1-7`) and operates on plain node-link dicts. The dashboard can import it
  directly. It already draws the exact panel layout (`_node_trace`, `_edge_trace`,
  `node_positions`, `_panel_shapes`) and cost/pair lines (`_pair_trace`,
  `_correspondence_pairs`) used by the formation viz.
- `incorrect_results.csv` already carries `image_id` (set at `classifier.py:258`,
  carried through `evaluation.py:447-452`), `image_path`, `expected`, `predicted`, and
  `classification_results` (JSON list of `{concept_id, is_minor, similarity,
  concept_complexity, image_complexity, message}`).

## 4. Architecture & data flow

Single phase, on click, in-process:

```
dashboard Misclassifications expander (one misclassified row)
  │  row → image_id, expected (class), classification_results (per-concept sims)
  │
  ├─ expected concept selection
  │     candidates = concepts in Neo4j whose class == row.expected (authoritative list),
  │       each annotated with its run similarity from classification_results
  │       ("pre-filtered / not scored" when absent — e.g. complexity > image).
  │     default = highest run similarity, else first; selector lets user switch.
  │     A pre-filtered expected concept is still selectable: its breakdown is computed
  │     on demand (Neo4j holds the concept graph), which is exactly the case worth seeing.
  │
  ├─ ImageRepository.get_image_graph(image_id)        [prod, Neo4j]
  │     graph.number_of_nodes() == 0  →  render absence note, STOP
  │
  └─ ged_breakdown(image_graph, expected_concept_id, expected_concept_graph)
        ├─ prod preprocessing chain (same as ConceptMinorClassifier.check_single_concept):
        │     StartPointPreprocessor.preprocess → GraphAnalyzer(Angle/Quadrant/Direction)
        │     → CriticalPointPreprocessor.preprocess_graphs → (prep_image, prep_concept)
        ├─ path-capturing GED:  nx.optimize_edit_paths(prep_image, prep_concept,
        │     node_subst_cost, node_del_cost, node_ins_cost, edge_match,
        │     edge_del_cost, edge_ins_cost)  with same deadline pattern → best (node_path, edge_path, cost)
        ├─ similarity = 1 - cost/(cost + max(n1, n2, 1))            [same formula as prod]
        ├─ edit_ops = build_edit_operations(node_path, edge_path, prep_image, prep_concept)
        └─ returns: {image_nodelink, concept_nodelink, edit_ops, cost, n1, n2, similarity}
              │  NOTE: image_nodelink/concept_nodelink are the PREPROCESSED graphs
              │  (the exact state GED aligned), so edit_op node refs resolve against the
              │  plotted nodes. Raw graphs are never rendered.
              │
              └─ plotting.comparison_figure(image_nodelink, concept_nodelink, edit_ops)
                 + edit-op table (DataFrame)   →   Option A, via components.html
```

## 5. Components & changes (file by file)

### 5.1 `src/classification/graph_similarity/graph_edit_distance_comparator.py` — refactor (DRY)

Split the existing `log_edit_operations` into:

- `build_edit_operations(node_path, edge_path, image_graph, concept_graph) -> list[EditOp]`
  — returns structured rows. `EditOp` carries: `kind` (`"node"`/`"edge"`), `op`
  (`INSERT`/`DELETE`/`SUBSTITUTE`/`MATCH`), `image_ref`, `concept_ref`, `cost`, and a short
  `reason` string for substitutions (e.g. dominant out-of-range feature when available,
  else node labels). Costs come from the **existing** prod cost functions
  (`node_subst_cost`, `node_del_cost`, `node_ins_cost`, `edge_del_cost`, `edge_ins_cost`,
  `edge_match`) — no new cost logic.
- `log_edit_operations(paths, image_graph, concept_graph)` — keeps current logging
  behaviour, now implemented by formatting `build_edit_operations(...)` output. Prod
  logging output is unchanged.

Add a debugger-only static method:

- `compare_graphs_ged_with_path(image_graph, concept_graph, concept_name, ged_timeout)
  -> tuple[float, list, list]` returning `(similarity, node_path, edge_path)`, using
  `nx.optimize_edit_paths` with the same cost functions and the same `time.monotonic()`
  deadline/iteration loop as `compare_graphs_ged`. It computes similarity with the
  identical formula so the debugger number matches prod within timeout. Prod's
  `compare_graphs_ged` is untouched.

### 5.2 `src/concept_creator/visualization/plotting.py` — add one figure builder

- `comparison_figure(image_graph: dict, concept_graph: dict, edit_ops: list[dict],
  *, height: int = 420) -> go.Figure` — composes the existing helpers:
  - two panels via `node_positions(image_graph, 0.0)` and
    `node_positions(concept_graph, PANEL_OFFSET)`, `_edge_trace`, `_node_trace`,
    `_panel_shapes([0.0, PANEL_OFFSET])`, `_figure_layout`.
  - one correspondence line per SUBSTITUTE/MATCH edit op via a cost→color mapping
    (reuse `_pair_trace`'s style; color by cost band rather than `PAIR_PALETTE`):
    `NO_COST→green`, graduated amber/orange, `>=NO_MATCH→red`.
  - DELETE (image node, no concept slot) and INSERT (concept node, no image slot) drawn
    with a red dashed halo marker around the node position.
  - reuses `figure_html` for the `components.html` embed. No change to existing functions.

Add a small module-level helper `cost_color(cost: float) -> str` for the banding, kept in
`plotting.py` so it stays pure.

### 5.3 `src/training/ged_breakdown.py` — new glue module

- `get_image_graph_if_present(driver, image_id) -> nx.Graph | None` — wraps prod
  `ImageRepository.get_image_graph`; returns `None` when the graph has 0 nodes.
- `expected_concepts(all_concept_ids: list[str], classification_results: list[dict],
  expected_class: str) -> list[dict]` — from the authoritative Neo4j concept list, keeps
  those whose class == `expected_class` (class via the existing
  `extract_class_from_concept_id`), annotates each with its run similarity from
  `classification_results` (or `None` = pre-filtered/not scored), sorted by similarity
  desc with scored concepts first.
- `compute_breakdown(image_graph, concept_id, concept_graph, ged_timeout) -> dict` —
  runs the prod preprocessing chain + `compare_graphs_ged_with_path` +
  `build_edit_operations`, returns the node-link dicts (`nx.node_link_data`), `edit_ops`
  (as plain dicts), and `{cost, n1, n2, similarity}`. Imports prod classes; no copies.

This module is import-only (no Streamlit), so it is unit-testable headless.

### 5.4 `src/training/dashboard.py` — wire the drill-down into the expander

Inside the existing `tab_incorrect` loop (`dashboard.py:242-262`), after the current
results table, add the drill-down:

- read `image_id` and `expected` from the row;
- compute `expected_concepts(get_all_concept_ids(), classification_results, expected)`;
  if empty → note "no concept of class `<expected>` in Neo4j"; else a `st.selectbox`
  (default = best run similarity), each option annotated with its score or "pre-filtered";
- `get_image_graph_if_present(driver, image_id)`; if `None` → render the absence note and
  stop (no panels/table);
- else load the selected expected concept graph (reuse existing `load_concept_graph`),
  call `compute_breakdown`, then render `plotting.comparison_figure(...)` via
  `components.html(plotting.figure_html(fig), ...)` and the edit-op table via
  `st.dataframe`, with penalized rows visually distinct.

A module-level Neo4j `driver` (already configured via `NEO4J_URI/USER/PASS` at
`dashboard.py:18-20`) is reused; the existing `@st.cache_data` pattern caches breakdowns
keyed by `(run, image_id, concept_id)`.

### 5.5 No change to `evaluation.py`, the Nuclio hot path, or message formats.

To make graphs available for debugging, the test run is performed with
`delete_image_nodes=False` (existing parameter). This is documentation, not code.

## 6. Error handling

| Condition | Behaviour |
|---|---|
| Image graph absent in Neo4j (0 nodes) | One-line note; no panels/table. |
| Neo4j unreachable | Caught; note "Neo4j unavailable — breakdown disabled". |
| Expected concept not in `classification_results` (pre-filtered) | Annotated "pre-filtered / not scored" in the selector; breakdown still computed on demand. |
| No concept of the expected class exists in Neo4j | Note "no concept of class `<expected>` in Neo4j"; no panels/table. |
| GED timeout | Use best path found so far (same anytime behaviour as prod); show iteration count + a "timed out" caption. |
| Preprocessing raises | Show the prod exception text (mirrors `ConceptMinorClassifier` `except`). |

All conditions degrade to a clean message inside the expander — never a stack trace.

## 7. Testing

- **Unit (`src/training/test_ged_breakdown.py`)**
  - `build_edit_operations` produces correct rows/costs for a hand-built path on two
    small graphs (covers MATCH, SUBSTITUTE-with-cost, DELETE, INSERT).
  - `expected_concepts` filters/sorts correctly, including the empty (pre-filtered) case.
  - `compute_breakdown` on two fixture graphs returns node-link dicts + edit_ops + a
    similarity equal to the prod formula on the same cost.
  - `get_image_graph_if_present` returns `None` for a 0-node result.
- **Plotting (`src/concept_creator/visualization/test_plotting.py`)**
  - `comparison_figure` emits the expected trace count (2 edge + 2 node + N pair + halos)
    and `cost_color` bands map correctly.
- **Smoke (`src/training/` AppTest, pattern of `visualization/test_app_smoke.py`)**
  - dashboard renders the expander with a stubbed `compute_breakdown` (no Neo4j) and with
    the absence path (image graph `None`).
- **Visual verification — `/playwright-expert`** (mandatory acceptance gate per request):
  drive the running dashboard (`make dashboard`, port 8501), open the Misclassifications
  tab, expand a misclassified row backed by a `delete_image_nodes=False` run, screenshot,
  and confirm: two panels render, correspondence lines are visible and color-graded,
  deleted nodes show the halo, the edit-op table is legible, dark theme is consistent, and
  nothing overflows the expander. Iterate on spacing/heights until visually clean.

## 8. Out of scope

- Persisting graphs to artifacts (explicitly dropped).
- Comparing against the winning/wrong concept (view targets the expected concept only).
- Migrating the existing **Concept Debugger** tab from pyvis to `plotting.py` (possible
  later cleanup; not part of this feature).
- Any change to production classification behaviour, Kafka messages, or accuracy.

## 9. References (existing patterns to follow)

- Decoupled Streamlit + plotting split: `src/concept_creator/visualization/formation_viz_app.py`
  and `plotting.py`.
- `components.html(plotting.figure_html(fig), ...)` embed: `formation_viz_app.py:184-188`.
- Edit-operation formatting to reuse: `graph_edit_distance_comparator.py:21-103`.
- Prod preprocessing chain to mirror: `concept_minor_classifier.py:51-100`.
- Concept loading from Neo4j: `dashboard.py:106-136` (`load_concept_graph`).
- Misclassification expander to extend: `dashboard.py:242-262`.
