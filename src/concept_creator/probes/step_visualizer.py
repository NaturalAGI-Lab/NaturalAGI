"""
step_visualizer.py — render a 3-panel (concept | sample | merged) matplotlib figure
for one concept-formation step.  Uses Agg backend; no display required.
"""
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import ConnectionPatch
import networkx as nx


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

_LABEL_COLORS = {
    "StartPoint": "red",
    "EndPoint": "orange",
    "IntersectionPoint": "purple",
    "CornerPoint": "green",
}
_DEFAULT_COLOR = "lightgray"

_PANEL_X = [0.0, 0.35, 0.7]   # left edges of the three sub-axes in figure coords
_PANEL_W = 0.28


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _coord_val(v: Any) -> float:
    if isinstance(v, dict):
        return float(v.get("center", v.get("min", 0.0)))
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _range_width(v: Any) -> float:
    if isinstance(v, dict) and "min" in v and "max" in v:
        return float(v["max"]) - float(v["min"])
    return 0.0


def _node_color(data: dict) -> str:
    for label, color in _LABEL_COLORS.items():
        if label in data.get("labels", []):
            return color
    return _DEFAULT_COLOR


def _build_pos(graph: nx.Graph) -> dict:
    pos = {}
    for nid, data in graph.nodes(data=True):
        x = _coord_val(data.get("normalized_x", 0.0))
        y = _coord_val(data.get("normalized_y", 0.0))
        pos[nid] = (x, -y)   # invert y to match image coords
    return pos


def _draw_panel(ax: plt.Axes, graph: nx.Graph, title: str) -> dict:
    pos = _build_pos(graph)
    if not pos:
        ax.set_title(title)
        return pos

    colors = [_node_color(graph.nodes[n]) for n in graph.nodes()]
    nx.draw_networkx_edges(graph, pos, ax=ax, width=1.5, alpha=0.6, edge_color="gray")
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=colors, node_size=300)

    labels_short = {n: str(n) for n in graph.nodes()}
    nx.draw_networkx_labels(graph, pos, labels=labels_short, ax=ax, font_size=6)

    ax.set_title(title, fontsize=9)
    ax.axis("off")
    return pos


def _annotate_merged(ax: plt.Axes, graph: nx.Graph, pos: dict) -> None:
    for nid, data in graph.nodes(data=True):
        wy = _range_width(data.get("normalized_y"))
        if wy > 0.5:
            p = pos.get(nid)
            if p is None:
                continue
            ax.annotate(f"Δy={wy:.2f}", xy=p, fontsize=5, color="darkred",
                        xytext=(p[0] + 0.05, p[1] - 0.05))


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def render_step(
    concept_before: nx.Graph,
    image_graph: nx.Graph,
    concept_after: nx.Graph,
    merge_events_for_step: list[dict],
    out_png: Path,
) -> None:
    """
    Draw a 3-panel figure:
      panel 1: concept_before
      panel 2: image_graph
      panel 3: concept_after (merged result)

    Draw ConnectionPatch lines between panel-1 and panel-2 for each merge event:
      red line  → mismatch flag set
      thin gray → clean merge

    Annotate merged-result nodes with width_y when > 0.5.
    """
    fig = plt.figure(figsize=(14, 5))
    fig.suptitle("Concept formation step", fontsize=11)

    ax1 = fig.add_axes([_PANEL_X[0], 0.1, _PANEL_W, 0.8])
    ax2 = fig.add_axes([_PANEL_X[1], 0.1, _PANEL_W, 0.8])
    ax3 = fig.add_axes([_PANEL_X[2], 0.1, _PANEL_W, 0.8])

    pos1 = _draw_panel(ax1, concept_before, "Concept (before)")
    pos2 = _draw_panel(ax2, image_graph, "Sample")
    pos3 = _draw_panel(ax3, concept_after, "Merged result")
    _annotate_merged(ax3, concept_after, pos3)

    # Draw merge-event links between panel-1 and panel-2
    pos1_ax = {nid: ax1.transData.transform(p) for nid, p in pos1.items()}
    pos2_ax = {nid: ax2.transData.transform(p) for nid, p in pos2.items()}

    for ev in merge_events_for_step:
        if ev.get("type") != "merge":
            continue
        # We match by coords — find panel-1 node closest to (g_x, -g_y)
        gx, gy = ev.get("g_x", 0.0), -ev.get("g_y", 0.0)
        hx, hy = ev.get("h_x", 0.0), -ev.get("h_y", 0.0)

        def _nearest(pos_dict, tx, ty):
            best = None
            best_d = float("inf")
            for nid, (px, py) in pos_dict.items():
                d = math.sqrt((px - tx) ** 2 + (py - ty) ** 2)
                if d < best_d:
                    best_d = d
                    best = nid
            return best

        nid1 = _nearest(pos1, gx, gy)
        nid2 = _nearest(pos2, hx, hy)
        if nid1 is None or nid2 is None:
            continue

        color = "lightgray"
        lw = 0.8

        p1 = pos1.get(nid1)
        p2 = pos2.get(nid2)
        if p1 is None or p2 is None:
            continue

        con = ConnectionPatch(
            xyA=p1, coordsA=ax1.transData,
            xyB=p2, coordsB=ax2.transData,
            color=color, lw=lw, alpha=0.7,
            arrowstyle="-",
        )
        fig.add_artist(con)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_png), dpi=120, bbox_inches="tight")
    plt.close(fig)
