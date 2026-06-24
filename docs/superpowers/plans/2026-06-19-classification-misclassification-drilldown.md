# Classification Misclassification Drill-Down Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the dashboard's Misclassifications tab, expanding a row shows the image graph and its *expected* concept graph side-by-side (formation-viz style) with the GED node-pair penalties that made the correct concept lose.

**Architecture:** On click, fetch the image graph live from Neo4j (prod `ImageRepository`); if absent, hide the breakdown. Otherwise reuse the prod preprocessing chain + prod cost functions in a path-capturing GED, turn the edit path into penalty rows, and render two panels + cost-colored correspondence lines via the existing pure `plotting.py`. No persistence, no hot-path or message-format changes.

**Tech Stack:** Python 3.12, Streamlit, NetworkX 3.6.1 (`optimize_edit_paths`), Plotly (via `plotting.py`), Neo4j, pytest.

## Global Constraints

- Reuse prod code; never re-implement scoring/cost/preprocessing logic. New code is glue + rendering only.
- `plotting.py` is pure: it must NOT import from `src/` or `probes/` (only plotly + stdlib + networkx).
- Node-link contract for plotting payloads is `nx.node_link_data(g, edges="links")` then JSON-sanitized (matches `formation_runner.serialize_graph`).
- Prod GED similarity formula is `1 - cost/(cost + max(n1, n2, 1))`, `n = nodes + edges`. Reuse verbatim.
- Cost ladder (source of truth `cost_functions.NodeCost`): `NO_COST=0.0, MINOR=0.65, GENERAL=0.75, SEVERE=1.0, NO_MATCH=1.5, IMPOSSIBLE=10.0`.
- Commit messages: Conventional Commits, lowercase after prefix. **Never** add a `Co-Authored-By` trailer.
- Run all Python via the venv: `natural-agi/bin/python` / `natural-agi/bin/pytest`.
- View comparison is **image → expected concept**, never image → matched/winning concept.

**Before you start:** create a feature branch off the project integration branch (do not work on `feature/concept-creator-fixes`). Spec reference: `docs/superpowers/specs/2026-06-19-classification-misclassification-drilldown-design.md`.

---

### Task 1: `build_edit_operations` — penalty rows from an edit path (DRY refactor)

Turn the dead-code `log_edit_operations` into the single source of truth for INSERT/DELETE/SUBSTITUTE/MATCH rows + costs, computed by the prod cost functions.

**Files:**
- Modify: `src/classification/graph_similarity/graph_edit_distance_comparator.py`
- Test: `src/classification/graph_similarity/test_edit_operations.py` (create)

**Interfaces:**
- Produces: `build_edit_operations(node_path, edge_path, image_graph, concept_graph) -> list[dict]`
  where each row is `{"kind": "node"|"edge", "op": "MATCH"|"SUBSTITUTE"|"DELETE"|"INSERT", "image_ref": str|None, "concept_ref": str|None, "cost": float, "reason": str}`.
- Consumes: prod cost callables already imported in the module (`node_subst_cost`, `node_del_cost`, `node_ins_cost`, `edge_match`, `edge_del_cost`, `edge_ins_cost`) and `NodeCost`.

- [ ] **Step 1: Write the failing test**

Create `src/classification/graph_similarity/test_edit_operations.py`:

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import networkx as nx

from graph_similarity.graph_edit_distance_comparator import build_edit_operations
from graph_similarity.cost_functions import NodeCost


def _img():
    g = nx.Graph()
    g.add_node("a", labels=["Point", "EndPoint"], normalized_x=0.1)
    g.add_node("b", labels=["Point", "CornerPoint"], normalized_x=0.9)
    g.add_edge("a", "b")
    return g


def _concept():
    g = nx.Graph()
    g.add_node("x", labels=["Point", "EndPoint"], normalized_x=0.1)
    return g


def test_build_edit_operations_classifies_and_costs():
    node_path = [("a", "x"), ("b", None)]
    edge_path = [(("a", "b"), None)]

    ops = build_edit_operations(node_path, edge_path, _img(), _concept())

    by = {(o["op"], o["kind"]): o for o in ops}
    assert by[("MATCH", "node")]["cost"] == NodeCost.NO_COST
    assert by[("MATCH", "node")]["image_ref"] == "a"
    assert by[("MATCH", "node")]["concept_ref"] == "x"
    assert by[("DELETE", "node")]["cost"] == NodeCost.MINOR
    assert by[("DELETE", "node")]["image_ref"] == "b"
    assert by[("DELETE", "edge")]["cost"] == NodeCost.MINOR
```

- [ ] **Step 2: Run test to verify it fails**

Run: `natural-agi/bin/pytest src/classification/graph_similarity/test_edit_operations.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_edit_operations'`.

- [ ] **Step 3: Implement `build_edit_operations` and route `log_edit_operations` through it**

In `src/classification/graph_similarity/graph_edit_distance_comparator.py`, add `NodeCost` to the existing cost import:

```python
from .cost_functions import (
    node_subst_cost,
    node_del_cost,
    node_ins_cost,
    edge_match,
    edge_del_cost,
    edge_ins_cost,
    NodeCost,
)
```

Add module-level helper + builder above the class:

```python
def _labels(node_data) -> list:
    return sorted(str(x) for x in node_data.get("labels", []))


def build_edit_operations(node_path, edge_path, image_graph, concept_graph) -> list:
    ops = []
    for n1, n2 in node_path:
        if n1 is None:
            ops.append({"kind": "node", "op": "INSERT", "image_ref": None,
                        "concept_ref": str(n2),
                        "cost": node_ins_cost(concept_graph.nodes[n2]),
                        "reason": "concept node unmatched"})
        elif n2 is None:
            ops.append({"kind": "node", "op": "DELETE", "image_ref": str(n1),
                        "concept_ref": None,
                        "cost": node_del_cost(image_graph.nodes[n1]),
                        "reason": "no slot in concept"})
        else:
            cost = node_subst_cost(image_graph.nodes[n1], concept_graph.nodes[n2])
            op = "MATCH" if cost == NodeCost.NO_COST else "SUBSTITUTE"
            ops.append({"kind": "node", "op": op, "image_ref": str(n1),
                        "concept_ref": str(n2), "cost": cost,
                        "reason": f"{_labels(image_graph.nodes[n1])} ↔ "
                                  f"{_labels(concept_graph.nodes[n2])}"})
    for e1, e2 in edge_path:
        if e1 is None:
            ops.append({"kind": "edge", "op": "INSERT", "image_ref": None,
                        "concept_ref": str(e2),
                        "cost": edge_ins_cost(concept_graph.edges[e2]), "reason": ""})
        elif e2 is None:
            ops.append({"kind": "edge", "op": "DELETE", "image_ref": str(e1),
                        "concept_ref": None,
                        "cost": edge_del_cost(image_graph.edges[e1]), "reason": ""})
        elif not edge_match(image_graph.edges[e1], concept_graph.edges[e2]):
            ops.append({"kind": "edge", "op": "SUBSTITUTE", "image_ref": str(e1),
                        "concept_ref": str(e2),
                        "cost": edge_del_cost(image_graph.edges[e1])
                        + edge_ins_cost(concept_graph.edges[e2]), "reason": ""})
        else:
            ops.append({"kind": "edge", "op": "MATCH", "image_ref": str(e1),
                        "concept_ref": str(e2), "cost": 0.0, "reason": ""})
    return ops
```

Then replace the body of `log_edit_operations` so it formats `build_edit_operations` output (preserving the existing section headers/totals), keeping its signature `log_edit_operations(paths, image_graph, concept_graph)`:

```python
    @staticmethod
    def log_edit_operations(paths, image_graph: nx.Graph, concept_graph: nx.Graph):
        if not paths:
            logger.info("No edit paths found")
            return
        node_path, edge_path = paths[0]
        ops = build_edit_operations(node_path, edge_path, image_graph, concept_graph)
        node_total = sum(o["cost"] for o in ops if o["kind"] == "node")
        edge_total = sum(o["cost"] for o in ops if o["kind"] == "edge")
        logger.info("=" * 60)
        logger.info("GRAPH EDIT DISTANCE OPERATIONS")
        for o in ops:
            logger.info(
                f"{o['op']:<12} {str(o['image_ref']):<16} "
                f"{str(o['concept_ref']):<16} {o['cost']:<8} {o['reason']}"
            )
        logger.info(f"TOTAL NODE COST: {node_total}")
        logger.info(f"TOTAL EDGE COST: {edge_total}")
        logger.info(f"TOTAL COST: {node_total + edge_total}")
        logger.info("=" * 60)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `natural-agi/bin/pytest src/classification/graph_similarity/test_edit_operations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/classification/graph_similarity/graph_edit_distance_comparator.py src/classification/graph_similarity/test_edit_operations.py
git commit -m "refactor: extract build_edit_operations as shared GED penalty source"
```

---

### Task 2: `compare_graphs_ged_with_path` — path-capturing GED

Prod GED discards the alignment. Add a debugger-only method that captures the edit path with the same cost functions and similarity formula.

**Files:**
- Modify: `src/classification/graph_similarity/graph_edit_distance_comparator.py`
- Test: `src/classification/graph_similarity/test_ged_with_path.py` (create)

**Interfaces:**
- Produces: `GraphEditDistanceComparator.compare_graphs_ged_with_path(image_graph, concept_graph, concept_name, ged_timeout) -> tuple[float, float, list, list]` returning `(similarity, cost, node_path, edge_path)`.

- [ ] **Step 1: Write the failing test**

Create `src/classification/graph_similarity/test_ged_with_path.py`:

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import networkx as nx

from graph_similarity.graph_edit_distance_comparator import GraphEditDistanceComparator


def _graph():
    g = nx.Graph()
    g.add_node(1, labels=["Point", "EndPoint"], normalized_x=0.2, normalized_y=0.3)
    g.add_node(2, labels=["Point", "CornerPoint"], normalized_x=0.6, normalized_y=0.7)
    g.add_edge(1, 2)
    return g


def test_identical_graphs_have_zero_cost_and_full_similarity():
    g1 = _graph()
    g2 = _graph()
    sim, cost, node_path, edge_path = (
        GraphEditDistanceComparator.compare_graphs_ged_with_path(g1, g2, "self", 5.0)
    )
    assert cost == 0.0
    assert sim == 1.0
    assert len(node_path) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `natural-agi/bin/pytest src/classification/graph_similarity/test_ged_with_path.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'compare_graphs_ged_with_path'`.

- [ ] **Step 3: Implement the method**

Add to `GraphEditDistanceComparator` in `graph_edit_distance_comparator.py` (after `compare_graphs_ged`):

```python
    @staticmethod
    def compare_graphs_ged_with_path(
        image_graph: nx.Graph,
        concept_graph: nx.Graph,
        concept_name: str,
        ged_timeout: float,
    ):
        best = None
        try:
            for node_path, edge_path, cost in nx.optimize_edit_paths(
                image_graph,
                concept_graph,
                node_subst_cost=node_subst_cost,
                node_del_cost=node_del_cost,
                node_ins_cost=node_ins_cost,
                edge_match=edge_match,
                edge_del_cost=edge_del_cost,
                edge_ins_cost=edge_ins_cost,
                timeout=ged_timeout,
            ):
                best = (node_path, edge_path, cost)
        except Exception as e:
            logging.error(f"Error calculating GED path for {concept_name}: {e}",
                          exc_info=True)
            return 0.0, 0.0, [], []

        if best is None:
            return 0.0, 0.0, [], []

        node_path, edge_path, cost = best
        n1 = image_graph.number_of_nodes() + image_graph.number_of_edges()
        n2 = concept_graph.number_of_nodes() + concept_graph.number_of_edges()
        similarity = round(1.0 - (cost / (cost + max(n1, n2, 1))), 4)
        return similarity, cost, node_path, edge_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `natural-agi/bin/pytest src/classification/graph_similarity/test_ged_with_path.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/classification/graph_similarity/graph_edit_distance_comparator.py src/classification/graph_similarity/test_ged_with_path.py
git commit -m "feat: add path-capturing GED for the misclassification debugger"
```

---

### Task 3: `preprocess_pair` — shared preprocessing seam (DRY refactor)

Extract the preprocessing block from `check_single_concept` so prod and the debugger share one preprocessing path.

**Files:**
- Modify: `src/classification/concept_minor_classifier.py`
- Test: `src/classification/test_preprocess_pair.py` (create)

**Interfaces:**
- Produces: `ConceptMinorClassifier.preprocess_pair(image_graph, concept_graph) -> tuple[nx.Graph, nx.Graph]` returning `(preprocessed_image_graph, preprocessed_concept_graph)`.
- `check_single_concept` is refactored to call it; external behavior unchanged.

- [ ] **Step 1: Write the failing test (wiring/refactor-safety)**

Create `src/classification/test_preprocess_pair.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import networkx as nx

from concept_minor_classifier import ConceptMinorClassifier
from models import ClassificationResult


def test_check_single_concept_uses_preprocess_pair(monkeypatch):
    clf = ConceptMinorClassifier()

    sentinel_img = nx.Graph()
    sentinel_img.add_node(1, labels=["Point"])
    sentinel_con = nx.Graph()
    sentinel_con.add_node(1, labels=["Point"])

    monkeypatch.setattr(clf, "preprocess_pair",
                        lambda image_graph, concept_graph: (sentinel_img, sentinel_con))

    captured = {}

    def fake_compare(image_graph, concept_graph, concept_name):
        captured["image"] = image_graph
        captured["concept"] = concept_graph
        return 0.5

    monkeypatch.setattr(clf.comparator, "compare", fake_compare)

    result = clf.check_single_concept(nx.Graph(), "7_1", nx.Graph())

    assert isinstance(result, ClassificationResult)
    assert captured["image"] is sentinel_img
    assert captured["concept"] is sentinel_con
```

- [ ] **Step 2: Run test to verify it fails**

Run: `natural-agi/bin/pytest src/classification/test_preprocess_pair.py -v`
Expected: FAIL — `AttributeError: 'ConceptMinorClassifier' object has no attribute 'preprocess_pair'`.

- [ ] **Step 3: Extract `preprocess_pair` and call it from `check_single_concept`**

In `src/classification/concept_minor_classifier.py`, add the method and rewrite the preprocessing portion of `check_single_concept` to delegate. Replace the body from the `image_graph = copy.deepcopy(image_graph)` line through the `preprocess_graphs(...)` assignment with a single `preprocess_pair` call:

```python
    def preprocess_pair(self, image_graph: nx.Graph, concept_graph: nx.Graph):
        image_graph = copy.deepcopy(image_graph)
        image_graph = self.start_point_preprocessor.preprocess(
            inference_graph=image_graph,
            concept_graph=concept_graph,
        )
        GraphAnalyzer(
            graph=image_graph,
            visitors=[
                AngleVisitor(image_graph),
                QuadrantVisitor(image_graph),
                DirectionVisitor(image_graph),
            ],
        ).analyze()
        return self.critical_point_preprocessor.preprocess_graphs(
            inference_graph=image_graph,
            concept_graph=concept_graph,
        )
```

Then inside `check_single_concept`'s `try:` block, replace the preprocessing lines with:

```python
            logging.info("Preprocessing image graph")
            preprocessed_image_graph, preprocessed_concept_graph = self.preprocess_pair(
                image_graph, concept_graph
            )
```

Leave the rest of `check_single_concept` (the `comparator.compare(...)`, complexity, return) unchanged. Note `check_single_concept` already deep-copies at its top; `preprocess_pair` deep-copies again (harmless, keeps the method self-contained for the debugger). Keep both — correctness over micro-optimization.

- [ ] **Step 4: Run test to verify it passes**

Run: `natural-agi/bin/pytest src/classification/test_preprocess_pair.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/classification/concept_minor_classifier.py src/classification/test_preprocess_pair.py
git commit -m "refactor: extract preprocess_pair seam for shared preprocessing"
```

---

### Task 4: `comparison_figure` + `cost_color` in plotting.py

Add the Option A figure (two panels + cost-colored correspondence lines + halos), composed from existing pure helpers.

**Files:**
- Modify: `src/concept_creator/visualization/plotting.py`
- Test: `src/concept_creator/visualization/test_plotting.py` (append)

**Interfaces:**
- Consumes: payload graphs `{"nodes":[{"id","labels","normalized_x"|"x","normalized_y"|"y"}], "links":[...]}` and `edit_ops` rows from Task 1 (`build_edit_operations`).
- Produces: `cost_color(cost: float) -> str`; `comparison_figure(image_graph: dict, concept_graph: dict, edit_ops: list, *, height: int = 420) -> go.Figure`.

- [ ] **Step 1: Write the failing test**

Append to `src/concept_creator/visualization/test_plotting.py`:

```python
import plotting


def _payload(prefix):
    return {
        "nodes": [
            {"id": f"{prefix}1", "labels": ["Point", "EndPoint"],
             "normalized_x": 0.2, "normalized_y": 0.3},
            {"id": f"{prefix}2", "labels": ["Point", "CornerPoint"],
             "normalized_x": 0.6, "normalized_y": 0.7},
        ],
        "links": [{"source": f"{prefix}1", "target": f"{prefix}2"}],
    }


def test_cost_color_bands():
    assert plotting.cost_color(0.0) == "#22c55e"
    assert plotting.cost_color(10.0) == "#f87171"
    assert plotting.cost_color(0.7) != plotting.cost_color(0.0)


def test_comparison_figure_trace_count():
    img = _payload("i")
    con = _payload("c")
    edit_ops = [
        {"kind": "node", "op": "MATCH", "image_ref": "i1",
         "concept_ref": "c1", "cost": 0.0, "reason": ""},
        {"kind": "node", "op": "DELETE", "image_ref": "i2",
         "concept_ref": None, "cost": 0.65, "reason": "no slot"},
    ]
    fig = plotting.comparison_figure(img, con, edit_ops)
    # 2 edge + 2 node base traces, 1 correspondence line, 1 halo trace
    assert len(fig.data) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/concept_creator/visualization && ../../../natural-agi/bin/pytest test_plotting.py -k "cost_color or comparison" -v`
Expected: FAIL — `AttributeError: module 'plotting' has no attribute 'cost_color'`.

- [ ] **Step 3: Implement `cost_color` and `comparison_figure`**

Append to `src/concept_creator/visualization/plotting.py`:

```python
def cost_color(cost: float) -> str:
    if cost <= 0.0:
        return "#22c55e"   # match
    if cost < 0.34:
        return "#86efac"   # minor
    if cost < 0.67:
        return "#f59e0b"   # general
    if cost < 1.0:
        return "#fb7185"   # severe
    return "#f87171"       # no-match / impossible


def comparison_figure(image_graph: dict, concept_graph: dict,
                      edit_ops: list, *, height: int = 420) -> go.Figure:
    # Base traces index pos by the RAW node id (may be int); edit_ops refs are
    # stringified, so keep a separate str-keyed lookup for matching them.
    pos_img_raw = node_positions(image_graph, 0.0)
    pos_con_raw = node_positions(concept_graph, PANEL_OFFSET)

    base = [
        _edge_trace(image_graph, pos_img_raw), _node_trace(image_graph, pos_img_raw),
        _edge_trace(concept_graph, pos_con_raw), _node_trace(concept_graph, pos_con_raw),
    ]

    pos_img = {str(k): v for k, v in pos_img_raw.items()}
    pos_con = {str(k): v for k, v in pos_con_raw.items()}

    lines, halo_x, halo_y = [], [], []
    for op in edit_ops:
        if op.get("kind") != "node":
            continue
        if op["op"] in ("MATCH", "SUBSTITUTE"):
            a = pos_img.get(str(op["image_ref"]))
            b = pos_con.get(str(op["concept_ref"]))
            if a and b:
                lines.append(go.Scatter(
                    x=[a[0], b[0]], y=[a[1], b[1]], mode="lines",
                    line=dict(color=cost_color(op["cost"]), width=2.2),
                    opacity=0.6, hoverinfo="text",
                    hovertext=f"{op['reason']} · cost={op['cost']:.2f}",
                    showlegend=False))
        elif op["op"] == "DELETE":
            p = pos_img.get(str(op["image_ref"]))
            if p:
                halo_x.append(p[0]); halo_y.append(p[1])
        elif op["op"] == "INSERT":
            p = pos_con.get(str(op["concept_ref"]))
            if p:
                halo_x.append(p[0]); halo_y.append(p[1])

    halo = []
    if halo_x:
        halo = [go.Scatter(
            x=halo_x, y=halo_y, mode="markers",
            marker=dict(size=22, color="rgba(0,0,0,0)",
                        line=dict(color="#f87171", width=1.6)),
            hoverinfo="skip", showlegend=False)]

    fig = go.Figure(data=base + lines + halo)
    offsets = [0.0, PANEL_OFFSET]
    x_range = [min(offsets) - PANEL_HALF_WIDTH - 0.16,
               max(offsets) + PANEL_HALF_WIDTH + 0.16]
    y_range = [-PANEL_HALF_HEIGHT - 0.12, PANEL_HALF_HEIGHT + 0.12]
    _figure_layout(fig, height=height, margin=dict(l=12, r=12, t=40, b=20),
                   x_range=x_range, y_range=y_range)
    annotations = [
        dict(x=0.0, y=1.04, xref="x", yref="paper", text="<b>Image</b>",
             showarrow=False, xanchor="center", yanchor="bottom",
             font=dict(color=TEXT, size=12)),
        dict(x=PANEL_OFFSET, y=1.04, xref="x", yref="paper",
             text="<b>Expected concept</b>", showarrow=False,
             xanchor="center", yanchor="bottom", font=dict(color=TEXT, size=12)),
    ]
    fig.update_layout(annotations=annotations, shapes=_panel_shapes(offsets))
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/concept_creator/visualization && ../../../natural-agi/bin/pytest test_plotting.py -k "cost_color or comparison" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/concept_creator/visualization/plotting.py src/concept_creator/visualization/test_plotting.py
git commit -m "feat: add comparison_figure for image-vs-concept GED rendering"
```

---

### Task 5: `ged_breakdown.py` — glue module

Tie Neo4j fetch + prod preprocessing + path-capturing GED + edit-ops into one import-only module.

**Files:**
- Create: `src/training/ged_breakdown.py`
- Test: `src/training/test_ged_breakdown.py` (create)

**Interfaces:**
- Produces:
  - `get_image_graph_if_present(driver, image_id) -> nx.Graph | None` (None when graph has 0 nodes)
  - `expected_concepts(all_concept_ids, classification_results, expected_class) -> list[dict]` — rows `{"concept_id": str, "similarity": float|None}`, expected-class only, scored-first then by similarity desc
  - `_run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout) -> dict`
  - `compute_breakdown(image_graph, concept_id, concept_graph, ged_timeout=5.0) -> dict` with keys `image_nodelink, concept_nodelink, edit_ops, cost, n1, n2, similarity`
- Consumes: Task 1 `build_edit_operations`, Task 2 `compare_graphs_ged_with_path`, Task 3 `ConceptMinorClassifier.preprocess_pair`, prod `ImageRepository`.

- [ ] **Step 1: Write the failing test**

Create `src/training/test_ged_breakdown.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import networkx as nx

import ged_breakdown


def _node_graph(n):
    g = nx.Graph()
    for i in range(1, n + 1):
        g.add_node(i, labels=["Point", "EndPoint"],
                   normalized_x=0.1 * i, normalized_y=0.2 * i)
    if n >= 2:
        g.add_edge(1, 2)
    return g


def test_expected_concepts_filters_sorts_annotates():
    all_ids = ["3_1", "7_1", "7_2", "9_2"]
    results = [
        {"concept_id": "7_1", "similarity": 0.67},
        {"concept_id": "3_1", "similarity": 0.74},
    ]
    rows = ged_breakdown.expected_concepts(all_ids, results, "7")
    assert [r["concept_id"] for r in rows] == ["7_1", "7_2"]
    assert rows[0]["similarity"] == 0.67   # scored first
    assert rows[1]["similarity"] is None   # 7_2 pre-filtered


def test_get_image_graph_if_present_returns_none_on_empty(monkeypatch):
    monkeypatch.setattr(ged_breakdown, "ImageRepository",
                        lambda driver: type("R", (), {"get_image_graph": lambda self, i: nx.Graph()})())
    assert ged_breakdown.get_image_graph_if_present(None, "img1") is None


def test_run_ged_breakdown_returns_payload():
    out = ged_breakdown._run_ged_breakdown(_node_graph(2), _node_graph(2), "7_1", 5.0)
    assert set(out) == {"image_nodelink", "concept_nodelink", "edit_ops",
                        "cost", "n1", "n2", "similarity"}
    assert "nodes" in out["image_nodelink"] and "links" in out["image_nodelink"]
    assert 0.0 <= out["similarity"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `natural-agi/bin/pytest src/training/test_ged_breakdown.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ged_breakdown'`.

- [ ] **Step 3: Implement `ged_breakdown.py`**

Create `src/training/ged_breakdown.py`:

```python
import json
import sys
from pathlib import Path

import networkx as nx

_REPO = Path(__file__).resolve().parents[2]
_CLASSIFICATION = _REPO / "src" / "classification"
if str(_CLASSIFICATION) not in sys.path:
    sys.path.insert(0, str(_CLASSIFICATION))

from repository.image_repository import ImageRepository
from concept_minor_classifier import ConceptMinorClassifier
from graph_similarity.graph_edit_distance_comparator import (
    GraphEditDistanceComparator,
    build_edit_operations,
)


def _class_of(concept_id: str) -> str:
    return concept_id.split("_")[0]


def _to_payload(g: nx.Graph) -> dict:
    return json.loads(json.dumps(
        nx.node_link_data(g, edges="links"),
        default=lambda o: float(o) if _is_number(o) else str(o),
    ))


def _is_number(o) -> bool:
    try:
        float(o)
        return True
    except (TypeError, ValueError):
        return False


def get_image_graph_if_present(driver, image_id: str):
    graph = ImageRepository(driver).get_image_graph(image_id)
    if graph is None or graph.number_of_nodes() == 0:
        return None
    return graph


def expected_concepts(all_concept_ids, classification_results, expected_class) -> list:
    sims = {r["concept_id"]: r.get("similarity")
            for r in classification_results if "concept_id" in r}
    rows = [{"concept_id": cid, "similarity": sims.get(cid)}
            for cid in all_concept_ids if _class_of(cid) == str(expected_class)]
    rows.sort(key=lambda r: (r["similarity"] is None,
                             -(r["similarity"] or 0.0), r["concept_id"]))
    return rows


def _run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout) -> dict:
    similarity, cost, node_path, edge_path = (
        GraphEditDistanceComparator.compare_graphs_ged_with_path(
            prep_image, prep_concept, concept_id, ged_timeout)
    )
    edit_ops = build_edit_operations(node_path, edge_path, prep_image, prep_concept)
    return {
        "image_nodelink": _to_payload(prep_image),
        "concept_nodelink": _to_payload(prep_concept),
        "edit_ops": edit_ops,
        "cost": cost,
        "n1": prep_image.number_of_nodes() + prep_image.number_of_edges(),
        "n2": prep_concept.number_of_nodes() + prep_concept.number_of_edges(),
        "similarity": similarity,
    }


def compute_breakdown(image_graph, concept_id, concept_graph, ged_timeout: float = 5.0) -> dict:
    prep_image, prep_concept = ConceptMinorClassifier().preprocess_pair(
        image_graph, concept_graph
    )
    return _run_ged_breakdown(prep_image, prep_concept, concept_id, ged_timeout)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `natural-agi/bin/pytest src/training/test_ged_breakdown.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training/ged_breakdown.py src/training/test_ged_breakdown.py
git commit -m "feat: add ged_breakdown glue for misclassification drill-down"
```

---

### Task 6: Wire the drill-down into the dashboard expander

**Files:**
- Modify: `src/training/dashboard.py`
- Test: `src/training/test_dashboard_drilldown.py` (create)

**Interfaces:**
- Consumes: Task 5 `ged_breakdown.*`, Task 4 `plotting.comparison_figure`/`figure_html`, existing `load_concept_graph`, `get_all_concept_ids`.

- [ ] **Step 1: Write the failing test (AppTest smoke, both branches)**

Create `src/training/test_dashboard_drilldown.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import neo4j
import pandas as pd
from streamlit.testing.v1 import AppTest

DASHBOARD = os.path.join(os.path.dirname(__file__), "dashboard.py")


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, *a, **k):
        return []


class _FakeDriver:
    def session(self):
        return _FakeSession()

    def close(self):
        pass


def _make_run(tmp_path):
    run = tmp_path / "training_results" / "run_test"
    run.mkdir(parents=True)
    pd.DataFrame([{
        "image_id": "img1", "image_path": "/x/7.png",
        "expected": "7", "predicted": "3", "status": "success",
        "classification_results": '[{"concept_id": "3_1", "is_minor": true, "similarity": 0.74}, '
                                  '{"concept_id": "7_1", "is_minor": true, "similarity": 0.67}]',
    }]).to_csv(run / "incorrect_results.csv", index=False)
    return run


def test_dashboard_drilldown_renders(tmp_path, monkeypatch):
    _make_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    # Patch the shared neo4j class object so every `from neo4j import GraphDatabase`
    # in the executed script resolves to the fake (no live Neo4j needed). Empty
    # query results → "No concept of class 7" branch renders deterministically.
    monkeypatch.setattr(neo4j.GraphDatabase, "driver", lambda *a, **k: _FakeDriver())

    at = AppTest.from_file(DASHBOARD, default_timeout=60).run()

    assert not at.exception
    assert any("No concept of class" in i.value for i in at.info)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `natural-agi/bin/pytest src/training/test_dashboard_drilldown.py -v`
Expected: FAIL — no `st.info` containing "No concept of class" (the drill-down block is not wired into the expander yet), or an ImportError until `ged_breakdown`/`plotting` imports are added.

- [ ] **Step 3: Wire the dashboard**

In `src/training/dashboard.py`, add imports near the top (after the existing imports), making `plotting` importable:

```python
import sys
from pathlib import Path

_VIZ = Path(__file__).resolve().parents[1] / "concept_creator" / "visualization"
if str(_VIZ) not in sys.path:
    sys.path.insert(0, str(_VIZ))

import plotting
import ged_breakdown
```

Add a cached Neo4j driver helper (after the `NEO4J_*` constants):

```python
@st.cache_resource
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
```

Add a cached breakdown wrapper (near `load_concept_graph`):

```python
@st.cache_data(ttl=300)
def cached_breakdown(run: str, image_id: str, concept_id: str) -> dict | None:
    graph = ged_breakdown.get_image_graph_if_present(get_driver(), image_id)
    if graph is None:
        return None
    concept_graph = load_concept_graph(concept_id)["graph"]
    return ged_breakdown.compute_breakdown(graph, concept_id, concept_graph)
```

Inside the `tab_incorrect` per-row `with st.expander(...)` block, AFTER the existing results table, append the drill-down:

```python
                st.markdown("---")
                st.caption("Image vs. expected concept — GED penalty breakdown")
                expected = str(row["expected"])
                try:
                    all_ids = get_all_concept_ids()
                except Exception:
                    all_ids = []
                try:
                    results_list = json.loads(row["classification_results"])
                except (json.JSONDecodeError, TypeError):
                    results_list = []
                cand = ged_breakdown.expected_concepts(all_ids, results_list, expected)
                if not cand:
                    st.info(f"No concept of class {expected} in Neo4j.")
                else:
                    labels = [
                        f"{c['concept_id']} "
                        + (f"(sim {c['similarity']:.3f})" if c["similarity"] is not None
                           else "(pre-filtered)")
                        for c in cand
                    ]
                    pick = st.selectbox("Expected concept", labels, key=f"exp_{idx}")
                    concept_id = cand[labels.index(pick)]["concept_id"]
                    try:
                        bd = cached_breakdown(selected_run, str(row["image_id"]), concept_id)
                    except Exception as e:
                        bd = None
                        st.warning(f"Breakdown unavailable: {e}")
                    if bd is None:
                        st.info(
                            "Image graph not in Neo4j (run cleaned / "
                            "delete_image_nodes=True). Re-run classification with "
                            "delete_image_nodes=False to enable the breakdown."
                        )
                    else:
                        st.caption(
                            f"GED cost {bd['cost']:.2f} · n1 {bd['n1']} · n2 {bd['n2']} "
                            f"· similarity {bd['similarity']:.3f}"
                        )
                        fig = plotting.comparison_figure(
                            bd["image_nodelink"], bd["concept_nodelink"], bd["edit_ops"]
                        )
                        components.html(
                            plotting.figure_html(fig),
                            height=int(fig.layout.height or 420) + 8,
                            scrolling=False,
                        )
                        ops_df = pd.DataFrame([
                            o for o in bd["edit_ops"] if o["op"] != "MATCH"
                        ])
                        if not ops_df.empty:
                            st.dataframe(ops_df, use_container_width=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `natural-agi/bin/pytest src/training/test_dashboard_drilldown.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/training/dashboard.py src/training/test_dashboard_drilldown.py
git commit -m "feat: add image-vs-expected-concept drill-down to dashboard"
```

---

### Task 7: Visual verification with `/playwright-expert`

Acceptance gate per the request ("visually clean, verify with /playwright-expert"). Not a code-commit task; may loop back to Task 4/6 for spacing fixes.

**Files:** none (verification). Any fix loops back to the relevant task with its own commit.

- [ ] **Step 1: Populate Neo4j with debuggable image graphs**

Start services and run a small classification batch with image nodes retained:
Run: `make start_services && make create_kafka_topics`
Then run a short test through `training.ipynb` / `evaluation.py` passing `params={"delete_image_nodes": False}` so image graphs persist in Neo4j (enough images to produce ≥1 misclassification with a `run_*` dir under `training_results/`).

- [ ] **Step 2: Launch the dashboard**

Run: `make dashboard`
Expected: Streamlit serves on `http://localhost:8501`.

- [ ] **Step 3: Drive + screenshot with the playwright-expert skill**

Invoke the `fullstack-dev-skills:playwright-expert` skill to: open `http://localhost:8501`, select the populated run, open the **Misclassifications** tab, expand a misclassified row, select the expected concept, and screenshot the drill-down.

- [ ] **Step 4: Verify visual acceptance criteria**

Confirm in the screenshot: two labeled panels (Image | Expected concept) render; correspondence lines are visible and color-graded (green→red); deleted image nodes show the red dashed halo; the penalty table is legible with non-MATCH rows; dark theme is consistent with the formation viz; nothing overflows the expander. If any criterion fails, fix in Task 4 (figure sizing/colors) or Task 6 (layout/height) and re-verify.

- [ ] **Step 5: Final regression run**

Run: `natural-agi/bin/pytest src/classification/graph_similarity/test_edit_operations.py src/classification/graph_similarity/test_ged_with_path.py src/classification/test_preprocess_pair.py src/training/test_ged_breakdown.py src/training/test_dashboard_drilldown.py -v && cd src/concept_creator/visualization && ../../../natural-agi/bin/pytest test_plotting.py -v`
Expected: all PASS.

---

## Notes for the implementer

- The drill-down is a **debug-while-fresh** tool: image graphs only exist in Neo4j when the run used `delete_image_nodes=False`. The absence note is the expected state for older/cleaned runs — it is not a bug.
- `plotting.py` must stay pure (plotly + stdlib + networkx only). Do not import classification/training code into it.
- `node_positions` prefers `normalized_x/y` and falls back to `x/y`; image and concept graphs both carry `normalized_x/y`, so both panels share a coordinate basis.
- If `optimize_edit_paths` is slow on large graphs, the `ged_timeout` (default 5.0s) bounds it; the best path found so far is used (same anytime behavior as prod).
