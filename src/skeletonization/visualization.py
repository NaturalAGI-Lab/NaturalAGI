"""
Visualization utilities for skeletonization pipeline.
Extracted from experiments.ipynb.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Generator, List, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from pydantic import BaseModel
from ypstruct import structure

from skeletonization.converter import Converter


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class Vector(BaseModel):
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    length: float


@dataclass
class Point:
    x: float
    y: float
    id: str

    def __hash__(self):
        return hash(self.id)


# ---------------------------------------------------------------------------
# Graph traversal
# ---------------------------------------------------------------------------

class GraphTraversal:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def dfs_traversal(
        self, start_node: Any
    ) -> Generator[Tuple[Point, Optional[Vector]], None, None]:
        visited_edges = set()

        def find_edge(x1, y1, x2, y2) -> Optional[dict]:
            for _, _, edge_data in self.graph.edges(data=True):
                if (
                    edge_data["x1"] == x1
                    and edge_data["y1"] == y1
                    and edge_data["x2"] == x2
                    and edge_data["y2"] == y2
                ) or (
                    edge_data["x1"] == x2
                    and edge_data["y1"] == y2
                    and edge_data["x2"] == x1
                    and edge_data["y2"] == y1
                ):
                    return edge_data
            return None

        def _dfs(node_id, prev_x=None, prev_y=None):
            node_data = self.graph.nodes[node_id]
            point = Point(id=node_data["id"], x=node_data["x"], y=node_data["y"])

            incoming_vector = None
            if prev_x is not None and prev_y is not None:
                edge_data = find_edge(prev_x, prev_y, point.x, point.y)
                if edge_data:
                    incoming_vector = Vector(
                        id=edge_data["id"],
                        x1=prev_x,
                        y1=prev_y,
                        x2=point.x,
                        y2=point.y,
                        length=edge_data["length"],
                    )
                else:
                    raise ValueError(
                        f"Edge not found between {prev_x}, {prev_y} and {point.x}, {point.y}"
                    )

            yield point, incoming_vector

            for neighbor_id in self.graph.neighbors(node_id):
                edge = tuple(sorted([node_id, neighbor_id]))
                if edge not in visited_edges:
                    visited_edges.add(edge)
                    yield from _dfs(neighbor_id, point.x, point.y)

        yield from _dfs(start_node)


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------

def find_top_leftmost_point(graph: nx.Graph) -> Optional[Any]:
    """Return the top-leftmost endpoint, or the highest-degree node if none exist."""
    if not graph.nodes:
        return None
    degree_one_nodes = [n for n in graph.nodes if graph.degree[n] == 1]
    if degree_one_nodes:
        return min(degree_one_nodes, key=lambda n: graph.nodes[n]["y"] + graph.nodes[n]["x"])
    return max(graph.nodes, key=lambda n: graph.degree[n])


def plot_graph_traversal(
    ax: plt.Axes,
    G: nx.Graph,
    traversal: List[Tuple[Point, Optional[Vector]]],
) -> None:
    """Plot DFS traversal with directional arrows."""
    pos = {node: (G.nodes[node]["x"], G.nodes[node]["y"]) for node in G.nodes()}
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="lightgray", arrows=False)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=30, node_color="lightblue")

    for i, (point, vector) in enumerate(traversal):
        if i == 0:
            ax.scatter(point.x, point.y, color="red", s=100, zorder=10)
        if vector:
            dx = vector.x2 - vector.x1
            dy = vector.y2 - vector.y1
            ax.arrow(
                vector.x1, vector.y1, dx, dy,
                head_width=3, head_length=3,
                fc="r", ec="r",
                length_includes_head=True,
                alpha=0.5,
            )
        ax.text(point.x, point.y, str(i), fontsize=8, ha="center", va="center")

    ax.set_title("Graph Traversal (DFS)")
    ax.axis("equal")
    ax.invert_yaxis()


def calculate_label_position(vector: Vector, offset: float = 1) -> Tuple[float, float]:
    dx = vector.x2 - vector.x1
    dy = vector.y2 - vector.y1
    length = vector.length
    if length > 0:
        nx_ = -dy / length
        ny_ = dx / length
    else:
        nx_, ny_ = 0, -1
    mid_x = vector.x1 + dx / 2
    mid_y = vector.y1 + dy / 2
    return mid_x + nx_ * offset, mid_y + ny_ * offset


def plot_network_result(
    image_path: str,
    network,
    network_params: structure,
    points: np.ndarray,
    image: np.ndarray,
    binary: np.ndarray,
    skeleton: np.ndarray,
    simplified_network: List[List[np.ndarray]],
    threshold_value: float = None,
) -> nx.Graph:
    """Visualise all 6 stages of image processing and return the final NetworkX graph."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    # 1. Original image
    axes[0].imshow(image, cmap="gray")
    axes[0].set_title(f"1. ОРИГІНАЛ\n{os.path.basename(image_path)}", fontsize=12, fontweight="bold")
    axes[0].axis("off")

    # 2. Binary image
    threshold_text = f"Otsu={threshold_value:.0f}" if threshold_value else "threshold"
    axes[1].imshow(binary, cmap="gray")
    axes[1].set_title(f"2. БІНАРИЗАЦІЯ\n({threshold_text})", fontsize=12, fontweight="bold")
    axes[1].axis("off")

    # 3. Skeleton
    axes[2].imshow(skeleton, cmap="gray")
    axes[2].set_title("3. СКЕЛЕТ\nЛінія 1px + pruning", fontsize=12, fontweight="bold")
    axes[2].axis("off")

    # 4. GNG network
    ax4 = axes[3]
    ax4.scatter(points[:, 0], points[:, 1], s=1, c="lightblue", alpha=0.5)
    for i in range(network_params.N):
        for j in range(i + 1, network_params.N):
            if network.C[i, j] == 1:
                ax4.plot(
                    [network.w[i, 0], network.w[j, 0]],
                    [network.w[i, 1], network.w[j, 1]],
                    c="red", linewidth=1.5,
                )
    ax4.scatter(network.w[:, 0], network.w[:, 1], s=80, c="yellow", edgecolors="red", zorder=5)
    ax4.set_title(f"4. GNG МЕРЕЖА\n{network_params.N} нейронів", fontsize=12, fontweight="bold")
    ax4.axis("equal")
    ax4.invert_yaxis()
    ax4.grid(True, alpha=0.3)

    # 5. RDP simplification
    ax5 = axes[4]
    ax5.scatter(points[:, 0], points[:, 1], s=1, c="lightblue", alpha=0.3)
    for segment in simplified_network:
        ax5.plot(segment[:, 0], segment[:, 1], "r-", linewidth=2)
        ax5.scatter(segment[:, 0], segment[:, 1], s=50, c="yellow", edgecolors="red", zorder=5)
    ax5.set_title(
        f"5. RDP СПРОЩЕННЯ\n~{len(simplified_network)} сегментів", fontsize=12, fontweight="bold"
    )
    ax5.axis("equal")
    ax5.invert_yaxis()
    ax5.grid(True, alpha=0.3)

    # 6. Final NetworkX graph
    ax6 = axes[5]
    G = Converter.convert_simplified_network_to_networkx(simplified_network)
    pos = {node: (G.nodes[node]["x"], G.nodes[node]["y"]) for node in G.nodes()}
    endpoints = [n for n in G.nodes() if G.degree(n) == 1]
    junctions = [n for n in G.nodes() if G.degree(n) >= 3]
    regular = [n for n in G.nodes() if G.degree(n) == 2]
    nx.draw_networkx_edges(G, pos, ax=ax6, edge_color="red", width=2)
    nx.draw_networkx_nodes(G, pos, nodelist=regular, ax=ax6, node_size=60, node_color="yellow", edgecolors="red")
    nx.draw_networkx_nodes(G, pos, nodelist=endpoints, ax=ax6, node_size=100, node_color="green", edgecolors="darkgreen", label="Endpoints")
    nx.draw_networkx_nodes(G, pos, nodelist=junctions, ax=ax6, node_size=100, node_color="blue", edgecolors="darkblue", label="Junctions")
    cycles = len(list(nx.cycle_basis(G)))
    ax6.set_title(
        f"6. ФІНАЛЬНИЙ ГРАФ\n{G.number_of_nodes()} вузлів, {G.number_of_edges()} ребер\n"
        f"{len(endpoints)} endpoints, {len(junctions)} junctions, {cycles} циклів",
        fontsize=12, fontweight="bold",
    )
    ax6.axis("equal")
    ax6.invert_yaxis()
    ax6.legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    plt.show()
    return G
