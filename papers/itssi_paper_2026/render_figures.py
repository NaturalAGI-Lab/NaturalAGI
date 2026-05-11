"""Generate figs 1, 2, 3 PNGs for the ITSSI 2026 paper.

Run once with the project venv:
    natural-agi/bin/python papers/itssi_paper_2026/render_figures.py

Outputs to papers/itssi_paper_2026/figures/:
  fig_1_pipeline.png       — matplotlib flowchart
  fig_2_digit7_graph.png   — two-panel: raster digit 7 + spring-laid graph
  fig_3_concept_7_1.png    — clean networkx render of concept 7_1
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

HERE = Path(__file__).parent
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(exist_ok=True)

REPO = HERE.parent.parent
CONCEPT_JSON = REPO / "experiments" / "run_20260427_144233" / "concept_graphs.json"
DIGIT_7_DIR = REPO / "datasets" / "mnist_all" / "7"

DPI = 300


# ---------- Fig 1: pipeline ----------

def render_fig_1_pipeline() -> Path:
    out = FIG_DIR / "fig_1_pipeline.png"
    boxes = [
        "Зображення\n100×100",
        "Скелетизація\n(GNG + RDP)",
        "Граф\n(Point/Vector,\nнормаліз. координати)",
        "Концепт-атрактор\n(CRO)",
        "Класифікація\n(GED + Boria sim,\ncomplexity-adjusted)",
    ]
    n = len(boxes)

    fig, ax = plt.subplots(figsize=(15, 4.5))
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.axis("off")

    box_w = 0.78
    box_h = 0.55
    gap = (1.0 - box_w)
    y_center = 0.5

    for i, label in enumerate(boxes):
        x_center = i + 0.5
        x_left = x_center - box_w / 2
        y_bottom = y_center - box_h / 2

        rect = FancyBboxPatch(
            (x_left, y_bottom),
            box_w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            linewidth=1.6,
            edgecolor="black",
            facecolor="#f0f0f0",
        )
        ax.add_patch(rect)
        ax.text(
            x_center,
            y_center,
            label,
            ha="center",
            va="center",
            fontsize=12,
            family="serif",
            wrap=True,
        )

        if i < n - 1:
            arrow = FancyArrowPatch(
                (x_center + box_w / 2, y_center),
                (x_center + 1 - box_w / 2, y_center),
                arrowstyle="-|>",
                mutation_scale=18,
                linewidth=1.6,
                color="black",
            )
            ax.add_patch(arrow)

    fig.tight_layout()
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# ---------- Concept loader ----------

def _load_concept(concept_id: str):
    with open(CONCEPT_JSON) as f:
        data = json.load(f)
    return data[concept_id]


def _node_label(node: dict, idx: int) -> str:
    labels = node.get("labels", [])
    if "StartPoint" in labels:
        kind = "Start"
    elif "EndPoint" in labels:
        kind = "End"
    elif "CornerPoint" in labels:
        kind = "Corner"
    elif "HorizontalVector" in labels:
        kind = "Vec(H)"
    elif "Vector" in labels:
        kind = "Vec"
    elif "Point" in labels:
        kind = "Point"
    else:
        kind = labels[0] if labels else "Node"
    return f"{kind}\n#{idx}"


def _node_color(node: dict) -> str:
    labels = node.get("labels", [])
    if "Vector" in labels:
        return "#e6f3ff"
    return "#fff2cc"


def _build_nx_graph(concept: dict) -> tuple[nx.Graph, dict, dict, dict]:
    g = nx.Graph()
    id_to_idx: dict[str, int] = {}
    labels: dict[str, str] = {}
    colors: dict[str, str] = {}
    pos: dict[str, tuple[float, float]] = {}

    for idx, node in enumerate(concept["nodes"]):
        nid = node["id"]
        id_to_idx[nid] = idx
        g.add_node(nid)
        labels[nid] = _node_label(node, idx)
        colors[nid] = _node_color(node)

        nx_val = node.get("normalized_x")
        ny_val = node.get("normalized_y")
        if isinstance(nx_val, dict) and isinstance(ny_val, dict):
            pos[nid] = (nx_val.get("center", 0.0), -ny_val.get("center", 0.0))

    for edge in concept["edges"]:
        s = edge["source"]
        t = edge["target"]
        if s in g and t in g:
            g.add_edge(s, t)

    if len(pos) != g.number_of_nodes():
        pos = nx.spring_layout(g, seed=7)

    return g, labels, colors, pos


def _draw_graph(ax, concept: dict, *, title: str | None = None) -> None:
    g, labels, colors, pos = _build_nx_graph(concept)
    node_colors = [colors[n] for n in g.nodes()]

    nx.draw_networkx_edges(g, pos, ax=ax, width=1.6, edge_color="black")
    nx.draw_networkx_nodes(
        g,
        pos,
        ax=ax,
        node_size=2400,
        node_color=node_colors,
        edgecolors="black",
        linewidths=1.4,
    )
    nx.draw_networkx_labels(
        g,
        pos,
        labels=labels,
        ax=ax,
        font_size=9,
        font_family="serif",
    )
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=12, family="serif")


# ---------- Fig 2: digit 7 raster + graph ----------

def render_fig_2_digit7() -> Path:
    out = FIG_DIR / "fig_2_digit7_graph.png"
    raster_files = sorted(DIGIT_7_DIR.glob("*.png"))
    if not raster_files:
        raise RuntimeError(f"No PNGs in {DIGIT_7_DIR}")
    raster_path = raster_files[0]

    img = Image.open(raster_path).convert("L")

    concept = _load_concept("7_1")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))

    axes[0].imshow(img, cmap="gray", vmin=0, vmax=255)
    axes[0].set_title(
        f"Растрове зображення: {raster_path.name}",
        fontsize=11,
        family="serif",
    )
    axes[0].axis("off")

    _draw_graph(
        axes[1],
        concept,
        title="Скелетний граф (Point / Vector)",
    )

    fig.tight_layout()
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# ---------- Fig 3: concept attractor 7_1 ----------

def render_fig_3_concept_7_1() -> Path:
    out = FIG_DIR / "fig_3_concept_7_1.png"
    concept = _load_concept("7_1")

    fig, ax = plt.subplots(figsize=(7, 6))
    _draw_graph(ax, concept)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    print("Rendering Fig 1 (pipeline)...")
    p1 = render_fig_1_pipeline()
    print(f"  -> {p1}")

    print("Rendering Fig 2 (digit 7 raster + graph)...")
    p2 = render_fig_2_digit7()
    print(f"  -> {p2}")

    print("Rendering Fig 3 (concept 7_1)...")
    p3 = render_fig_3_concept_7_1()
    print(f"  -> {p3}")


if __name__ == "__main__":
    main()
