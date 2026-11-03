"""Band concepts over a graph-level feature vector (the direction map).

A band concept is what several samples of one writing mode have in common, written as a
per-dimension band [lo, hi] (10th / 90th percentile of its members) plus a centre (their mean).
Unlike the node-level fold it needs no node correspondence, so it exists even when the
training graphs share no common minor, which is what makes a per-form root possible.

Pure numpy; no Neo4j, no Nuclio.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np

DEFAULT_BLOCK_WEIGHTS: Dict[str, float] = {"orient": 8.8, "ep": 0.58, "jp": 0.5, "glob": 1.0, "curv": 1.0, "epdir": 2.0, "dorient": 4.4}
# With the dense centre-line orientation block (dm3) the graph block shares its weight with it.
DENSE_BLOCK_WEIGHTS: Dict[str, float] = dict(DEFAULT_BLOCK_WEIGHTS, orient=4.4, dorient=4.4)
DEFAULT_PERCENTILE = 10.0


def dim_weights(
    blocks: Sequence[str],
    grid_of_dim: Sequence[int],
    block_weights: Dict[str, float] | None = None,
) -> np.ndarray:
    """Per-dimension weight: a block's weight is shared by its dimensions, and the grid
    blocks are additionally shared between the grid levels, so neither a finer grid nor an
    extra level can outvote the others by sheer dimension count."""
    block_weights = block_weights or DEFAULT_BLOCK_WEIGHTS
    blocks = list(blocks)
    grid_of_dim = list(grid_of_dim)
    n_grids = max(len({g for g in grid_of_dim if g}), 1)
    sizes: Dict[tuple, int] = {}
    for b, g in zip(blocks, grid_of_dim):
        sizes[(b, g)] = sizes.get((b, g), 0) + 1
    return np.array(
        [
            block_weights[b] / sizes[(b, g)] / (n_grids if g else 1)
            for b, g in zip(blocks, grid_of_dim)
        ]
    )


def chi2(P: np.ndarray, Q: np.ndarray, w: np.ndarray) -> np.ndarray:
    """(len(P), len(Q)) weighted chi-square distances."""
    P = np.atleast_2d(P)
    Q = np.atleast_2d(Q)
    out = np.zeros((len(P), len(Q)))
    for i in range(len(P)):
        num = (P[i] - Q) ** 2
        den = np.abs(P[i]) + np.abs(Q) + 1e-9
        out[i] = (num / den * w).sum(1)
    return out


def percentile_band(members: np.ndarray, q: float = DEFAULT_PERCENTILE):
    """-> (lo, hi, centre) over the rows of ``members``."""
    members = np.atleast_2d(members)
    return (
        np.percentile(members, q, axis=0),
        np.percentile(members, 100.0 - q, axis=0),
        members.mean(axis=0),
    )


def merge_similar(
    originals: np.ndarray, members: Sequence[np.ndarray], w: np.ndarray
) -> List[List[int]]:
    """Group originals that are the same writing mode.

    An original's own augmentations show how far "the same glyph" can drift; two originals
    are merged when each lies within the other's drift (90th-percentile distance from an
    original to its augmentations). ``members[i]`` has the original in row 0 followed by
    its augmentations. No tuned threshold.
    """
    n = len(originals)
    radius = [
        float(np.percentile(chi2(originals[i], members[i][1:], w)[0], 90))
        if len(members[i]) > 1
        else 0.0
        for i in range(n)
    ]
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            a = parent[a]
        return a

    for a in range(n):
        for b in range(a + 1, n):
            if chi2(originals[a], originals[b], w)[0, 0] <= min(radius[a], radius[b]):
                parent[find(a)] = find(b)
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def pooled_scale(counts: Sequence[int], sums: Sequence[np.ndarray], sumsqs: Sequence[np.ndarray]):
    """Per-dimension (population) std over all leaf members, from the leaves' own
    (n, sum, sum of squares), so the training images need not be kept."""
    n = float(sum(counts))
    mean = np.sum(sums, axis=0) / n
    var = np.sum(sumsqs, axis=0) / n - mean**2
    return np.maximum(np.sqrt(np.maximum(var, 0.0)), 1e-6)
