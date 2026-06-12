import pytest

from visualization import plotting

GRAPH = {
    "directed": False, "multigraph": False, "graph": {},
    "nodes": [
        {"id": 0, "labels": ["Point", "StartPoint"], "normalized_x": 0.1,
         "normalized_y": 0.2},
        {"id": 1, "labels": ["Point", "EndPoint"],
         "normalized_x": {"min": 0.0, "max": 1.0, "center": 0.5},
         "normalized_y": {"min": -0.2, "max": 0.2, "center": 0.0}},
    ],
    "links": [{"source": 0, "target": 1}],
}


def test_coord_val_scalar_and_range():
    assert plotting.coord_val(0.25) == 0.25
    assert plotting.coord_val({"min": 0.0, "max": 1.0, "center": 0.5}) == 0.5
    assert plotting.coord_val(None) == 0.0


def test_node_positions_offset_and_y_inversion():
    pos = plotting.node_positions(GRAPH, x_offset=2.5)
    assert pos[0] == (pytest.approx(2.6), pytest.approx(-0.2))
    assert pos[1] == (pytest.approx(3.0), pytest.approx(0.0))


def test_node_color_palette():
    assert plotting.node_color(GRAPH["nodes"][0]) == "red"      # StartPoint
    assert plotting.node_color(GRAPH["nodes"][1]) == "orange"   # EndPoint
    assert plotting.node_color({"labels": ["Point"]}) == "lightgray"


def test_mean_xy_width():
    # node 0: width 0; node 1: (1.0 + 0.4)/2 = 0.7  → mean = 0.35
    assert plotting.mean_xy_width(GRAPH) == pytest.approx(0.35)


def test_widest_nodes():
    top = plotting.widest_nodes(GRAPH, k=5)
    assert top[0] == (1, pytest.approx(0.7))
    assert len(top) == 2


def test_widening_history():
    # Step 1 mirrors reality: the initial concept is the first sample, whose
    # properties are still scalars (width 0) — no widening entries yet.
    scalar = {
        **GRAPH,
        "nodes": [
            GRAPH["nodes"][0],
            {"id": 1, "labels": ["Point", "EndPoint"],
             "normalized_x": 0.5, "normalized_y": 0.0},
        ],
    }
    wider = {
        **GRAPH,
        "nodes": [
            GRAPH["nodes"][0],
            {**GRAPH["nodes"][1],
             "normalized_y": {"min": -0.9, "max": 0.9, "center": 0.0}},
        ],
    }
    step1 = {"step": 1, "image_id": "a", "concept_after": scalar}
    step2 = {"step": 2, "image_id": "b", "concept_after": GRAPH}
    step3 = {"step": 3, "image_id": "c", "concept_after": wider}
    hist = plotting.widening_history([step1, step2, step3], node_id=1)
    # step 2: x 0→1.0 and y 0→0.4; step 3: y 0.4→1.8 (x unchanged)
    assert [(h["step"], h["property"]) for h in hist] == [
        (2, "normalized_x"), (2, "normalized_y"), (3, "normalized_y"),
    ]
    assert hist[2]["image_id"] == "c"
    assert hist[2]["from_width"] == pytest.approx(0.4)
    assert hist[2]["to_width"] == pytest.approx(1.8)


STEP = {
    "step": 2, "description": "Image 2/3: b", "image_id": "b",
    "concept_before": GRAPH, "sample": GRAPH, "concept_after": GRAPH,
}
MERGE_EVENTS = [
    {"type": "merge", "step": 2, "g_x": 0.1, "g_y": 0.2, "h_x": 0.1, "h_y": 0.2,
     "distance": 0.0, "mismatch": False},
    {"type": "merge", "step": 2, "g_x": 0.5, "g_y": 0.0, "h_x": 0.1, "h_y": 0.2,
     "distance": 0.45, "mismatch": True},
]


def test_step_figure_static_trace_count():
    fig = plotting.step_figure(STEP, MERGE_EVENTS, animate=False)
    # 3 panels x (edge trace + node trace) + 2 correspondence lines
    assert len(fig.data) == 8
    line_colors = [t.line.color for t in fig.data[6:]]
    assert "red" in line_colors


def test_step_figure_animated_frames():
    fig = plotting.step_figure(STEP, MERGE_EVENTS, animate=True)
    assert len(fig.data) == 8           # same traces, lines hidden in base
    assert len(fig.frames) == 3          # 0, 1, 2 pairs revealed
    assert all(not t.visible for t in fig.data[6:])


def test_range_evolution_figure():
    steps = [
        {"step": 1, "image_id": "a", "description": "", "concept_after": GRAPH},
        {"step": 2, "image_id": "b", "description": "", "concept_after": GRAPH},
    ]
    fig = plotting.range_evolution_figure(steps)
    # 1 mean trace + per-node traces for top widest final nodes (2 nodes here)
    assert len(fig.data) == 3
    assert fig.data[0].name == "mean_xy_width"
    # SUSPECT threshold rendered as a horizontal line shape
    assert any(s.type == "line" for s in fig.layout.shapes)
