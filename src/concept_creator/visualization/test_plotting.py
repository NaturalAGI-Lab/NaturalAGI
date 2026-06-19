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
    assert plotting.node_color(GRAPH["nodes"][0]) == "#ff4d5a"  # StartPoint
    assert plotting.node_color(GRAPH["nodes"][1]) == "#f59e0b"  # EndPoint
    assert plotting.node_color({"labels": ["Point"]}) == "#8b95a7"


def test_node_symbol_palette():
    assert plotting.node_symbol(GRAPH["nodes"][0]) == "star"
    assert plotting.node_symbol(GRAPH["nodes"][1]) == "diamond"
    assert plotting.node_symbol({"labels": ["Point"]}) == "circle"


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
PAIR_EVENTS = [
    {"type": "merge", "step": 2, "g_x": 0.5, "g_y": 0.0,
     "h_x": 0.5, "h_y": 0.0, "distance": 0.0},
    {"type": "merge", "step": 2, "g_x": 0.1, "g_y": 0.2,
     "h_x": 0.1, "h_y": 0.2, "distance": 0.45},
]


def test_step_figure_static_trace_count():
    fig = plotting.step_figure(STEP, PAIR_EVENTS, animate=False)
    # 3 panels x (edge trace + node trace) + 2 correspondence lines:
    # every actual merge is drawn, regardless of distance.
    assert len(fig.data) == 8
    line_a, line_b = fig.data[6], fig.data[7]
    assert fig.data[0].line.color == plotting.EDGE
    assert line_a.line.color == plotting.PAIR_PALETTE[0]
    assert line_b.line.color == plotting.PAIR_PALETTE[1]
    # no "potential match" styling: every line is solid (dash unset)
    assert line_a.line.dash is None
    assert line_b.line.dash is None
    assert line_a.opacity == pytest.approx(plotting.PAIR_OPACITY)
    assert line_b.opacity == pytest.approx(plotting.PAIR_OPACITY)
    assert fig.layout.plot_bgcolor == plotting.PLOT_BG
    assert fig.layout.paper_bgcolor == plotting.PAPER_BG
    assert len(fig.layout.shapes) == 9


def test_step_figure_matched_lines_get_distinct_colors():
    events = [
        {"type": "merge", "step": 2, "g_x": 0.1, "g_y": 0.2,
         "h_x": 0.1, "h_y": 0.2, "distance": 0.0},
        {"type": "merge", "step": 2, "g_x": 0.5, "g_y": 0.0,
         "h_x": 0.5, "h_y": 0.0, "distance": 0.1},
    ]
    fig = plotting.step_figure(STEP, events, animate=False)
    line_colors = [t.line.color for t in fig.data[6:]]
    assert line_colors == [plotting.PAIR_PALETTE[0], plotting.PAIR_PALETTE[1]]
    assert all(t.opacity == pytest.approx(plotting.PAIR_OPACITY)
               for t in fig.data[6:])


def test_step_figure_animated_frames():
    fig = plotting.step_figure(STEP, PAIR_EVENTS, animate=True)
    assert len(fig.data) == 8           # all matched lines, hidden in base
    assert len(fig.frames) == 3          # 0, 1, 2 pairs revealed
    assert all(not t.visible for t in fig.data[6:])
    assert all(len(frame.data) == len(fig.data) for frame in fig.frames)
    assert all(frame.data[1].mode == "markers" for frame in fig.frames)
    assert all(frame.data[3].mode == "markers" for frame in fig.frames)
    assert all(frame.data[5].mode == "markers" for frame in fig.frames)


def test_figure_html_autoplay_emits_animation_call():
    fig = plotting.step_figure(STEP, PAIR_EVENTS, animate=True)
    html = plotting.figure_html(fig, auto_play=True, include_plotlyjs=False)
    assert "Plotly.animate" in html
    assert "responsive" in html
    assert "background:#0b1017" in html


def test_step_figure_merge_lines_resolve_by_coordinate():
    fig = plotting.step_figure(STEP, PAIR_EVENTS, animate=False)
    line = fig.data[6]
    # merge events carry no node ids; endpoints resolve to the nearest plotted
    # node of the concept-side (g) and image-side (h) merge coordinates.
    assert line.x[0] == pytest.approx(0.5)
    assert line.y[0] == pytest.approx(0.0)
    assert line.x[1] == pytest.approx(plotting.PANEL_OFFSET + 0.5)
    assert line.y[1] == pytest.approx(0.0)


def test_correspondence_pairs_node_ids_override_nearest_snapping():
    pos_before = {
        "c0": (0.0, 0.0),
        "c1": (0.05, 0.0),
    }
    pos_sample = {
        "i0": (plotting.PANEL_OFFSET, 0.0),
        "i1": (plotting.PANEL_OFFSET + 0.05, 0.0),
    }
    events = [
        {"type": "merge", "step": 2, "node_c": "c0", "node_i": "i0",
         "g_x": 0.0, "g_y": 0.0, "h_x": 0.0, "h_y": 0.0,
         "distance": 0.0},
        {"type": "merge", "step": 2, "node_c": "c1", "node_i": "i1",
         "g_x": 0.0, "g_y": 0.0, "h_x": 0.0, "h_y": 0.0,
         "distance": 0.1},
    ]

    pairs = plotting._correspondence_pairs(events, pos_before, pos_sample)

    assert pairs == [
        {"a": pos_before["c0"], "b": pos_sample["i0"], "distance": 0.0},
        {"a": pos_before["c1"], "b": pos_sample["i1"], "distance": 0.1},
    ]
    assert {p["b"] for p in pairs} == {pos_sample["i0"], pos_sample["i1"]}


EMPTY_GRAPH = {"directed": False, "multigraph": False, "graph": {},
               "nodes": [], "links": []}
EXC_STEP = {
    "step": 3, "description": "EXCEPTION at image 3/5 (c): boom", "image_id": "c",
    "is_exception": True, "error_message": "boom",
    "concept_before": GRAPH, "sample": GRAPH, "concept_after": EMPTY_GRAPH,
}


def test_step_figure_exception_step_relabels_result_panel():
    fig = plotting.step_figure(EXC_STEP, [], animate=False)
    texts = [a.text for a in fig.layout.annotations]
    # third panel no longer claims a successful merge
    assert not any("Merged result" in t for t in texts)
    assert any("no common minor" in t.lower() for t in texts)
    # the two input panels are still labelled
    assert any("Concept" in t for t in texts)
    assert any("Sample" in t for t in texts)


def test_step_figure_normal_step_unchanged_without_is_exception():
    # regression guard: a step lacking is_exception keeps the success label
    fig = plotting.step_figure(STEP, PAIR_EVENTS, animate=False)
    texts = [a.text for a in fig.layout.annotations]
    assert any("Merged result" in t for t in texts)


def test_range_evolution_figure():
    steps = [
        {"step": 1, "image_id": "a", "description": "", "concept_after": GRAPH},
        {"step": 2, "image_id": "b", "description": "", "concept_after": GRAPH},
    ]
    fig = plotting.range_evolution_figure(steps)
    # 1 mean trace + per-node traces for top widest final nodes (2 nodes here)
    assert len(fig.data) == 3
    assert fig.data[0].name == "mean_xy_width"
    assert fig.layout.plot_bgcolor == plotting.PLOT_BG
    # SUSPECT threshold rendered as a horizontal line shape
    assert any(s.type == "line" for s in fig.layout.shapes)
