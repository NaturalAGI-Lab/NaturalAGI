import networkx as nx
import numpy as np

# Multiple of the estimated stroke width below which a junction-junction edge is
# treated as a thinning artifact ("theta bridge") and collapsed.
BRIDGE_MERGE_FACTOR = 1.5


def estimate_stroke_width(binary, skeleton) -> float:
    """Mean stroke width ~= filled area / centerline length (both in pixels)."""
    return 2.0 * float(np.asarray(binary).sum()) / max(float(np.asarray(skeleton).sum()), 1.0)


def merge_short_junction_bridges(graph: nx.Graph, max_bridge_len: float) -> nx.Graph:
    """Collapse a short edge joining two junctions (degree >= 3) into a single crossing node.

    Zhang-Suen thinning of a thick crossing (e.g. the waist of an 8) does not yield a clean
    4-way node; it splits into two 3-way junctions joined by a short link whose length is
    ~ the stroke width. This restores the single crossing. Reductions never disconnect the
    graph (edge contraction only), so topology stays intact apart from the removed bridge.
    """
    graph = graph.copy()
    changed = True
    while changed:
        changed = False
        for u, v, data in list(graph.edges(data=True)):
            if (
                graph.degree(u) >= 3
                and graph.degree(v) >= 3
                and data.get("length", np.inf) < max_bridge_len
            ):
                mid_x = (graph.nodes[u]["x"] + graph.nodes[v]["x"]) / 2.0
                mid_y = (graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2.0
                nx.contracted_nodes(graph, u, v, self_loops=False, copy=False)
                graph.nodes[u]["x"], graph.nodes[u]["y"] = mid_x, mid_y
                graph.nodes[u].pop("contraction", None)
                changed = True
                break
    return graph
