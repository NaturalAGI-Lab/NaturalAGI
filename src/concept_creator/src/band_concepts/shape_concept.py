"""Shape concept of a leaf: what the centre lines of one original and of its augmentations have in common.

The original's N centre-line points are the anchors. Every augmentation's points are assigned to the anchors
one-to-one (points with similar surroundings and position), which gives for each anchor
  * a mean position,
  * a tolerance (how far the assigned points scatter around it),
  * a mean shape context (where the rest of the line lies around it),
  * a mean tangent.
Classification compares an image with this prototype, never with an individual example.
Pure numpy / scipy. `shape_context` must stay identical to classification/band/shape_context.py
(unit_tests/test_shape_context.py checks that).
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

RADIAL_BINS = 5
ANGULAR_BINS = 12
POSITION_WEIGHT = 0.3


def shape_context(points: np.ndarray) -> np.ndarray:
    """(N, 2) unit-box points -> (N, RADIAL_BINS * ANGULAR_BINS) normalised log-polar histograms."""
    points = np.asarray(points, np.float32)
    d = np.linalg.norm(points[:, None] - points[None], axis=2)
    mean = d[d > 0].mean() if (d > 0).any() else 1.0
    r = d / mean
    edges = np.logspace(np.log10(0.125), np.log10(2.0), RADIAL_BINS + 1)
    rb = np.clip(np.searchsorted(edges, r) - 1, 0, RADIAL_BINS - 1)
    ang = np.arctan2(points[None, :, 1] - points[:, None, 1], points[None, :, 0] - points[:, None, 0]) % (2 * np.pi)
    tb = np.minimum((ang / (2 * np.pi) * ANGULAR_BINS).astype(int), ANGULAR_BINS - 1)
    hist = np.zeros((len(points), RADIAL_BINS * ANGULAR_BINS), np.float32)
    valid = (r > 0) & (r <= edges[-1])
    for i in range(len(points)):
        np.add.at(hist[i], rb[i][valid[i]] * ANGULAR_BINS + tb[i][valid[i]], 1.0)
    return hist / np.maximum(hist.sum(1, keepdims=True), 1e-6)


def leaf_prototype(points: List[np.ndarray], tangents: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """points[0] / tangents[0] belong to the original, the rest to its augmentations (each (N, 2)).
    -> (mean positions (N, 2), tolerances (N,), mean shape contexts (N, B), mean tangents (N, 2))"""
    anchors = np.asarray(points[0], np.float32)
    anchor_hist = shape_context(anchors)
    pos, hist, tan = [anchors], [anchor_hist], [np.asarray(tangents[0], np.float32)]
    for p, t in zip(points[1:], tangents[1:]):
        p, t = np.asarray(p, np.float32), np.asarray(t, np.float32)
        h = shape_context(p)
        cost = 0.5 * ((h[:, None] - anchor_hist[None]) ** 2 / (h[:, None] + anchor_hist[None] + 1e-6)).sum(2)
        cost = cost + POSITION_WEIGHT * np.linalg.norm(p[:, None] - anchors[None], axis=2)
        rows, cols = linear_sum_assignment(cost)
        order = np.argsort(cols)                         # row index of the point assigned to anchor 0, 1, ...
        pos.append(p[rows[order]]); hist.append(h[rows[order]]); tan.append(t[rows[order]])
    pos, hist, tan = np.stack(pos), np.stack(hist), np.stack(tan)
    mu = pos.mean(0)
    tol = np.sqrt(((pos - mu[None]) ** 2).sum(2).mean(0))
    mean_tan = tan.mean(0)
    mean_tan /= np.maximum(np.linalg.norm(mean_tan, axis=1, keepdims=True), 1e-6)
    return mu, tol, hist.mean(0), mean_tan
