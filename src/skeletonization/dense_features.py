"""Shape information taken from the DENSE thinned skeleton (the one-pixel centre line), before the
GNG / RDP simplification reduces a letter to 5-10 straight edges and loses how its strokes bend.

Two things are produced, both in the centre line's own bounding box stretched to the unit square:
  * orient  — stroke-direction mass per cell (2x2 and 3x3 grids x 4 orientation bins, soft), i.e. the
              direction map's orientation block measured on the true curve;
  * points / tangents — N_POINTS centre-line points spread evenly (farthest-point sampling) with
              their tangents (doubled-angle unit vectors), the input of the shape-context comparison.
Pure numpy; no learning, no comparison of ink pixels.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

GRID = 32            # quantisation of the unit box for sampling
ORIENT_BINS = 4
ORIENT_GRIDS = (2, 3)
N_POINTS = 32
TANGENT_RADIUS = 3   # px, neighbourhood of the local PCA tangent


def _cell_weights(points: np.ndarray, grid: int) -> np.ndarray:
    """(n, grid*grid) soft membership of unit-square points in the grid cells (same rule as the direction map)."""
    n = len(points)
    weights = np.zeros((n, grid * grid))
    rows = np.arange(n)
    c = np.clip(points * grid - 0.5, 0, grid - 1)
    i0 = np.floor(c).astype(int)
    frac = c - i0
    i1 = np.minimum(i0 + 1, grid - 1)
    for ix, wx in ((i0[:, 0], 1 - frac[:, 0]), (i1[:, 0], frac[:, 0])):
        for iy, wy in ((i0[:, 1], 1 - frac[:, 1]), (i1[:, 1], frac[:, 1])):
            np.add.at(weights, (rows, iy * grid + ix), wx * wy)
    return weights


def orient_dimension_names() -> list:
    return [f"g{g}.dorient.c{c}.b{b}" for g in ORIENT_GRIDS for c in range(g * g) for b in range(ORIENT_BINS)]


MAX_SHEAR = 1.0


def dense_representation(skeleton_image, deslant: bool = False, normalisation: str = "bbox",
                         moment_range: float = 2.0) -> Optional[dict]:
    """skeleton_image: 2-d array, non-zero on the centre line. None when the line is too short.
    With ``deslant`` the line is first sheared upright (x' = x - s*(y - mean_y), s = mu11/mu02)."""
    ys, xs = np.nonzero(np.asarray(skeleton_image))
    if len(xs) < 4:
        return None
    raw = np.stack([xs, ys], 1).astype(float)
    pts = raw.copy()
    if deslant:
        c = raw - raw.mean(0)
        mu02 = float((c[:, 1] ** 2).mean())
        shear = float(np.clip((c[:, 0] * c[:, 1]).mean() / mu02, -MAX_SHEAR, MAX_SHEAR)) if mu02 > 1e-9 else 0.0
        pts[:, 0] -= shear * (raw[:, 1] - raw[:, 1].mean())
    angles = np.empty(len(pts))
    for i, p in enumerate(pts):
        nb = pts[np.abs(raw - raw[i]).max(1) <= TANGENT_RADIUS] - p     # neighbours on the original line
        _, vecs = np.linalg.eigh(nb.T @ nb)
        v = vecs[:, 1]
        angles[i] = math.atan2(v[1], v[0]) % math.pi
    extent = np.maximum(pts.max(0) - pts.min(0), 1e-6)
    if normalisation == "moment":      # centroid +- moment_range standard deviations per axis
        half = np.maximum(moment_range * np.maximum(pts.std(0), 1e-6), 0.02 * float(extent.max()))
        unit = np.clip((pts - (pts.mean(0) - half)) / (2 * half), 0.0, 1.0)
    else:
        unit = (pts - pts.min(0)) / extent
    cells = np.clip((unit * GRID).astype(int), 0, GRID - 1)
    x = angles / math.pi * ORIENT_BINS
    b0 = np.floor(x).astype(int) % ORIENT_BINS
    frac = x - np.floor(x)
    W = np.zeros((len(pts), ORIENT_BINS))
    W[np.arange(len(pts)), b0] = 1 - frac
    W[np.arange(len(pts)), (b0 + 1) % ORIENT_BINS] += frac

    centres = (cells.astype(float) + 0.5) / GRID
    orient = np.concatenate([((_cell_weights(centres, g) / len(centres)).T @ W).ravel() for g in ORIENT_GRIDS])

    u, inv = np.unique(cells, axis=0, return_inverse=True)
    upts = u.astype(float) / GRID
    Wm = np.zeros((len(u), ORIENT_BINS))
    np.add.at(Wm, inv.ravel(), W)
    theta = np.arange(ORIENT_BINS) / ORIENT_BINS * math.pi
    tan = np.stack([(Wm * np.cos(2 * theta)).sum(1), (Wm * np.sin(2 * theta)).sum(1)], 1)
    tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-6)
    idx = [int(np.argmin(upts.sum(1)))]
    d = np.linalg.norm(upts - upts[idx[0]], axis=1)
    while len(idx) < min(N_POINTS, len(upts)):
        j = int(np.argmax(d))
        idx.append(j)
        d = np.minimum(d, np.linalg.norm(upts - upts[j], axis=1))
    if len(idx) < N_POINTS:
        idx = idx + [idx[i % len(idx)] for i in range(N_POINTS - len(idx))]
    return {
        "orient": [float(v) for v in orient],
        "points": [float(v) for v in upts[idx].ravel()],
        "tangents": [float(v) for v in tan[idx].ravel()],
    }
