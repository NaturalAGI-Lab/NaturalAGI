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
