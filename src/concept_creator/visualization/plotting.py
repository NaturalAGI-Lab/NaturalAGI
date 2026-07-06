"""
plotting.py — Plotly figures + helpers over runner payload dicts.

Operates ONLY on plain payload data (node-link dicts). MUST NOT import from
src/ or probes/ — the Streamlit app imports this module, and the app process
must stay decoupled from concept_creator code.
"""
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

LABEL_COLORS = {
    "StartPoint": "#ff4d5a",
    "EndPoint": "#f59e0b",
    "IntersectionPoint": "#a855f7",
    "CornerPoint": "#22c55e",
}
LABEL_SYMBOLS = {
    "StartPoint": "star",
    "EndPoint": "diamond",
    "IntersectionPoint": "x",
    "CornerPoint": "circle",
}
DEFAULT_COLOR = "#8b95a7"
DEFAULT_SYMBOL = "circle"
PANEL_OFFSET = 2.75
PANEL_HALF_WIDTH = 1.08
PANEL_HALF_HEIGHT = 1.08
SUSPECT_WIDTH = 0.6
PAPER_BG = "#0b1017"
PLOT_BG = "#0f1722"
PANEL_BG = "#121c28"
PANEL_BORDER = "#263241"
TEXT = "#e6edf3"
MUTED_TEXT = "#9aa7b7"
EDGE = "#8c98a8"
PAIR_PALETTE = [
    "#38bdf8", "#f59e0b", "#a855f7", "#22c55e", "#f472b6",
    "#facc15", "#2dd4bf", "#fb7185", "#818cf8", "#a3e635",
]
PAIR_OPACITY = 0.5
GRID = "#243140"


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


def node_symbol(node: dict) -> str:
    for label, symbol in LABEL_SYMBOLS.items():
        if label in node.get("labels", []):
            return symbol
    return DEFAULT_SYMBOL


def node_positions(graph: dict, x_offset: float = 0.0) -> dict:
    pos = {}
    for node in graph["nodes"]:
        x = coord_val(node.get("normalized_x", node.get("x", 0.0)))
        y = coord_val(node.get("normalized_y", node.get("y", 0.0)))
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
                      line=dict(color=EDGE, width=1.7),
                      opacity=0.65, hoverinfo="skip", showlegend=False)


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
        mode="markers",
        marker=dict(
            size=13,
            color=[node_color(n) for n in graph["nodes"]],
            symbol=[node_symbol(n) for n in graph["nodes"]],
            line=dict(color=PLOT_BG, width=1.5),
        ),
        customdata=[str(i) for i in ids],  # node id, surfaced on click-to-copy
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


def _event_endpoint(event: dict, pos: dict, node_key: str,
                    x_key: str, y_key: str, x_offset: float = 0.0):
    node_id = event.get(node_key)
    if node_id in pos:
        return pos[node_id]
    return pos.get(_nearest(pos, event.get(x_key, 0.0) + x_offset,
                            -event.get(y_key, 0.0)))


def _correspondence_pairs(events: list[dict], pos_before: dict,
                          pos_sample: dict) -> list[dict]:
    """Build correspondence lines from `merge` events — the actual node pairs
    that production formation merged. Endpoints resolve to the nearest plotted
    node of the concept-side (g) and image-side (h) merge coordinates."""
    pairs = []
    for ev in events:
        if ev.get("type") != "merge":
            continue
        a = _event_endpoint(ev, pos_before, "node_c", "g_x", "g_y")
        b = _event_endpoint(ev, pos_sample, "node_i", "h_x", "h_y",
                            x_offset=PANEL_OFFSET)
        if a is None or b is None:
            continue
        pairs.append({"a": a, "b": b, "distance": ev.get("distance", 0.0)})
    return pairs


def _pair_color(index: int) -> str:
    return PAIR_PALETTE[index % len(PAIR_PALETTE)]


def _pair_trace(pair: dict, color: str, visible: bool = True) -> go.Scatter:
    return go.Scatter(
        x=[pair["a"][0], pair["b"][0]], y=[pair["a"][1], pair["b"][1]],
        mode="lines", line=dict(color=color, width=1.8),
        opacity=PAIR_OPACITY, visible=visible, hoverinfo="text",
        hovertext=f"distance={pair['distance']:.3f}", showlegend=False,
    )


def _panel_shapes(offsets: list[float]) -> list[dict]:
    shapes = []
    for off in offsets:
        shapes.append(dict(
            type="rect", xref="x", yref="y", layer="below",
            x0=off - PANEL_HALF_WIDTH, x1=off + PANEL_HALF_WIDTH,
            y0=-PANEL_HALF_HEIGHT, y1=PANEL_HALF_HEIGHT,
            fillcolor=PANEL_BG, line=dict(color=PANEL_BORDER, width=1),
        ))
        shapes.append(dict(
            type="line", xref="x", yref="y", layer="below",
            x0=off - PANEL_HALF_WIDTH, x1=off + PANEL_HALF_WIDTH,
            y0=0, y1=0, line=dict(color=GRID, width=0.8),
        ))
        shapes.append(dict(
            type="line", xref="x", yref="y", layer="below",
            x0=off, x1=off, y0=-PANEL_HALF_HEIGHT, y1=PANEL_HALF_HEIGHT,
            line=dict(color=GRID, width=0.8),
        ))
    return shapes


def _figure_layout(fig: go.Figure, *, height: int, margin: dict,
                   x_range=None, y_range=None, equal_aspect: bool = False) -> None:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT, family="Avenir Next, Helvetica, Arial, sans-serif"),
        height=height,
        margin=margin,
        showlegend=False,
        hoverlabel=dict(bgcolor="#172232", bordercolor=PANEL_BORDER,
                        font=dict(color=TEXT)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, range=x_range)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False, range=y_range)
    if equal_aspect:
        # Lock 1:1 data aspect so node geometry is preserved regardless of the
        # container width. Without it, a wide-but-short panel stretches x vs y
        # and shears near-vertical shapes to the right (a "1" looked ~70° instead
        # of its true ~28° lean). `constrain="domain"` keeps the set ranges and
        # letterboxes the panel rather than expanding the visible range.
        fig.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain")
        fig.update_xaxes(constrain="domain")


# Click a node marker to copy its id. Runs inside the components.html iframe,
# where navigator.clipboard is frequently blocked by permissions-policy, so we
# try the async API first and fall back to execCommand on the click gesture.
_CLICK_TO_COPY_JS = """
<div id="copy-toast" style="position:fixed;bottom:14px;left:50%;
  transform:translateX(-50%);background:#172232;color:#e6edf3;
  border:1px solid #263241;border-radius:6px;padding:6px 12px;
  font:13px/1.3 'Avenir Next',Helvetica,Arial,sans-serif;opacity:0;
  transition:opacity .2s;pointer-events:none;z-index:9999;"></div>
<script>
(function(){
  function fallbackCopy(text){
    try{
      var ta=document.createElement('textarea');ta.value=text;
      ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);
      ta.focus();ta.select();var ok=document.execCommand('copy');
      document.body.removeChild(ta);return ok;
    }catch(e){return false;}
  }
  function attach(){
    var gd=document.querySelector('.plotly-graph-div');
    if(!gd||!gd.on){return setTimeout(attach,120);}
    var toast=document.getElementById('copy-toast');
    function showToast(t){toast.textContent=t;toast.style.opacity='1';
      clearTimeout(toast._t);toast._t=setTimeout(function(){toast.style.opacity='0';},1500);}
    gd.on('plotly_hover',function(ev){
      if(ev&&ev.points&&ev.points.length&&ev.points[0].customdata!=null)gd.style.cursor='pointer';});
    gd.on('plotly_unhover',function(){gd.style.cursor='';});
    gd.on('plotly_click',function(ev){
      if(!ev||!ev.points||!ev.points.length)return;
      var id=ev.points[0].customdata;
      if(id==null)return;
      id=String(id);
      function ok(){showToast('Copied id: '+id);}
      function fail(){showToast(fallbackCopy(id)?('Copied id: '+id):('Copy failed: '+id));}
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(id).then(ok).catch(fail);
      }else{fail();}
    });
  }
  attach();
})();
</script>
"""


def figure_html(fig: go.Figure, *, auto_play: bool = False,
                include_plotlyjs: bool | str = True) -> str:
    height = int(fig.layout.height or 560)
    body = pio.to_html(
        fig,
        auto_play=auto_play,
        config={"displaylogo": False, "responsive": True},
        default_height=f"{height}px",
        default_width="100%",
        full_html=False,
        include_plotlyjs=include_plotlyjs,
    )
    return (
        "<!doctype html><html><head><style>"
        "html,body{margin:0;background:#0b1017;overflow:hidden;}"
        "</style></head><body>"
        f"{body}"
        f"{_CLICK_TO_COPY_JS}"
        "</body></html>"
    )


def step_figure(step: dict, correspondence_events: list[dict],
                animate: bool = False) -> go.Figure:
    result_title = (
        "✗ no common minor (formation failed)"
        if step.get("is_exception")
        else "Merged result"
    )
    panels = [
        ("Concept (before)", step["concept_before"], 0.0),
        ("Sample", step["sample"], PANEL_OFFSET),
        (result_title, step["concept_after"], 2 * PANEL_OFFSET),
    ]
    base, annotations, positions = [], [], {}
    for title, graph, off in panels:
        pos = node_positions(graph, off)
        positions[title] = pos
        base += [_edge_trace(graph, pos), _node_trace(graph, pos)]
        annotations.append(dict(
            x=off, y=1.04, xref="x", yref="paper",
            text=f"<b>{title}</b>",
            showarrow=False, xanchor="center", yanchor="bottom",
            font=dict(color=TEXT, size=12),
        ))

    pairs = _correspondence_pairs(
        correspondence_events, positions["Concept (before)"], positions["Sample"]
    )
    lines = [_pair_trace(p, _pair_color(i), visible=not animate)
             for i, p in enumerate(pairs)]
    fig = go.Figure(data=base + lines)

    if animate and pairs:
        trace_idx = list(range(len(base) + len(pairs)))
        fig.frames = [
            go.Frame(
                name=str(k),
                traces=trace_idx,
                data=base + [
                    _pair_trace(p, _pair_color(j), visible=(j < k))
                    for j, p in enumerate(pairs)
                ],
            )
            for k in range(len(pairs) + 1)
        ]
        fig.update_layout(updatemenus=[dict(
            type="buttons", direction="right", x=0.0, y=1.14,
            xanchor="left", yanchor="top",
            bgcolor="#172232", bordercolor=PANEL_BORDER, borderwidth=1,
            font=dict(color=TEXT, size=12),
            pad=dict(t=2, r=4, b=2, l=4),
            buttons=[
                dict(label="Play", method="animate",
                     args=[None, {
                         "frame": {"duration": 600, "redraw": True},
                         "transition": {"duration": 0},
                         "fromcurrent": True,
                     }]),
                dict(label="Pause", method="animate",
                     args=[[None], {"mode": "immediate"}]),
            ],
        )])

    offsets = [panel[2] for panel in panels]
    x_range = [
        min(offsets) - PANEL_HALF_WIDTH - 0.16,
        max(offsets) + PANEL_HALF_WIDTH + 0.16,
    ]
    y_range = [-PANEL_HALF_HEIGHT - 0.12, PANEL_HALF_HEIGHT + 0.12]
    _figure_layout(fig, height=560, margin=dict(l=12, r=12, t=72, b=20),
                   x_range=x_range, y_range=y_range, equal_aspect=True)
    fig.update_layout(annotations=annotations, shapes=_panel_shapes(offsets))
    return fig


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
                   x_range=x_range, y_range=y_range, equal_aspect=True)
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


def single_graph_figure(graph: dict, *, title: str = "Skeleton",
                        height: int = 320) -> go.Figure:
    """One-panel formation-viz render of an arbitrary node-link graph.

    Auto-ranges to the node positions so it is robust whether the graph
    carries normalized coords (~0..1) or raw pixel coords (~0..100)."""
    pos = node_positions(graph, 0.0)
    fig = go.Figure(data=[_edge_trace(graph, pos), _node_trace(graph, pos)])
    if pos:
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        pad_x = max((max(xs) - min(xs)) * 0.12, 0.1)
        pad_y = max((max(ys) - min(ys)) * 0.12, 0.1)
        x_range = [min(xs) - pad_x, max(xs) + pad_x]
        y_range = [min(ys) - pad_y, max(ys) + pad_y]
    else:
        x_range = [-PANEL_HALF_WIDTH, PANEL_HALF_WIDTH]
        y_range = [-PANEL_HALF_HEIGHT, PANEL_HALF_HEIGHT]
    _figure_layout(fig, height=height, margin=dict(l=12, r=12, t=36, b=12),
                   x_range=x_range, y_range=y_range, equal_aspect=True)
    fig.update_layout(annotations=[dict(
        x=0.5, y=1.0, xref="paper", yref="paper", text=f"<b>{title}</b>",
        showarrow=False, xanchor="center", yanchor="bottom",
        font=dict(color=TEXT, size=12))])
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
    _figure_layout(fig, height=420, margin=dict(l=12, r=12, t=34, b=12))
    fig.update_xaxes(visible=True, title="step", color=MUTED_TEXT,
                     gridcolor=GRID, showgrid=True, zeroline=False)
    fig.update_yaxes(visible=True, title="xy range width", color=MUTED_TEXT,
                     gridcolor=GRID, showgrid=True, zeroline=False)
    return fig
