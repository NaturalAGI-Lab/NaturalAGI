"""Direction map: a fixed-length, graph-level description of a skeleton.

The skeleton's bounding box is stretched per axis to the unit square and laid over
G x G grids (default 2x2 and 3x3). For every cell the map records
  * orient: how much of the stroke length passes through the cell in each of NB
            orientation bins (mod 180 degrees), as a share of the total length;
  * ep:     how many endpoints (degree 1) fall into the cell;
  * jp:     how many junctions (degree >= 3) fall into the cell;
plus five globals: endpoint count, junction count, independent cycles,
bounding-box aspect (width / height) and total normalised stroke length.
Cell and orientation binning are soft (bilinear / linear), so a point near a cell
border contributes to both neighbours.

dm2 adds two blocks that dm1 cannot express (the letters it confused most were
M/N, U/V, g/q and t/f -- how sharply a stroke bends and which way a tail points):
  * curv:  per cell, the turning angle (radians) accumulated at the skeleton's
           degree-2 nodes, split into bends toward the glyph centroid ("in",
           the stroke dents inwards) and away from it ("out", it bulges);
  * epdir: per 2x2 cell, the outward direction of each endpoint's last edge in
           EP_DIR_BINS signed bins over 360 degrees (soft), i.e. where a stroke
           ends and which way it was heading.

It answers "where do the strokes run, and which way" without deciding which node
of one graph corresponds to which node of another, which is what makes it robust
on the 5-8 node skeletons this pipeline produces.

Layout for grids=(2, 3): g2.orient[16] g2.ep[4] g2.jp[4] g3.orient[36] g3.ep[9]
g3.jp[9] glob[5] (= dm1, 83 values) g2.curv[8] g3.curv[18] g2.epdir[32] = 141
values. DM_VERSION must change whenever this layout or any constant below
changes: stored maps and band models are tagged with it.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import networkx as nx
import numpy as np

DM_VERSION = "dm2"
DEFAULT_GRIDS: Tuple[int, ...] = (2, 3)
ORIENTATION_BINS = 4
RASTER_STEP = 0.02
CURVATURE_GRIDS: Tuple[int, ...] = (2, 3)
EP_DIR_GRID = 2
EP_DIR_BINS = 8
GLOBAL_NAMES = ("n_endpoints", "n_junctions", "n_cycles", "aspect", "total_length")
_EPS = 1e-6


def _cell_weights(points: np.ndarray, grid: int) -> np.ndarray:
    """(n, grid*grid) soft membership of unit-square points in the grid cells."""
    n = len(points)
    weights = np.zeros((n, grid * grid))
    if n == 0:
        return weights
    rows = np.arange(n)
    c = np.clip(points * grid - 0.5, 0, grid - 1)
    i0 = np.floor(c).astype(int)
    frac = c - i0
    i1 = np.minimum(i0 + 1, grid - 1)
    for ix, wx in ((i0[:, 0], 1 - frac[:, 0]), (i1[:, 0], frac[:, 0])):
        for iy, wy in ((i0[:, 1], 1 - frac[:, 1]), (i1[:, 1], frac[:, 1])):
            np.add.at(weights, (rows, iy * grid + ix), wx * wy)
    return weights


def _orientation_weights(angles: np.ndarray, bins: int) -> np.ndarray:
    """(n, bins) soft membership of angles in [0, pi) in circular orientation bins."""
    n = len(angles)
    weights = np.zeros((n, bins))
    if n == 0:
        return weights
    x = (angles / math.pi) * bins
    rows = np.arange(n)
    b0 = np.floor(x).astype(int) % bins
    frac = x - np.floor(x)
    np.add.at(weights, (rows, b0), 1 - frac)
    np.add.at(weights, (rows, (b0 + 1) % bins), frac)
    return weights


def _direction_bins(vectors: np.ndarray, bins: int) -> np.ndarray:
    """(n, bins) soft membership of 2-d directions in signed bins over [0, 2*pi)."""
    n = len(vectors)
    weights = np.zeros((n, bins))
    if n == 0:
        return weights
    x = (np.arctan2(vectors[:, 1], vectors[:, 0]) % (2 * math.pi)) / (2 * math.pi) * bins
    rows = np.arange(n)
    b0 = np.floor(x).astype(int) % bins
    frac = x - np.floor(x)
    np.add.at(weights, (rows, b0), 1 - frac)
    np.add.at(weights, (rows, (b0 + 1) % bins), frac)
    return weights


def dim_schema(grids: Sequence[int] = DEFAULT_GRIDS, bins: int = ORIENTATION_BINS):
    """-> (names, blocks, grid_of_dim) describing every dimension, in order."""
    names: List[str] = []
    blocks: List[str] = []
    grid_of_dim: List[int] = []
    for g in grids:
        for cell in range(g * g):
            for b in range(bins):
                names.append(f"g{g}.orient.c{cell}.b{b}")
                blocks.append("orient")
                grid_of_dim.append(g)
        for block in ("ep", "jp"):
            for cell in range(g * g):
                names.append(f"g{g}.{block}.c{cell}")
                blocks.append(block)
                grid_of_dim.append(g)
    for name in GLOBAL_NAMES:
        names.append(f"glob.{name}")
        blocks.append("glob")
        grid_of_dim.append(0)
    for g in CURVATURE_GRIDS:
        for side in ("in", "out"):
            for cell in range(g * g):
                names.append(f"g{g}.curv.{side}.c{cell}")
                blocks.append("curv")
                grid_of_dim.append(g)
    for cell in range(EP_DIR_GRID * EP_DIR_GRID):
        for b in range(EP_DIR_BINS):
            names.append(f"g{EP_DIR_GRID}.epdir.c{cell}.b{b}")
            blocks.append("epdir")
            grid_of_dim.append(EP_DIR_GRID)
    return names, blocks, grid_of_dim


def dimension_count(grids: Sequence[int] = DEFAULT_GRIDS, bins: int = ORIENTATION_BINS) -> int:
    return (
        sum(g * g * (bins + 2) for g in grids)
        + len(GLOBAL_NAMES)
        + sum(2 * g * g for g in CURVATURE_GRIDS)
        + EP_DIR_GRID * EP_DIR_GRID * EP_DIR_BINS
    )


def _curvature_and_endpoint_dims(graph: nx.Graph, unit: np.ndarray, index: dict) -> List[np.ndarray]:
    """curv blocks (per CURVATURE_GRIDS) and the epdir block, in schema order."""
    pos = {n: unit[index[n]] for n in index}
    centroid = unit.mean(0)
    turn_pos, turn_val, inward = [], [], []
    ep_pos, ep_dir = [], []
    for n in index:
        nb = list(graph.neighbors(n))
        if len(nb) == 2:
            a, b = pos[nb[0]] - pos[n], pos[nb[1]] - pos[n]
            na, nb_ = np.linalg.norm(a), np.linalg.norm(b)
            if na < 1e-9 or nb_ < 1e-9:
                continue
            a, b = a / na, b / nb_
            theta = math.pi - math.acos(max(-1.0, min(1.0, float(a @ b))))  # 0 = straight through
            turn_pos.append(pos[n])
            turn_val.append(theta)
            inward.append(float((a + b) @ (centroid - pos[n])) > 0)  # concave side faces the centroid
        elif len(nb) == 1:
            d = pos[n] - pos[nb[0]]
            if np.linalg.norm(d) > 1e-9:
                ep_pos.append(pos[n])
                ep_dir.append(d / np.linalg.norm(d))
    turn_pos = np.array(turn_pos).reshape(-1, 2)
    turn_val = np.array(turn_val)
    inward = np.array(inward, bool)
    ep_pos = np.array(ep_pos).reshape(-1, 2)
    ep_dir = np.array(ep_dir).reshape(-1, 2)
    parts = []
    for g in CURVATURE_GRIDS:
        cells = _cell_weights(turn_pos, g)
        parts.append((cells * (turn_val * inward)[:, None]).sum(0))
        parts.append((cells * (turn_val * ~inward)[:, None]).sum(0))
    cells = _cell_weights(ep_pos, EP_DIR_GRID)
    parts.append((cells[:, :, None] * _direction_bins(ep_dir, EP_DIR_BINS)[:, None, :]).sum(0).ravel())
    return parts


MAX_SHEAR = 1.0             # |shear| limit of the slant normalisation (45 degrees)
DM_VERSION_DESLANT = "dm4"  # dm3 computed on slant-normalised coordinates


def slant_shear(points: np.ndarray) -> float:
    """Shear s that makes the principal axis of a point cloud upright: x' = x - s * (y - mean_y),
    s = mu11 / mu02 (second central moments), limited to +-MAX_SHEAR. The classic handwriting deskew."""
    if len(points) < 2:
        return 0.0
    c = points - points.mean(0)
    mu02 = float((c[:, 1] ** 2).mean())
    if mu02 <= 1e-9:
        return 0.0
    return float(np.clip((c[:, 0] * c[:, 1]).mean() / mu02, -MAX_SHEAR, MAX_SHEAR))


def _edge_samples(graph: nx.Graph, node_ids: list, xy: np.ndarray) -> np.ndarray:
    """Points every ~2 px along the edges (length-weighted description of where the strokes are)."""
    index = {n: i for i, n in enumerate(node_ids)}
    samples = []
    for u, v in graph.edges():
        a, b = xy[index[u]], xy[index[v]]
        k = max(1, int(np.hypot(*(b - a)) / 2))
        samples.append(a + ((np.arange(k) + 0.5) / k)[:, None] * (b - a))
    return np.vstack(samples) if samples else xy


def _deslanted_xy(graph: nx.Graph, node_ids: list, xy: np.ndarray) -> np.ndarray:
    """Node coordinates after removing the skeleton's slant (length-weighted)."""
    if graph.number_of_edges() == 0:
        return xy
    samples = _edge_samples(graph, node_ids, xy)
    shear = slant_shear(samples)
    out = xy.copy()
    out[:, 0] -= shear * (xy[:, 1] - samples[:, 1].mean())
    return out


def compute_direction_map(
    graph: nx.Graph,
    grids: Iterable[int] = DEFAULT_GRIDS,
    bins: int = ORIENTATION_BINS,
    step: float = RASTER_STEP,
    deslant: bool = False,
    normalisation: str = "bbox",
    moment_range: float = 2.0,
) -> np.ndarray:
    """Direction map of a skeleton graph whose nodes carry raw ``x`` and ``y``.
    With ``deslant`` the node coordinates are first sheared upright (the graph itself is not modified).
    ``normalisation``: "bbox" stretches the bounding box to the unit square (historical); "moment" centres on the
    stroke centroid and scales each axis by ``moment_range`` standard deviations (insensitive to one long tail)."""
    grids = tuple(grids)
    node_ids = list(graph.nodes)
    if not node_ids:
        return np.zeros(dimension_count(grids, bins))

    xy = np.array([[graph.nodes[n]["x"], graph.nodes[n]["y"]] for n in node_ids], float)
    if deslant:
        xy = _deslanted_xy(graph, node_ids, xy)
    lo, hi = xy.min(0), xy.max(0)
    extent = np.maximum(hi - lo, _EPS)
    if normalisation == "moment":
        samples = _edge_samples(graph, node_ids, xy)
        centre, sigma = samples.mean(0), np.maximum(samples.std(0), _EPS)
        half = np.maximum(moment_range * sigma, 0.02 * float(extent.max()))    # a bare stroke keeps a minimal width
        lo, extent = centre - half, 2 * half
        unit = np.clip((xy - lo) / extent, 0.0, 1.0)
    else:
        unit = (xy - lo) / extent
    index = {n: i for i, n in enumerate(node_ids)}
    degree = dict(graph.degree())

    points, mass, angles = [], [], []
    for u, v in graph.edges():
        p0, p1 = unit[index[u]], unit[index[v]]
        d = p1 - p0
        length = float(np.hypot(*d))
        if length < 1e-9:
            continue
        k = max(1, int(math.ceil(length / step)))
        t = (np.arange(k) + 0.5) / k
        points.append(p0 + t[:, None] * d)
        mass.append(np.full(k, length / k))
        angles.append(np.full(k, math.atan2(d[1], d[0]) % math.pi))
    if points:
        points, mass, angles = np.vstack(points), np.concatenate(mass), np.concatenate(angles)
    else:
        points, mass, angles = np.zeros((0, 2)), np.zeros(0), np.zeros(0)
    total = float(mass.sum())
    share = mass / max(total, 1e-9)
    orientation = _orientation_weights(angles, bins)

    endpoints = np.array([unit[index[n]] for n in node_ids if degree[n] == 1]).reshape(-1, 2)
    junctions = np.array([unit[index[n]] for n in node_ids if degree[n] >= 3]).reshape(-1, 2)
    try:
        n_cycles = len(nx.cycle_basis(graph))
    except Exception:  # directed / multigraph input
        n_cycles = 0

    parts = []
    for g in grids:
        cells = _cell_weights(points, g)
        parts.append(((cells * share[:, None]).T @ orientation).ravel())
        parts.append(_cell_weights(endpoints, g).sum(0))
        parts.append(_cell_weights(junctions, g).sum(0))
    parts.append(
        np.array(
            [len(endpoints), len(junctions), n_cycles, extent[0] / max(extent[1], _EPS), total],
            float,
        )
    )
    parts += _curvature_and_endpoint_dims(graph, unit, index)   # `unit` already carries the deslanted coordinates
    return np.concatenate(parts)


# dm3 = dm2 + the orientation block measured on the dense centre line (computed in skeletonization,
# where the thinned skeleton exists; see src/skeletonization/dense_features.py). The block arrives
# with the message; this module only describes its dimensions.
DM_VERSION_DENSE = "dm3"
DENSE_ORIENT_GRIDS: Tuple[int, ...] = (2, 3)


def dense_dim_schema():
    """-> (names, blocks, grid_of_dim) of dm3: the graph map followed by the dense orientation block."""
    names, blocks, grid_of_dim = dim_schema()
    for g in DENSE_ORIENT_GRIDS:
        for cell in range(g * g):
            for b in range(ORIENTATION_BINS):
                names.append(f"g{g}.dorient.c{cell}.b{b}")
                blocks.append("dorient")
                grid_of_dim.append(g)
    return names, blocks, grid_of_dim
