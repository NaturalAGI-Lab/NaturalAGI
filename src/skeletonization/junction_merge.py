import networkx as nx
import numpy as np

# Multiple of the estimated stroke width below which a junction-junction edge is
# treated as a thinning artifact ("theta bridge") and collapsed.
BRIDGE_MERGE_FACTOR = 1.5
# A short junction-junction edge is only a thinning artifact when the strokes pass THROUGH the pair
# diagonally (the waist of an 8, the crossing of an X). When a stroke runs straight through one of the
# two junctions (the stem of an H or a K: its two other branches are collinear), the short edge is a
# real stroke attached to that stem and must stay. Off by default = historical behaviour.
PROTECT_THROUGH_STROKES = False
THROUGH_STROKE_MIN_ANGLE_DEG = 150.0


def estimate_stroke_width(binary, skeleton) -> float:
    """Mean stroke width ~= filled area / centerline length (both in pixels)."""
    return 2.0 * float(np.asarray(binary).sum()) / max(float(np.asarray(skeleton).sum()), 1.0)


def _has_through_stroke(graph: nx.Graph, junction, other) -> bool:
    """True when two of the junction's branches (other than the bridge to `other`) continue each other in a
    straight line, i.e. a stem passes through the junction."""
    p = np.array([graph.nodes[junction]["x"], graph.nodes[junction]["y"]], float)
    dirs = []
    for n in graph.neighbors(junction):
        if n == other:
            continue
        d = np.array([graph.nodes[n]["x"], graph.nodes[n]["y"]], float) - p
        norm = np.linalg.norm(d)
        if norm > 1e-9:
            dirs.append(d / norm)
    cos_limit = np.cos(np.radians(THROUGH_STROKE_MIN_ANGLE_DEG))
    for i in range(len(dirs)):
        for j in range(i + 1, len(dirs)):
            if float(dirs[i] @ dirs[j]) <= cos_limit:
                return True
    return False


def merge_short_junction_bridges(graph: nx.Graph, max_bridge_len: float, protect_through_strokes: bool = None) -> nx.Graph:
    """Collapse a short edge joining two junctions (degree >= 3) into a single crossing node.

    Zhang-Suen thinning of a thick crossing (e.g. the waist of an 8) does not yield a clean
    4-way node; it splits into two 3-way junctions joined by a short link whose length is
    ~ the stroke width. This restores the single crossing.

    A merge is only applied when the two junctions share NO common neighbour. For a simple
    graph, contracting the bridge ``u-v`` drops the cycle rank by exactly the number of common
    neighbours: a genuine thinning bridge has none (both loops of the 8 are preserved), whereas
    a shared neighbour means the "bridge" actually closes a small loop. Merging the latter would
    both destroy a real cycle (an 8 collapses toward a 0) and create a parallel edge whose
    ``contraction`` bookkeeping is keyed by a tuple, which breaks JSON serialisation downstream.
    Skipping shared-neighbour pairs avoids both.
    """
    if protect_through_strokes is None:
        protect_through_strokes = PROTECT_THROUGH_STROKES
    graph = graph.copy()
    changed = True
    while changed:
        changed = False
        for u, v, data in list(graph.edges(data=True)):
            if not (
                graph.degree(u) >= 3
                and graph.degree(v) >= 3
                and data.get("length", np.inf) < max_bridge_len
            ):
                continue
            common = (set(graph.neighbors(u)) - {v}) & (set(graph.neighbors(v)) - {u})
            if common:
                continue
            if protect_through_strokes and (_has_through_stroke(graph, u, v) or _has_through_stroke(graph, v, u)):
                continue
            mid_x = (graph.nodes[u]["x"] + graph.nodes[v]["x"]) / 2.0
            mid_y = (graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2.0
            nx.contracted_nodes(graph, u, v, self_loops=False, copy=False)
            graph.nodes[u]["x"], graph.nodes[u]["y"] = mid_x, mid_y
            graph.nodes[u].pop("contraction", None)
            for _, _, edata in graph.edges(u, data=True):
                edata.pop("contraction", None)
            changed = True
            break
    return graph
