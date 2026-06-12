"""
plotting.py — Plotly figures + helpers over runner payload dicts.

Operates ONLY on plain payload data (node-link dicts). MUST NOT import from
src/ or probes/ — the Streamlit app imports this module, and the app process
must stay decoupled from concept_creator code.
"""
from typing import Any

import plotly.graph_objects as go

LABEL_COLORS = {
    "StartPoint": "red",
    "EndPoint": "orange",
    "IntersectionPoint": "purple",
    "CornerPoint": "green",
}
DEFAULT_COLOR = "lightgray"
PANEL_OFFSET = 2.5
SUSPECT_WIDTH = 0.6


def coord_val(v: Any) -> float:
    if isinstance(v, dict):
        return float(v.get("center", v.get("min", 0.0)))
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def range_width(v: Any) -> float:
    if isinstance(v, dict) and "min" in v and "max" in v:
        return float(v["max"]) - float(v["min"])
    return 0.0


def node_color(node: dict) -> str:
    for label, color in LABEL_COLORS.items():
        if label in node.get("labels", []):
            return color
    return DEFAULT_COLOR


def node_positions(graph: dict, x_offset: float = 0.0) -> dict:
    pos = {}
    for node in graph["nodes"]:
        x = coord_val(node.get("normalized_x", 0.0))
        y = coord_val(node.get("normalized_y", 0.0))
        pos[node["id"]] = (x + x_offset, -y)  # invert y to match image coords
    return pos


def node_xy_width(node: dict) -> float:
    return (range_width(node.get("normalized_x"))
            + range_width(node.get("normalized_y"))) / 2


def mean_xy_width(graph: dict) -> float:
    nodes = graph["nodes"]
    if not nodes:
        return 0.0
    return sum(node_xy_width(n) for n in nodes) / len(nodes)


def widest_nodes(graph: dict, k: int = 5) -> list[tuple]:
    widths = [(n["id"], node_xy_width(n)) for n in graph["nodes"]]
    widths.sort(key=lambda t: t[1], reverse=True)
    return widths[:k]


def _node_props(graph: dict, node_id) -> dict:
    for n in graph["nodes"]:
        if n["id"] == node_id:
            return n
    return {}


def widening_history(steps: list[dict], node_id) -> list[dict]:
    """Per property: the steps where this node's range width grew."""
    history = []
    prev = {}
    for step in steps:
        cur = _node_props(step["concept_after"], node_id)
        for prop, value in cur.items():
            w = range_width(value)
            if w <= 0.0:
                continue
            prev_w = range_width(prev.get(prop))
            if w > prev_w + 1e-9:
                history.append({
                    "step": step["step"],
                    "image_id": step["image_id"],
                    "property": prop,
                    "from_width": round(prev_w, 4),
                    "to_width": round(w, 4),
                })
        if cur:
            prev = cur
    return history


def _edge_trace(graph: dict, pos: dict) -> go.Scatter:
    xs, ys = [], []
    for link in graph["links"]:
        a, b = pos.get(link["source"]), pos.get(link["target"])
        if a is None or b is None:
            continue
        xs += [a[0], b[0], None]
        ys += [a[1], b[1], None]
    return go.Scatter(x=xs, y=ys, mode="lines",
                      line=dict(color="gray", width=1.5),
                      opacity=0.6, hoverinfo="skip", showlegend=False)


def _hover_text(node: dict) -> str:
    lines = [f"<b>{node['id']}</b>", ", ".join(node.get("labels", []))]
    for key, value in node.items():
        if key in ("id", "labels"):
            continue
        if isinstance(value, dict) and "min" in value:
            lines.append(f"{key}: [{value['min']:.3f}, {value['max']:.3f}]")
        else:
            lines.append(f"{key}: {value}")
    return "<br>".join(lines)


def _node_trace(graph: dict, pos: dict) -> go.Scatter:
    ids = [n["id"] for n in graph["nodes"]]
    return go.Scatter(
        x=[pos[i][0] for i in ids], y=[pos[i][1] for i in ids],
        mode="markers+text", text=[str(i) for i in ids],
        textposition="top center", textfont=dict(size=8),
        marker=dict(size=14, color=[node_color(n) for n in graph["nodes"]]),
        hovertext=[_hover_text(n) for n in graph["nodes"]],
        hoverinfo="text", showlegend=False,
    )


def _nearest(pos: dict, tx: float, ty: float):
    best, best_d = None, float("inf")
    for nid, (px, py) in pos.items():
        d = (px - tx) ** 2 + (py - ty) ** 2
        if d < best_d:
            best, best_d = nid, d
    return best


def _correspondence_pairs(merge_events: list[dict], pos_before: dict,
                          pos_sample: dict) -> list[dict]:
    pairs = []
    for ev in merge_events:
        if ev.get("type") != "merge":
            continue
        a = _nearest(pos_before, ev.get("g_x", 0.0), -ev.get("g_y", 0.0))
        b = _nearest(pos_sample, ev.get("h_x", 0.0) + PANEL_OFFSET, -ev.get("h_y", 0.0))
        if a is None or b is None:
            continue
        pairs.append({"a": pos_before[a], "b": pos_sample[b],
                      "mismatch": bool(ev.get("mismatch")),
                      "distance": ev.get("distance", 0.0)})
    return pairs


def _pair_trace(pair: dict, visible: bool = True) -> go.Scatter:
    color = "red" if pair["mismatch"] else "lightgray"
    width = 2.0 if pair["mismatch"] else 0.8
    return go.Scatter(
        x=[pair["a"][0], pair["b"][0]], y=[pair["a"][1], pair["b"][1]],
        mode="lines", line=dict(color=color, width=width), opacity=0.7,
        visible=visible, hoverinfo="text",
        hovertext=f"distance={pair['distance']:.3f}", showlegend=False,
    )


def step_figure(step: dict, merge_events: list[dict], animate: bool = False) -> go.Figure:
    panels = [
        ("Concept (before)", step["concept_before"], 0.0),
        ("Sample", step["sample"], PANEL_OFFSET),
        ("Merged result", step["concept_after"], 2 * PANEL_OFFSET),
    ]
    base, annotations, positions = [], [], {}
    for title, graph, off in panels:
        pos = node_positions(graph, off)
        positions[title] = pos
        base += [_edge_trace(graph, pos), _node_trace(graph, pos)]
        annotations.append(dict(x=off + 0.5, y=1.4, text=f"<b>{title}</b>",
                                showarrow=False, xanchor="center"))

    pairs = _correspondence_pairs(
        merge_events, positions["Concept (before)"], positions["Sample"]
    )
    lines = [_pair_trace(p, visible=not animate) for p in pairs]
    fig = go.Figure(data=base + lines)

    if animate and pairs:
        n0 = len(base)
        line_idx = list(range(n0, n0 + len(pairs)))
        fig.frames = [
            go.Frame(name=str(k), traces=line_idx,
                     data=[_pair_trace(p, visible=(j < k))
                           for j, p in enumerate(pairs)])
            for k in range(len(pairs) + 1)
        ]
        fig.update_layout(updatemenus=[dict(
            type="buttons", x=0.0, y=1.5,
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, {"frame": {"duration": 600, "redraw": False},
                                  "fromcurrent": True}]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], {"mode": "immediate"}]),
            ],
        )])

    fig.update_layout(
        annotations=annotations, height=480, showlegend=False,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="white",
    )
    return fig


def range_evolution_figure(steps: list[dict], k_widest: int = 5) -> go.Figure:
    xs = [s["step"] for s in steps]
    means = [mean_xy_width(s["concept_after"]) for s in steps]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=means, mode="lines+markers",
                             name="mean_xy_width", line=dict(width=3)))

    final = steps[-1]["concept_after"]
    for node_id, _ in widest_nodes(final, k=k_widest):
        ys = []
        for s in steps:
            node = _node_props(s["concept_after"], node_id)
            ys.append(node_xy_width(node) if node else None)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                                 name=f"node {node_id}", line=dict(dash="dot")))

    fig.add_hline(y=SUSPECT_WIDTH, line_color="red", line_dash="dash",
                  annotation_text=f"SUSPECT ≥ {SUSPECT_WIDTH}")
    fig.update_layout(xaxis_title="step", yaxis_title="xy range width",
                      height=420, margin=dict(l=10, r=10, t=30, b=10))
    return fig
